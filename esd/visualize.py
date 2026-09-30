"""Draw both knowledge graphs for the demo screen (pyvis -> HTML)."""
import json
import re

from pyvis.network import Network

from . import config
from .graph_store import MemoryGraph

KIND_COLORS = {"constraint": "#e5484d", "decision": "#3e63dd", "fact": "#30a46c", "event": "#8e4ec6"}
OLD_COLOR = {"background": "#e6e6e6", "border": "#9e9e9e"}
ENTITY_COLOR = "#b0b6bd"
GRAPH_RAG_NODE = "#4c78a8"
GOLD = "#f5a623"
RED = "#e5484d"
ORANGE = "#f08c00"
EDGE_GREY = "#c4c4c4"
HIDDEN_ENTITIES = {"user", "i", "me"}
# Same drawing limit for both panels, so neither looks busier by construction.
MAX_NODES = 40

ESD_LEGEND = "🔴 rule · 🔵 decision · 🟢 fact · 🟣 event · ⚪ replaced · ⭐ question · gold = on the Memory Card"
GRAPH_RAG_LEGEND = "🔷 thing · arrow = relation · ⭐ question · gold = sent to AI · red = changed fact, still stored as true"

# No spaces inside string values: pyvis strips spaces when parsing options.
_OPTIONS = {
    "physics": {
        "barnesHut": {"gravitationalConstant": -1500, "centralGravity": 1.2, "springLength": 60,
                      "springConstant": 0.06, "avoidOverlap": 0.5},
        "stabilization": {"enabled": True, "iterations": 160},
    },
    "interaction": {"hover": True, "tooltipDelay": 120},
    "edges": {"smooth": False, "font": {"size": 11, "align": "middle", "color": "#666666"}},
    "nodes": {"font": {"size": 14}, "scaling": {"label": {"drawThreshold": 3}}},
}


def _safe(text: str) -> str:
    """Labels come from model-extracted text; keep them from ever closing the page's <script>."""
    return " ".join(str(text).split()).replace("<", "‹").replace(">", "›")


def _n(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def _short(text: str, n: int = 28) -> str:
    text = _safe(text)
    return text if len(text) <= n else text[: n - 1] + "…"


def _net(height: int) -> Network:
    net = Network(height=f"{height - 8}px", width="100%", directed=True, cdn_resources="remote")
    options = json.loads(json.dumps(_OPTIONS))
    if height > 400:  # enlarged view: room to spread out, so labels overlap less
        options["physics"]["barnesHut"].update(
            {"gravitationalConstant": -4000, "centralGravity": 0.35, "springLength": 130})
    net.set_options(json.dumps(options))
    return net


def _html(net: Network, legend: str = "") -> str:
    html = net.generate_html(notebook=False)
    html = re.sub(r"<center>\s*<h1>\s*</h1>\s*</center>", "", html)
    html = html.replace(
        "return network;",
        "network.once('stabilizationIterationsDone', function () {\n"
        "                    network.setOptions({physics: false}); network.fit(); });\n"
        "                  return network;",
        1,
    )
    html = html.replace(
        "</head>",
        "<style>body{margin:0;overflow:hidden;} #mynetwork{border:none !important;}"
        ".legend{position:absolute;left:6px;right:6px;bottom:4px;font:11px/1.35 sans-serif;color:#555;"
        "background:rgba(255,255,255,.85);padding:2px 4px;border-radius:4px;pointer-events:none;}</style></head>",
        1,
    )
    if legend:
        html = html.replace("</body>", f"<div class='legend'>{legend}</div></body>", 1)
    return html


def _empty(height: int, message: str) -> str:
    return (
        f"<div style='height:{height - 8}px;display:flex;align-items:center;justify-content:center;"
        f"font-family:sans-serif;color:#888;font-size:13px'>{message}</div>"
    )


def _add_question(net: Network, question: str) -> None:
    net.add_node(
        "Q", label="Q: " + _short(question, 30), title=_safe(question), shape="star", size=20,
        color={"background": GOLD, "border": "#c77c00"}, font={"size": 15, "color": "#8a5300"},
    )


# --- Top panel: our memory graph --------------------------------------------------
def draw_esd(graph: MemoryGraph, answer: dict | None, question: str | None, height: int = 290,
             max_nodes: int = MAX_NODES) -> str:
    if not graph.facts:
        return _empty(height, "Our memory is empty. Start chatting, or load the demo history.")

    used = set(answer["used"]) if answer else set()
    extra = answer.get("extra", {}) if answer else {}
    hits = {h["fact_id"]: h for h in extra.get("hits", []) if h["fact_id"] in used}
    seed_ents = extra.get("seed_entities", {})

    def visible_entities(fid: str) -> list[str]:
        return [e for e in graph.fact_entity_ids(fid) if graph.entity_name(e) not in HIDDEN_ENTITIES]

    # Facts on the card first, then the most recently mentioned, until the node limit.
    facts = sorted(graph.facts.values(), key=lambda f: (f.last_seen or f.recorded_at, f.recorded_at), reverse=True)
    order = [f.id for f in facts if f.id in used] + [f.id for f in facts if f.id not in used]
    chosen: dict[str, None] = {}
    entity_nodes: set[str] = set()
    for fid in order:
        f = graph.facts[fid]
        # keep both ends of every "replaced by" arrow together
        group = [fid] + [o.id for o in graph.predecessors(fid)] + ([f.superseded_by] if f.superseded_by else [])
        group = [g for g in dict.fromkeys(group) if g not in chosen]
        if not group:
            continue
        new_ents = {e for g in group for e in visible_entities(g)} - entity_nodes
        if fid not in used and len(chosen) + len(entity_nodes) + len(group) + len(new_ents) > max_nodes:
            continue
        chosen.update(dict.fromkeys(group))
        entity_nodes |= new_ents

    # The question's path: question -> matched fact, or question -> entity -> linked fact.
    gold_links: set[tuple[str, str]] = set()
    q_edges: dict[str, str] = {}
    for fid, h in hits.items():
        through = h.get("through")
        if through and through in entity_nodes:
            gold_links.add((fid, through))
            if through in seed_ents:
                q_edges.setdefault(through, seed_ents[through]["via"])
            else:  # reached through a matched fact that shares this entity
                for other, oh in hits.items():
                    if other != fid and oh.get("via") and through in graph.fact_entity_ids(other):
                        gold_links.add((other, through))
        elif h.get("via"):
            q_edges.setdefault(fid, h["via"])

    net = _net(height)
    for fid in chosen:
        f = graph.facts[fid]
        color = OLD_COLOR if f.is_old else {"background": KIND_COLORS[f.kind], "border": KIND_COLORS[f.kind]}
        border = {"background": color["background"], "border": GOLD} if fid in used else color
        label = ("(old) " if f.is_old else "") + _short(f.statement)
        span = f"{f.valid_from} to {f.valid_to or 'now'}"
        title = f"{f.kind.upper()}: {_safe(f.statement)} | true {span} | learned {f.recorded_at}"
        if f.is_old:
            title += f" | stopped believing {f.invalidated_at}"
        net.add_node(
            fid, label=label, title=title, shape="dot", size=13 if not f.is_old else 10,
            color=border, borderWidth=4 if fid in used else 1,
            shapeProperties={"borderDashes": [4, 3]} if f.is_old else {},
            font={"size": 15, "color": "#999999" if f.is_old else "#222222"},
        )
    for eid in entity_nodes:
        name = graph.entity_name(eid)
        net.add_node(eid, label=_short(name, 20), title=f"entity: {_safe(name)}", shape="dot", size=6,
                     color=ENTITY_COLOR, font={"size": 13, "color": "#666666"})
    for fid in chosen:
        for eid in visible_entities(fid):
            on_path = (fid, eid) in gold_links
            net.add_edge(fid, eid, color=GOLD if on_path else EDGE_GREY, width=3 if on_path else 1,
                         arrows={"to": {"enabled": False}})
        f = graph.facts[fid]
        if f.superseded_by and f.superseded_by in chosen:
            net.add_edge(fid, f.superseded_by, label="replaced by", color=ORANGE, dashes=True, width=2,
                         font={"size": 13, "color": ORANGE})

    if question and answer:
        _add_question(net, question)
        for target, via in q_edges.items():
            net.add_edge("Q", target, label=_short(via, 16), color=GOLD, dashes=True, width=2,
                         font={"size": 13, "color": "#8a5300"})
    return _html(net, ESD_LEGEND)


def esd_stats(graph: MemoryGraph, answer: dict | None, history_tokens: int = 0) -> str:
    active, old = len(graph.active_facts()), len(graph.old_facts())
    text = f"**Memory:** {_n(active, 'fact')} · {old} replaced (kept)"
    if answer:
        card = answer.get("extra", {}).get("card_tokens", "?")
        text += (f"  \n**Sent to AI:** {answer['prompt_tokens']:,} tokens · "
                 f"Memory Card {card} (limit {config.CARD_TOKEN_BUDGET})")
    if history_tokens:
        text += f"  \nFull history would already be **{history_tokens:,}** tokens, and growing"
    return text


# --- Bottom panel: the current method's graph -----------------------------------
def draw_graph_rag(assistant, answer: dict | None, conflicts: list[dict], question: str | None,
                   height: int = 290, max_nodes: int = MAX_NODES) -> str:
    edges = assistant.edges()
    if not edges:
        return _empty(height, "The current method's graph is empty.")

    used = set(answer["used"]) if answer else set()
    matched = answer.get("extra", {}).get("matched", {}) if answer else {}
    red = {k for c in conflicts for k in c["stale_edges"] + c["fresh_edges"]}

    # Sent-to-AI and conflict edges first, then the most recent, until the node limit.
    edges = sorted(edges, key=lambda e: e[3]["seq"], reverse=True)
    must = [e for e in edges if e[2] in used or e[2] in red]
    rest = [e for e in edges if e[2] not in used and e[2] not in red]
    chosen, shown = [], set()
    for e in must + rest:
        new = {e[0], e[1]} - shown
        if e[2] not in used and e[2] not in red and len(shown) + len(new) > max_nodes:
            continue
        chosen.append(e)
        shown |= new

    net = _net(height)
    nodes: set[str] = set()
    for u, v, k, d in chosen:
        for n in (u, v):
            if n not in nodes:
                net.add_node(n, label=_short(n, 22), title=_safe(n), shape="dot", size=11 if n == "user" else 8,
                             color=GRAPH_RAG_NODE, font={"size": 14, "color": "#333333"})
                nodes.add(n)
        if k in red:
            color, width = RED, 4
        elif k in used:
            color, width = GOLD, 3
        else:
            color, width = EDGE_GREY, 1
        net.add_edge(u, v, label=_short(d["relation"], 18), title=_safe(f"{u} — {d['relation']} — {v}"),
                     color=color, width=width)

    if question and answer:
        _add_question(net, question)
        for ent, kw in matched.items():
            if ent in nodes:
                net.add_edge("Q", ent, label=_short(kw, 16), color=GOLD, dashes=True, width=1.5,
                             font={"size": 13, "color": "#8a5300"})
    return _html(net, GRAPH_RAG_LEGEND)


def graph_rag_stats(assistant, answer: dict | None, conflicts: list[dict]) -> str:
    text = f"**Memory:** {_n(len(assistant.edges()), 'triple')} · **{_n(len(conflicts), 'conflict')} stored as true**"
    if answer:
        mem = answer.get("extra", {}).get("memory_tokens", "?")
        text += f"  \n**Sent to AI:** {answer['prompt_tokens']:,} tokens · knowledge {mem} (its keyword matches)"
    return text
