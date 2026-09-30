"""Draw both knowledge graphs for the demo screen (pyvis -> HTML)."""
import json
import re

from pyvis.network import Network

from . import config
from .graph_store import MemoryGraph

HIDDEN_ENTITIES = {"user", "i", "me"}
# Same drawing limit for both panels, so neither looks busier by construction.
MAX_NODES = 40
LEGEND_SPACE = 46  # px under the graph for the legend
KIND_NAMES = {"constraint": "Rule", "decision": "Decision", "fact": "Fact", "event": "Event"}

# One palette per theme. Kind colours are categorical data colours; amber marks what was
# sent to the AI; red is reserved for conflicts. Backgrounds match the app theme.
PALETTES = {
    "light": {
        "bg": "#F3F5F8", "ink": "#172033", "muted": "#5A6376",
        "kinds": {"constraint": "#C8372D", "decision": "#2F62C9", "fact": "#2E8B57", "event": "#8150C2"},
        "old_fill": "#D8DDE5", "old_border": "#8E97A6", "entity": "#A7B0BD", "edge": "#C9D0DA",
        "amber": "#D48A0B", "amber_ink": "#8A5A00", "replaced": "#B8661A", "rag_node": "#6E7C91",
        "conflict": "#C8372D", "legend_bg": "rgba(243,245,248,.92)",
    },
    "dark": {
        "bg": "#11151C", "ink": "#E6E9EF", "muted": "#9AA3B2",
        "kinds": {"constraint": "#E5645A", "decision": "#6B9BEA", "fact": "#4FB57E", "event": "#A98AE0"},
        "old_fill": "#2D3440", "old_border": "#6B7483", "entity": "#5C6676", "edge": "#394251",
        "amber": "#F0B232", "amber_ink": "#F0B232", "replaced": "#E0914A", "rag_node": "#8391A6",
        "conflict": "#E5645A", "legend_bg": "rgba(17,21,28,.9)",
    },
}

# No spaces inside string values: pyvis strips spaces when parsing options.
_OPTIONS = {
    "physics": {
        "barnesHut": {"gravitationalConstant": -1500, "centralGravity": 1.2, "springLength": 60,
                      "springConstant": 0.06, "avoidOverlap": 0.5},
        "stabilization": {"enabled": True, "iterations": 160},
    },
    "interaction": {"hover": True, "tooltipDelay": 120},
    "edges": {"smooth": False, "font": {"size": 11, "align": "middle", "strokeWidth": 0}},
    "nodes": {"font": {"size": 14}, "scaling": {"label": {"drawThreshold": 3}}},
}
_FONT = "Atkinson Hyperlegible Next, system-ui, sans-serif"


def _palette(dark: bool) -> dict:
    return PALETTES["dark" if dark else "light"]


def _plural(count: int, one: str, many: str) -> str:
    return one if count == 1 else many


def _safe(text: str) -> str:
    """Labels come from model-extracted text; keep them from ever closing the page's <script>."""
    return " ".join(str(text).split()).replace("<", "‹").replace(">", "›")


def _short(text: str, n: int = 28) -> str:
    text = _safe(text)
    return text if len(text) <= n else text[: n - 1] + "…"


def _net(height: int, pal: dict) -> Network:
    # Leave room under the drawing for the legend, so it never covers nodes.
    net = Network(height=f"{height - LEGEND_SPACE}px", width="100%", directed=True, cdn_resources="remote",
                  bgcolor=pal["bg"])
    options = json.loads(json.dumps(_OPTIONS))
    options["edges"]["font"]["color"] = pal["muted"]
    if height > 400:  # enlarged view: room to spread out, so labels overlap less
        options["physics"]["barnesHut"].update(
            {"gravitationalConstant": -4000, "centralGravity": 0.35, "springLength": 130})
    net.set_options(json.dumps(options))
    return net


def _swatch(color: str, label: str, ring: bool = False, dashed: bool = False) -> str:
    style = f"border:2px {'dashed' if dashed else 'solid'} {color};" + ("" if ring else f"background:{color};")
    return f"<span class='k'><i style='{style}'></i>{label}</span>"


def _html(net: Network, pal: dict, legend: str = "") -> str:
    html = net.generate_html(notebook=False)
    html = re.sub(r"<center>\s*<h1>\s*</h1>\s*</center>", "", html)
    html = html.replace(
        "return network;",
        "network.once('stabilizationIterationsDone', function () {\n"
        "                    network.setOptions({physics: false}); network.fit(); });\n"
        "                  return network;",
        1,
    )
    style = (
        "<style>"
        "@font-face{font-family:'Atkinson Hyperlegible Next';src:url('/app/static/fonts/AtkinsonHyperlegibleNext.woff2')"
        " format('woff2');font-weight:200 800;font-display:swap;}"
        f"html,body{{margin:0;overflow:hidden;background:{pal['bg']};}}"
        "#mynetwork{border:none !important;}"
        # pyvis wraps the drawing in a white Bootstrap card; let it take the theme background instead.
        ".card{background:transparent !important;border:none !important;}"
        f".legend{{font:12px/1.5 {_FONT};color:{pal['muted']};padding:4px 6px 0;}}"
        ".legend .k{display:inline-flex;align-items:center;gap:5px;margin-right:12px;white-space:nowrap;}"
        ".legend i{display:inline-block;width:9px;height:9px;border-radius:50%;box-sizing:border-box;}"
        f"div.vis-tooltip{{font:13px/1.45 {_FONT} !important;white-space:pre-line !important;max-width:320px;"
        f"color:{pal['ink']} !important;background:{pal['bg']} !important;border:1px solid {pal['edge']} !important;"
        "border-radius:8px !important;padding:8px 10px !important;box-shadow:0 6px 20px rgba(15,23,42,.18) !important;}"
        "</style></head>"
    )
    html = html.replace("</head>", style, 1)
    if legend:
        html = html.replace("</body>", f"<div class='legend'>{legend}</div></body>", 1)
    return html


def _empty(height: int, message: str, pal: dict) -> str:
    return (
        f"<div style='height:{height - 8}px;display:flex;align-items:center;justify-content:center;"
        f"background:{pal['bg']};font:14px/1.5 {_FONT};color:{pal['muted']};text-align:center;padding:0 24px'>"
        f"{message}</div>"
    )


def _add_question(net: Network, question: str, pal: dict) -> None:
    net.add_node(
        "Q", label="Q: " + _short(question, 30), title=f"Your question\n{_safe(question)}", shape="star", size=20,
        color={"background": pal["amber"], "border": pal["amber"]},
        font={"size": 15, "color": pal["amber_ink"], "face": _FONT},
    )


# --- Top panel: our memory graph --------------------------------------------------
def draw_esd(graph: MemoryGraph, answer: dict | None, question: str | None, height: int = 290,
             max_nodes: int = MAX_NODES, dark: bool = False) -> str:
    pal = _palette(dark)
    if not graph.facts:
        return _empty(height, "Memory is empty. Send a message, or load the demo history from the sidebar.", pal)

    # An answer saved in a chat may point at facts from before a memory reset or reload.
    used = {u for u in answer["used"] if u in graph.facts} if answer else set()
    extra = answer.get("extra", {}) if answer else {}
    hits = {h["fact_id"]: h for h in extra.get("hits", []) if h["fact_id"] in used}
    seed_ents = {e: v for e, v in extra.get("seed_entities", {}).items() if e in graph.g}

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

    net = _net(height, pal)
    for fid in chosen:
        f = graph.facts[fid]
        base = pal["kinds"][f.kind]
        fill = pal["old_fill"] if f.is_old else base
        edge = pal["old_border"] if f.is_old else base
        label = ("(old) " if f.is_old else "") + _short(f.statement)
        title = (f"{KIND_NAMES[f.kind]}{' (replaced)' if f.is_old else ''}\n{_safe(f.statement)}\n"
                 f"True {f.valid_from} to {f.valid_to or 'now'}\nLearned {f.recorded_at}")
        if f.is_old:
            title += f"\nStopped believing {f.invalidated_at}"
        net.add_node(
            fid, label=label, title=title, shape="dot", size=13 if not f.is_old else 10,
            color={"background": fill, "border": pal["amber"] if fid in used else edge},
            borderWidth=4 if fid in used else 1,
            shapeProperties={"borderDashes": [4, 3]} if f.is_old else {},
            font={"size": 15, "color": pal["muted"] if f.is_old else pal["ink"], "face": _FONT},
        )
    for eid in entity_nodes:
        name = graph.entity_name(eid)
        net.add_node(eid, label=_short(name, 20), title=f"Entity\n{_safe(name)}", shape="dot", size=6,
                     color=pal["entity"], font={"size": 13, "color": pal["muted"], "face": _FONT})
    for fid in chosen:
        for eid in visible_entities(fid):
            on_path = (fid, eid) in gold_links
            net.add_edge(fid, eid, color=pal["amber"] if on_path else pal["edge"], width=3 if on_path else 1,
                         arrows={"to": {"enabled": False}})
        f = graph.facts[fid]
        if f.superseded_by and f.superseded_by in chosen:
            net.add_edge(fid, f.superseded_by, label="replaced by", color=pal["replaced"], dashes=True, width=2,
                         font={"size": 13, "color": pal["replaced"], "face": _FONT})

    if question and answer:
        _add_question(net, question, pal)
        for target, via in q_edges.items():
            net.add_edge("Q", target, label=_short(via, 16), color=pal["amber"], dashes=True, width=2,
                         font={"size": 13, "color": pal["amber_ink"], "face": _FONT})
    legend = "".join([
        _swatch(pal["kinds"]["constraint"], "rule"), _swatch(pal["kinds"]["decision"], "decision"),
        _swatch(pal["kinds"]["fact"], "fact"), _swatch(pal["kinds"]["event"], "event"),
        _swatch(pal["old_border"], "replaced", ring=True, dashed=True),
        _swatch(pal["amber"], "sent on the Memory Card", ring=True),
    ])
    return _html(net, pal, legend)


def esd_stats(graph: MemoryGraph, answer: dict | None, history_tokens: int = 0) -> list[dict]:
    """Counters for the top panel: [{value, label, note?, tone?}]."""
    active = len(graph.active_facts())
    items = [
        {"value": f"{active:,}", "label": _plural(active, "fact in memory", "facts in memory")},
        {"value": f"{len(graph.old_facts()):,}", "label": "replaced, kept as history"},
    ]
    if answer:
        card = answer.get("extra", {}).get("card_tokens", "?")
        items.append({"value": f"{answer['prompt_tokens']:,}", "label": "tokens sent",
                      "note": f"Memory Card {card} of {config.CARD_TOKEN_BUDGET}"})
    if history_tokens:
        items.append({"value": f"{history_tokens:,}", "label": "tokens if pasting full history"})
    return items


# --- Bottom panel: the current method's graph -----------------------------------
def draw_graph_rag(assistant, answer: dict | None, conflicts: list[dict], question: str | None,
                   height: int = 290, max_nodes: int = MAX_NODES, dark: bool = False) -> str:
    pal = _palette(dark)
    edges = assistant.edges()
    if not edges:
        return _empty(height, "The current method has nothing stored yet.", pal)

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

    net = _net(height, pal)
    nodes: set[str] = set()
    for u, v, k, d in chosen:
        for n in (u, v):
            if n not in nodes:
                net.add_node(n, label=_short(n, 22), title=f"Entity\n{_safe(n)}", shape="dot",
                             size=11 if n == "user" else 8, color=pal["rag_node"],
                             font={"size": 14, "color": pal["ink"], "face": _FONT})
                nodes.add(n)
        if k in red:
            color, width = pal["conflict"], 4
        elif k in used:
            color, width = pal["amber"], 3
        else:
            color, width = pal["edge"], 1
        net.add_edge(u, v, label=_short(d["relation"], 18), title=_safe(f"{u} → {d['relation']} → {v}"),
                     color=color, width=width)

    if question and answer:
        _add_question(net, question, pal)
        for ent, kw in matched.items():
            if ent in nodes:
                net.add_edge("Q", ent, label=_short(kw, 16), color=pal["amber"], dashes=True, width=1.5,
                             font={"size": 13, "color": pal["amber_ink"], "face": _FONT})
    legend = "".join([
        _swatch(pal["rag_node"], "entity"),
        _swatch(pal["amber"], "sent to the AI", ring=True),
        _swatch(pal["conflict"], "changed fact still stored as true"),
    ])
    return _html(net, pal, legend)


def graph_rag_stats(assistant, answer: dict | None, conflicts: list[dict]) -> list[dict]:
    """Counters for the bottom panel: [{value, label, note?, tone?}]."""
    triples = len(assistant.edges())
    items = [
        {"value": f"{triples:,}", "label": _plural(triples, "triple in memory", "triples in memory")},
        {"value": f"{len(conflicts):,}",
         "label": _plural(len(conflicts), "conflict stored as true", "conflicts stored as true"),
         "tone": "signal" if conflicts else None},
    ]
    if answer:
        mem = answer.get("extra", {}).get("memory_tokens", "?")
        items.append({"value": f"{answer['prompt_tokens']:,}", "label": "tokens sent",
                      "note": f"{mem} from its keyword matches"})
    return items
