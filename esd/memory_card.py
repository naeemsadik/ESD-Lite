"""Step 5, Compress: pack the best facts into a fixed-size Memory Card.

This is our text stand-in for the spec's K=64 soft prefix (spec 4.4): however
large memory grows, the card never exceeds `budget` tokens.
"""
from .graph_store import MemoryGraph
from .llm import count_tokens
from .models import Hit

ORDER = ["constraint", "decision", "fact", "event"]
TITLES = {
    "constraint": "RULES (always respect)",
    "decision": "DECISIONS",
    "fact": "FACTS",
    "event": "EVENTS",
}
RULE_PRIORITY = 0.5


def _line(graph: MemoryGraph, fact_id: str) -> str:
    f = graph.facts[fact_id]
    line = f"- {f.statement} ({f.valid_from})" if f.kind == "event" else f"- {f.statement} (since {f.valid_from})"
    olds = graph.predecessors(fact_id)
    if olds:
        line += "; replaced: " + "; ".join(f'"{o.statement}" ({o.valid_from} to {o.valid_to})' for o in olds)
    return line


def _render(sections: dict[str, list[str]], ts: str) -> str:
    parts = [f"MEMORY CARD (today {ts})"]
    for kind in ORDER:
        if sections[kind]:
            parts.append(TITLES[kind] + ":")
            parts.extend(sections[kind])
    if len(parts) == 1:
        parts.append("(nothing relevant remembered yet)")
    return "\n".join(parts)


def build_card(hits: list[Hit], graph: MemoryGraph, ts: str, budget: int) -> tuple[str, list[str]]:
    """Greedily add the highest-scoring facts until the token budget is reached."""
    sections: dict[str, list[str]] = {k: [] for k in ORDER}
    used: list[str] = []
    ranked = sorted(hits, key=lambda h: -(h.score + (RULE_PRIORITY if h.kind == "constraint" else 0.0)))
    for hit in ranked:
        if hit.fact_id not in graph.facts:
            continue
        line = _line(graph, hit.fact_id)
        sections[hit.kind].append(line)
        if count_tokens(_render(sections, ts)) > budget:
            sections[hit.kind].pop()
            continue
        used.append(hit.fact_id)
    return _render(sections, ts), used
