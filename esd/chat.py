"""Step 6, Answer: our assistant, wiring steps 1-5 together."""
from . import config
from .base import BaseAssistant
from .extractor import extract
from .graph_store import MemoryGraph
from .llm import count_tokens
from .memory_card import build_card
from .retriever import retrieve
from .revision import integrate


class ESDAssistant(BaseAssistant):
    key = "esd"
    name = "ESD-Lite (ours)"
    label = "MEMORY CARD"

    def load(self) -> None:
        self.graph = MemoryGraph.load(self.path) if self.path else MemoryGraph()
        self.last_actions: list[dict] = []

    def save(self) -> None:
        if self.path:
            self.graph.save(self.path)

    def observe(self, msg: str, ts: str) -> list[dict]:
        facts = extract(msg, ts, self.graph.known_slots())
        self.last_actions = integrate(self.graph, facts, ts, msg)
        self.save()
        return self.last_actions

    def memory_block(self, question: str, ts: str) -> tuple[str, list[str], dict]:
        r = retrieve(self.graph, question, ts)
        card, used = build_card(r.hits, self.graph, ts, config.CARD_TOKEN_BUDGET)
        extra = {
            "hits": [h.model_dump() for h in r.hits],
            "seed_entities": r.seed_entities,
            "concepts": r.concepts,
            "card_tokens": count_tokens(card),
        }
        return card, used, extra
