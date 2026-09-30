import json

from baselines.graph_rag import GraphRAGAssistant, Keywords, Triple, Triples
from esd.graph_store import MemoryGraph
from esd.models import Fact
from esd.visualize import MAX_NODES, draw_esd, draw_graph_rag

from .fakes import install

TRIPLES = {
    "We use PostgreSQL": [Triple(subject="invoicing service", relation="uses", object="postgresql")],
    "Switching to MongoDB": [Triple(subject="invoicing service", relation="switches to", object="mongodb")],
}


def fake_parse(messages, schema, default):
    if schema is Triples:
        return Triples(triples=TRIPLES.get(messages[-1]["content"], []))
    if schema is Keywords:
        return Keywords(keywords=["invoicing service", "database"])
    return default


def _esd_graph() -> MemoryGraph:
    g = MemoryGraph()
    g.add_fact(Fact(id="f_pg", kind="decision", statement="Invoicing service uses PostgreSQL",
                    entities=["invoicing service", "postgresql"], valid_from="2025-02-20", recorded_at="2025-02-20"))
    g.add_fact(Fact(id="f_mg", kind="decision", statement="Invoicing service uses MongoDB",
                    entities=["invoicing service", "mongodb"], valid_from="2025-03-03", recorded_at="2025-03-03"))
    g.supersede("f_pg", "f_mg", "2025-03-03")
    return g


def test_graph_rag_keeps_both_facts_and_reports_conflict(monkeypatch, tmp_path):
    install(monkeypatch, fake_parse)
    a = GraphRAGAssistant(path=tmp_path / "grag.json")
    a.observe("We use PostgreSQL", "2025-02-20")
    a.observe("We use PostgreSQL", "2025-02-21")  # exact duplicate is skipped
    a.observe("Switching to MongoDB", "2025-03-03")
    assert len(a.edges()) == 2

    block, used, extra = a.memory_block("Write the database connection code", "2025-03-17")
    assert "postgresql" in block and "mongodb" in block  # both still "true"
    assert "invoicing service" in extra["matched"]

    conflicts = a.conflicts(_esd_graph().changes())
    assert len(conflicts) == 1
    assert conflicts[0]["stale_edges"] and conflicts[0]["fresh_edges"]

    reloaded = GraphRAGAssistant(path=tmp_path / "grag.json")
    assert len(reloaded.edges()) == 2


def test_both_graphs_render(monkeypatch):
    install(monkeypatch, fake_parse)
    g = _esd_graph()
    answer = {"used": ["f_mg"], "prompt_tokens": 400,
              "extra": {"hits": [{"fact_id": "f_mg", "via": "database"}],
                        "seed_entities": {"e:mongodb": {"via": "database", "score": 0.5}}, "card_tokens": 60}}
    html = draw_esd(g, answer, "Write the database code", height=280)
    assert "vis-network" in html and "replaced by" in html and "(old)" in html

    a = GraphRAGAssistant(path=None)
    a.observe("We use PostgreSQL", "2025-02-20")
    a.observe("Switching to MongoDB", "2025-03-03")
    html = draw_graph_rag(a, None, a.conflicts(g.changes()), None, height=280)
    assert "vis-network" in html and "#e5484d" in html


def test_both_panels_share_the_node_limit_and_esd_draws_the_path(monkeypatch):
    install(monkeypatch, fake_parse)
    g = MemoryGraph()
    g.add_fact(Fact(id="f_sister", kind="fact", statement="Rina is the user's sister", entities=["rina", "sister"],
                    valid_from="2025-02-20", recorded_at="2025-02-20"))
    g.add_fact(Fact(id="f_choc", kind="fact", statement="Rina dislikes chocolate", entities=["rina", "chocolate"],
                    valid_from="2025-02-22", recorded_at="2025-02-22"))
    for i in range(80):
        g.add_fact(Fact(id=f"f_{i}", kind="fact", statement=f"Fact {i}", entities=[f"thing{i}"],
                        valid_from="2025-01-01", recorded_at="2025-01-01"))
    answer = {"used": ["f_sister", "f_choc"], "prompt_tokens": 300, "extra": {
        "hits": [{"fact_id": "f_sister", "via": "sister"}, {"fact_id": "f_choc", "via": None, "through": "e:rina"}],
        "seed_entities": {}}}
    html = draw_esd(g, answer, "What cake for my sister?", height=280)
    nodes = html.split("nodes = new vis.DataSet(")[1].split(");")[0]
    assert nodes.count('"id":') <= MAX_NODES + 1  # limit, plus the question star
    drawn = json.loads(html.split("edges = new vis.DataSet(")[1].split(");")[0])
    gold = {(e["from"], e["to"]) for e in drawn if e.get("color") == "#f5a623"}
    # question -> matched fact -> shared entity -> linked fact, all in gold
    assert {("Q", "f_sister"), ("f_sister", "e:rina"), ("f_choc", "e:rina")} <= gold

    a = GraphRAGAssistant(path=None)
    for i in range(80):
        a._add(f"thing{i}", "relates to", f"other{i}", "2025-01-01")
    html = draw_graph_rag(a, None, [], None, height=280)
    nodes = html.split("nodes = new vis.DataSet(")[1].split(");")[0]
    assert nodes.count('"id":') <= MAX_NODES
