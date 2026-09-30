"""Step 3, Update: non-destructive belief revision (spec 4.2, AGM).

For each new fact we look for existing facts on the same topic and ask the
model whether the new fact repeats, replaces, or sits alongside each one.
"""
from typing import Literal

import numpy as np
from pydantic import BaseModel

from . import llm
from .graph_store import MemoryGraph, new_fact_id
from .models import ExtractedFact, Fact

SIMILARITY_CANDIDATE = 0.6
MAX_CANDIDATES = 4


class Judgement(BaseModel):
    candidate_index: int
    why: str  # written before the label: a short comparison of what each statement claims
    relation: Literal["same", "replaces", "unrelated"]


class RevisionResult(BaseModel):
    judgements: list[Judgement]


SYSTEM = """You maintain a memory of facts about a user. Compare a NEW statement with numbered EXISTING statements.
For each existing statement decide:
- "same": the new statement says the same thing as the existing one (a repeat or rephrase) and adds no new information.
- "replaces": the new statement updates, changes, reverses or contradicts it, so the existing statement is no longer true now (e.g. switched tools, moved city, changed diet, new budget, cancelled plan).
- "unrelated": both can be true at the same time.
Only choose "replaces" when the two statements cannot both be true now. A new detail about the same topic is "unrelated", not "replaces".
Examples: "User leads project X" vs "Project X is due in May" -> unrelated (both true). "User uses Vim" vs "User switched to VS Code" -> replaces.
Past events stay true (someone who moved still did move).
For each existing statement, first write "why": one short sentence comparing what the two statements claim. Then choose the relation.
Return exactly one judgement per existing statement."""


def _candidates(graph: MemoryGraph, fact: Fact, ts: str) -> list[Fact]:
    active = graph.active_facts(ts)
    if not active:
        return []
    same_slot = [f for f in active if fact.slot and f.slot == fact.slot]
    vecs = llm.embed([fact.statement] + [f.statement for f in active])
    sims = llm.cosine_matrix(vecs[:1], vecs[1:])[0]
    order = np.argsort(-sims)
    similar = [active[i] for i in order if sims[i] >= SIMILARITY_CANDIDATE][:MAX_CANDIDATES]
    seen, out = set(), []
    for f in same_slot + similar:
        if f.id not in seen:
            seen.add(f.id)
            out.append(f)
    return out[: MAX_CANDIDATES + len(same_slot)]


def integrate(graph: MemoryGraph, extracted: list[ExtractedFact], ts: str, source: str) -> list[dict]:
    """Add extracted facts to the graph. Returns a log of what happened, for the UI."""
    actions: list[dict] = []
    for ex in extracted:
        fact = Fact(
            id=new_fact_id(),
            kind=ex.kind,
            statement=ex.statement.strip(),
            slot=(ex.slot or None),
            entities=[e for e in ex.entities if e.strip()],
            triggers=[t for t in ex.triggers if t.strip()],
            valid_from=ex.valid_from or ts,
            recorded_at=ts,
            source=source,
        )
        cands = _candidates(graph, fact, ts)
        if not cands:
            graph.add_fact(fact)
            actions.append({"action": "added", "fact": fact.statement})
            continue

        listing = "\n".join(f"{i}. {c.statement} (since {c.valid_from})" for i, c in enumerate(cands))
        result = llm.parse(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"TODAY: {ts}\nNEW: {fact.statement}\n\nEXISTING:\n{listing}"},
            ],
            RevisionResult,
            default=RevisionResult(judgements=[]),
        )
        rel = {j.candidate_index: j.relation for j in result.judgements}

        repeats = [c for i, c in enumerate(cands) if rel.get(i) == "same"]
        replaced = [c for i, c in enumerate(cands) if rel.get(i) == "replaces"]
        if repeats and not replaced:
            graph.bump(repeats[0].id, ts)
            actions.append({"action": "repeated", "fact": repeats[0].statement})
            continue

        graph.add_fact(fact)
        actions.append({"action": "added", "fact": fact.statement})
        for old in replaced:
            graph.supersede(old.id, fact.id, ts)
            actions.append({"action": "replaced", "old": old.statement, "fact": fact.statement})
    return actions
