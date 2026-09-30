"""Step 4, Find: what in memory matters for this question? (spec 4.3, simplified)

1. Expand the question into hidden concepts ("macaron" -> almond flour, nuts...).
2. Seed the walk with facts/entities that match the question or those concepts.
3. Spread along the graph with Personalized PageRank (multi-hop links).
4. Fade old, rarely mentioned facts (spec's decay formula with hand-set rates).
5. Always include active rules (constraints).
"""
import math
from dataclasses import dataclass, field
from datetime import date

import networkx as nx
import numpy as np
from pydantic import BaseModel

from . import config, llm
from .graph_store import MemoryGraph
from .models import Hit

SEED_MIN = 0.20
MAX_SEEDS = 10
DIRECT_SEEDS = 4
LINK_MIN = 0.05
TOP_K = 12
HUB_ENTITIES = {"user", "i", "me", "myself"}


class Expansion(BaseModel):
    concepts: list[str]


EXPAND_SYSTEM = """A user is asking their personal AI assistant something. List 6-10 short concepts that are hidden inside or implied by the request and could make an old memory about the user relevant: ingredients, components, materials, people or roles involved, activities, places, risks, times, costs, tools. Think about what the request actually involves, not just its words.
Example: "Plan a weekend hiking trip" -> mountains, altitude, cold weather, long walks, driving, packing, budget, outdoor food.
Example: "Suggest a gift for my colleague" -> coworker, workplace, budget, hobbies, food gifts, dietary preferences."""


@dataclass
class Retrieval:
    hits: list[Hit] = field(default_factory=list)
    seed_entities: dict[str, dict] = field(default_factory=dict)  # entity id -> {via, score}
    concepts: list[str] = field(default_factory=list)


def _days(since: str | None, ts: str) -> int:
    try:
        return max(0, (date.fromisoformat(ts[:10]) - date.fromisoformat((since or ts)[:10])).days)
    except ValueError:
        return 0


def expand(question: str) -> list[str]:
    result = llm.parse(
        [{"role": "system", "content": EXPAND_SYSTEM}, {"role": "user", "content": question}],
        Expansion,
        default=Expansion(concepts=[]),
    )
    return [c.strip() for c in result.concepts if c.strip()][:10]


def retrieve(graph: MemoryGraph, question: str, ts: str) -> Retrieval:
    active = graph.active_facts(ts)
    if not active:
        return Retrieval()

    concepts = expand(question)
    queries = [question] + concepts
    labels = ["question"] + concepts
    qv = llm.embed(queries)

    # Entities that belong to at least one active fact (hubs like "user" excluded).
    active_ids = {f.id for f in active}
    ent_ids = [
        e
        for e in graph.entity_ids()
        if graph.entity_name(e) not in HUB_ENTITIES
        and any(p in active_ids for p in graph.g.predecessors(e))
    ]

    # --- 2. seeds ------------------------------------------------------------
    # For every candidate node: its best match over question + concepts, and its match
    # with the question alone. (node, best, best label, question-only, via an earlier version?)
    candidates: list[tuple[str, float, str, float, bool]] = []

    def add(nodes: list[str], sims: np.ndarray, from_old: bool = False) -> None:
        for j, node in enumerate(nodes):
            i = int(np.argmax(sims[:, j]))
            candidates.append((node, float(sims[i, j]), labels[i], float(sims[0, j]), from_old))

    add([f.id for f in active], llm.cosine_matrix(qv, llm.embed([f.embed_text() for f in active])))
    if ent_ids:
        add(ent_ids, llm.cosine_matrix(qv, llm.embed([graph.entity_name(e) for e in ent_ids])))
    # Replaced facts can answer questions about the past ("where did I live in February?").
    # A match on an old fact seeds its current version, whose card line carries the history.
    old = [f for f in graph.old_facts() if graph.current_version(f.id) in active_ids]
    if old:
        add([graph.current_version(f.id) for f in old],
            llm.cosine_matrix(qv, llm.embed([f.embed_text() for f in old])), from_old=True)

    seeds: dict[str, float] = {}
    via: dict[str, str] = {}
    history_seed: set[str] = set()

    def take(node: str, score: float, label: str, from_old: bool) -> None:
        if node not in seeds and score >= SEED_MIN:
            seeds[node], via[node] = score, label
            if from_old:
                history_seed.add(node)

    # The question's own best matches always get in; expanded concepts fill the rest.
    for node, _, _, q_score, from_old in sorted(candidates, key=lambda c: -c[3]):
        if len(seeds) >= DIRECT_SEEDS:
            break
        take(node, q_score, "question", from_old)
    for node, score, label, _, from_old in sorted(candidates, key=lambda c: -c[1]):
        if len(seeds) >= MAX_SEEDS:
            break
        take(node, score, label, from_old)

    # --- 3. graph walk -----------------------------------------------------------
    walk = nx.Graph()
    for f in active:
        walk.add_node(f.id)
        for e in graph.fact_entity_ids(f.id):
            if e in ent_ids:
                walk.add_edge(f.id, e, weight=1.0)
    personalization = {n: s for n, s in seeds.items() if n in walk}
    ppr = nx.pagerank(walk, alpha=0.85, personalization=personalization, weight="weight") if personalization else {}
    max_fact_ppr = max((ppr.get(f.id, 0.0) for f in active), default=0.0) or 1.0

    # --- 4. score --------------------------------------------------------------
    hits: list[Hit] = []
    for f in active:
        seed = seeds.get(f.id, 0.0)
        link = ppr.get(f.id, 0.0) / max_fact_ppr if ppr else 0.0
        is_rule = f.kind == "constraint"
        if seed == 0.0 and link < LINK_MIN and not is_rule:
            continue
        fade = math.exp(-config.DECAY[f.kind] * _days(f.last_seen, ts))
        repeat = math.log(1 + f.mentions) / math.log(2)  # = 1.0 for a single mention
        score = (seed + 0.5 * link) * fade * repeat

        reasons, hit_via, through = [], None, None
        if is_rule:
            reasons.append("standing rule")
        if f.id in seeds:
            hit_via = via[f.id]
            reasons.append(f"matched via '{hit_via}'" + (" (its earlier version)" if f.id in history_seed else ""))
        elif link >= LINK_MIN:
            ents = [e for e in graph.fact_entity_ids(f.id) if e in ppr]
            if ents:
                best = max(ents, key=lambda e: ppr[e])
                through = best
                reasons.append(f"linked through '{graph.entity_name(best)}'")
                if best in seeds:
                    hit_via = via[best]
        hits.append(
            Hit(
                fact_id=f.id,
                statement=f.statement,
                kind=f.kind,
                score=round(score, 4),
                reason=", ".join(reasons) or "linked",
                via=hit_via,
                through=through,
            )
        )

    rules = [h for h in hits if h.kind == "constraint"]
    others = sorted((h for h in hits if h.kind != "constraint"), key=lambda h: -h.score)[:TOP_K]
    hits = sorted(rules + others, key=lambda h: -h.score)

    seed_entities = {e: {"via": via[e], "score": round(seeds[e], 3)} for e in seeds if e.startswith("e:")}
    return Retrieval(hits=hits, seed_entities=seed_entities, concepts=concepts)
