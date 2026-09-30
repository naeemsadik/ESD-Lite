"""The "current method": a standard Graph RAG memory.

Built the way LightRAG / GraphRAG-style local search works:
- every message becomes (subject, relation, object) triples in a graph,
- questions are turned into keywords, matched to entities by similarity,
- the triples around the matched entities are pasted into the prompt as text.

Like those systems, it keeps no valid-time and never retires a triple, so
changed facts end up side by side with the facts they replaced. That is the
behaviour we compare against; nothing here is deliberately weakened.
"""
import json
import uuid

import networkx as nx
import numpy as np
from pydantic import BaseModel

from esd import config, llm
from esd.base import BaseAssistant
from esd.graph_store import norm_entity

TOP_ENTITIES = 5
MATCH_MIN = 0.35
IGNORED = {"user", "i", "me"}


class Triple(BaseModel):
    subject: str
    relation: str
    object: str


class Triples(BaseModel):
    triples: list[Triple]


class Keywords(BaseModel):
    keywords: list[str]


TRIPLE_SYSTEM = """Extract knowledge-graph triples (subject, relation, object) from ONE user message, for a personal assistant's knowledge graph.
- The speaker is "user".
- Use short lowercase entity names and short lowercase relation phrases (e.g. "works at", "uses", "lives in", "sister of", "dislikes").
- Only lasting information; greetings and chit-chat -> empty list."""

KEYWORD_SYSTEM = """Extract 3-8 search keywords from the user's question for looking things up in a knowledge graph: the specific entities mentioned and the broader themes of the question."""


class GraphRAGAssistant(BaseAssistant):
    key = "graph_rag"
    name = "Standard Graph RAG"
    label = "KNOWLEDGE GRAPH FACTS"

    # --- storage ---------------------------------------------------------------
    def load(self) -> None:
        self.g = nx.MultiDiGraph()
        self.seq = 0
        if self.path and self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for e in data.get("edges", []):
                self._add(e["s"], e["relation"], e["o"], e["added_at"], e["id"])

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        edges = [
            {"id": k, "s": u, "o": v, "relation": d["relation"], "added_at": d["added_at"]}
            for u, v, k, d in sorted(self.edges(), key=lambda x: x[3]["seq"])
        ]
        self.path.write_text(json.dumps({"edges": edges}, indent=1), encoding="utf-8")

    def _add(self, s: str, relation: str, o: str, added_at: str, edge_id: str | None = None) -> str | None:
        s, o = norm_entity(s), norm_entity(o)
        relation = " ".join(relation.lower().split())
        if not s or not o or not relation:
            return None
        if self.g.has_node(s):
            for _, v, d in self.g.out_edges(s, data=True):
                if v == o and d["relation"] == relation:
                    return None  # exact duplicate
        edge_id = edge_id or "t_" + uuid.uuid4().hex[:8]
        self.seq += 1
        self.g.add_edge(s, o, key=edge_id, relation=relation, added_at=added_at, seq=self.seq)
        return edge_id

    def edges(self) -> list[tuple[str, str, str, dict]]:
        return list(self.g.edges(keys=True, data=True))

    # --- the method ------------------------------------------------------------
    def observe(self, msg: str, ts: str) -> list[str]:
        result = llm.parse(
            [{"role": "system", "content": TRIPLE_SYSTEM}, {"role": "user", "content": msg}],
            Triples,
            default=Triples(triples=[]),
        )
        added = []
        for t in result.triples:
            if self._add(t.subject, t.relation, t.object, ts):
                added.append(f"{t.subject} — {t.relation} — {t.object}")
        self.save()
        return added

    def memory_block(self, question: str, ts: str) -> tuple[str, list[str], dict]:
        names = [n for n in self.g.nodes if n not in IGNORED]
        if not names:
            return "", [], {"matched": {}, "keywords": []}
        kw = llm.parse(
            [{"role": "system", "content": KEYWORD_SYSTEM}, {"role": "user", "content": question}],
            Keywords,
            default=Keywords(keywords=[]),
        )
        keywords = [k.strip() for k in kw.keywords if k.strip()] or [question]

        sims = llm.cosine_matrix(llm.embed(keywords), llm.embed(names))
        best, arg = sims.max(axis=0), sims.argmax(axis=0)
        order = np.argsort(-best)
        matched = {names[i]: keywords[arg[i]] for i in order[:TOP_ENTITIES] if best[i] >= MATCH_MIN}

        lines, used, seen, tokens = [], [], set(), 0
        for ent in matched:
            around = list(self.g.out_edges(ent, keys=True, data=True)) + list(self.g.in_edges(ent, keys=True, data=True))
            for u, v, k, d in sorted(around, key=lambda x: x[3]["seq"]):
                if k in seen:
                    continue
                seen.add(k)
                line = f"{u} — {d['relation']} — {v}"
                cost = llm.count_tokens(line) + 1
                if tokens + cost > config.GRAPH_RAG_TOKEN_CAP:
                    break
                lines.append(line)
                used.append(k)
                tokens += cost
        return "\n".join(lines), used, {"matched": matched, "keywords": keywords}

    # --- for the demo screen ---------------------------------------------------
    def _edges_touching(self, names: set[str]) -> list[str]:
        names = {n for n in names if n and n not in IGNORED}
        if not names:
            return []
        nodes = {
            node
            for node in self.g.nodes
            if node not in IGNORED
            and any(node == n or (len(n) >= 3 and (n in node or node in n)) for n in names)
        }
        return [k for u, v, k in self.g.edges(keys=True) if u in nodes or v in nodes]

    def conflicts(self, esd_changes) -> list[dict]:
        """Changes our method detected, located in this graph.

        Each result is a place where this graph still stores the old fact and the
        new fact side by side, both treated as true.
        """
        out = []
        for old, new in esd_changes:
            old_e = {norm_entity(e) for e in old.entities}
            new_e = {norm_entity(e) for e in new.entities}
            stale = self._edges_touching((old_e - new_e) or old_e)
            fresh = self._edges_touching((new_e - old_e) or new_e)
            fresh = [k for k in fresh if k not in stale]
            if stale and fresh:
                out.append({"old": old.statement, "new": new.statement, "stale_edges": stale, "fresh_edges": fresh})
        return out
