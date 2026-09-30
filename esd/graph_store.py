"""Step 2, Store: the bi-temporal memory graph (spec 4.2).

Nodes are facts (with valid time and transaction time) and entities.
Edges: fact -ABOUT-> entity, and new fact -SUPERSEDES-> old fact.
Nothing is ever deleted; replaced facts are closed off instead.
"""
import json
import uuid
from pathlib import Path

import networkx as nx

from .models import Fact

ABOUT_WEIGHT = 1.0
SUPERSEDES_WEIGHT = 0.3


def new_fact_id() -> str:
    return "f_" + uuid.uuid4().hex[:8]


def entity_id(name: str) -> str:
    return "e:" + norm_entity(name)


def norm_entity(name: str) -> str:
    return " ".join(name.lower().strip().split())


class MemoryGraph:
    def __init__(self) -> None:
        self.g = nx.MultiDiGraph()
        self.facts: dict[str, Fact] = {}
        self.version = 0

    # --- writing ---------------------------------------------------------------
    def add_fact(self, fact: Fact) -> str:
        if fact.last_seen is None:
            fact.last_seen = fact.recorded_at
        self.facts[fact.id] = fact
        self.g.add_node(fact.id, node_type="fact", kind=fact.kind)
        for name in fact.entities:
            if not norm_entity(name):
                continue
            eid = entity_id(name)
            if eid not in self.g:
                self.g.add_node(eid, node_type="entity", name=norm_entity(name))
            self.g.add_edge(fact.id, eid, key="ABOUT", rel="ABOUT", weight=ABOUT_WEIGHT)
        self.version += 1
        return fact.id

    def supersede(self, old_id: str, new_id: str, ts: str) -> None:
        """AGM-style revision: close the old fact's intervals and link new -> old."""
        old, new = self.facts[old_id], self.facts[new_id]
        # Valid time ends when the new fact became true (if that is sensible), else now.
        old.valid_to = new.valid_from if new.valid_from >= old.valid_from else ts
        old.invalidated_at = ts
        old.superseded_by = new_id
        self.g.add_edge(new_id, old_id, key="SUPERSEDES", rel="SUPERSEDES", weight=SUPERSEDES_WEIGHT)
        self.version += 1

    def bump(self, fact_id: str, ts: str) -> None:
        fact = self.facts[fact_id]
        fact.mentions += 1
        fact.last_seen = ts
        self.version += 1

    # --- reading ---------------------------------------------------------------
    @staticmethod
    def is_active(fact: Fact, ts: str | None = None) -> bool:
        if fact.superseded_by is not None:
            return False
        return fact.valid_to is None or ts is None or fact.valid_to > ts

    def active_facts(self, ts: str | None = None) -> list[Fact]:
        return [f for f in self.facts.values() if self.is_active(f, ts)]

    def old_facts(self) -> list[Fact]:
        return [f for f in self.facts.values() if f.superseded_by is not None]

    def history(self, slot: str) -> list[Fact]:
        return sorted((f for f in self.facts.values() if f.slot == slot), key=lambda f: f.valid_from)

    def predecessors(self, fact_id: str) -> list[Fact]:
        """Facts that this fact replaced (directly)."""
        return [
            self.facts[v]
            for _, v, k in self.g.out_edges(fact_id, keys=True)
            if k == "SUPERSEDES"
        ]

    def current_version(self, fact_id: str) -> str:
        """Follow "replaced by" links to the fact that is true now."""
        seen = set()
        while self.facts[fact_id].superseded_by and fact_id not in seen:
            seen.add(fact_id)
            fact_id = self.facts[fact_id].superseded_by
        return fact_id

    def known_slots(self) -> list[str]:
        return sorted({f.slot for f in self.active_facts() if f.slot})

    def changes(self) -> list[tuple[Fact, Fact]]:
        """(old, new) pairs for every replacement we have recorded."""
        return [(f, self.facts[f.superseded_by]) for f in self.old_facts()]

    def entity_ids(self) -> list[str]:
        return [n for n, d in self.g.nodes(data=True) if d.get("node_type") == "entity"]

    def entity_name(self, eid: str) -> str:
        return self.g.nodes[eid]["name"]

    def fact_entity_ids(self, fact_id: str) -> list[str]:
        return [v for _, v, k in self.g.out_edges(fact_id, keys=True) if k == "ABOUT"]

    def __len__(self) -> int:
        return len(self.facts)

    # --- persistence -----------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "facts": [f.model_dump() for f in self.facts.values()],
            "supersedes": [[u, v] for u, v, k in self.g.edges(keys=True) if k == "SUPERSEDES"],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryGraph":
        mg = cls()
        for fd in data.get("facts", []):
            mg.add_fact(Fact(**fd))
        for u, v in data.get("supersedes", []):
            mg.g.add_edge(u, v, key="SUPERSEDES", rel="SUPERSEDES", weight=SUPERSEDES_WEIGHT)
        mg.version = data.get("version", mg.version)
        return mg

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "MemoryGraph":
        if not path.exists():
            return cls()
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
