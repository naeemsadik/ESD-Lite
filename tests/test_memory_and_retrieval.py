from esd import llm
from esd.chat import ESDAssistant
from esd.graph_store import MemoryGraph
from esd.memory_card import build_card
from esd.models import ExtractedFact, Extraction, Fact, Hit
from esd.retriever import Expansion, retrieve
from esd.revision import RevisionResult, integrate

from .fakes import install

EXPANSIONS = {
    "What cake should I order for my sister's birthday?": ["sister", "birthday", "cake", "dessert"],
    "Give me a recipe for macarons": ["almond flour", "nuts", "baking", "dessert"],
}


def fake_parse(messages, schema, default):
    if schema is Expansion:
        return Expansion(concepts=EXPANSIONS.get(messages[-1]["content"], []))
    if schema is RevisionResult:
        text = messages[-1]["content"]
        new = text.split("NEW:")[1].split("\n")[0].lower()
        n = text.count("\n") - text.split("EXISTING:")[0].count("\n")
        relation = "replaces" if ("switch" in new or "now" in new) else ("same" if "again" in new else "unrelated")
        return RevisionResult(judgements=[{"candidate_index": i, "why": "fake", "relation": relation} for i in range(n)])
    return default


def _graph_with_distractors() -> MemoryGraph:
    g = MemoryGraph()
    facts = [
        ("f_allergy", "constraint", "User is allergic to nuts", ["nut"], ["macarons", "baking", "desserts", "almond flour"]),
        ("f_sister", "fact", "Rina is the user's sister", ["rina", "sister"], []),
        ("f_choc", "fact", "Rina dislikes chocolate", ["rina", "chocolate"], []),
    ] + [(f"f_d{i}", "fact", f"User enjoys hobby number {i} on weekends", [f"hobby{i}"], []) for i in range(25)]
    for fid, kind, st, ents, trig in facts:
        g.add_fact(Fact(id=fid, kind=kind, statement=st, entities=ents, triggers=trig,
                        valid_from="2025-02-20", recorded_at="2025-02-20"))
    return g


def test_graph_walk_finds_multi_hop_fact(monkeypatch):
    install(monkeypatch, fake_parse)
    g = _graph_with_distractors()
    r = retrieve(g, "What cake should I order for my sister's birthday?", "2025-03-10")
    ids = [h.fact_id for h in r.hits]
    # "Rina dislikes chocolate" shares no words with the question: it is reached through the entity "rina".
    assert "f_choc" in ids
    choc = next(h for h in r.hits if h.fact_id == "f_choc")
    assert "rina" in choc.reason
    # Standing rules are always considered.
    assert "f_allergy" in ids


def test_hidden_link_via_triggers(monkeypatch):
    install(monkeypatch, fake_parse)
    g = _graph_with_distractors()
    r = retrieve(g, "Give me a recipe for macarons", "2025-03-06")
    allergy = next(h for h in r.hits if h.fact_id == "f_allergy")
    assert "matched via" in allergy.reason


def test_card_respects_budget_and_shows_replacements():
    g = MemoryGraph()
    g.add_fact(Fact(id="f_pg", kind="decision", statement="Invoicing service uses PostgreSQL",
                    valid_from="2025-02-20", recorded_at="2025-02-20"))
    g.add_fact(Fact(id="f_mg", kind="decision", statement="Invoicing service uses MongoDB",
                    valid_from="2025-03-03", recorded_at="2025-03-03"))
    g.supersede("f_pg", "f_mg", "2025-03-03")
    hits = [Hit(fact_id="f_mg", statement="", kind="decision", score=1.0, reason="")]
    for i in range(60):
        fid = f"f_{i}"
        g.add_fact(Fact(id=fid, kind="fact", statement=f"User likes a fairly long described thing number {i}",
                        valid_from="2025-02-01", recorded_at="2025-02-01"))
        hits.append(Hit(fact_id=fid, statement="", kind="fact", score=0.5 - i / 1000, reason=""))
    card, used = build_card(hits, g, "2025-03-10", budget=300)
    assert llm.count_tokens(card) <= 300
    assert "f_mg" in used and len(used) < len(hits)
    assert 'replaced: "Invoicing service uses PostgreSQL" (2025-02-20 to 2025-03-03)' in card


def test_integrate_adds_replaces_and_repeats(monkeypatch):
    install(monkeypatch, fake_parse)
    g = MemoryGraph()

    def ef(statement, slot):
        return ExtractedFact(kind="decision", statement=statement, slot=slot, entities=[], triggers=[], valid_from=None)

    integrate(g, [ef("Invoicing service uses PostgreSQL", "project.database")], "2025-02-20", "msg1")
    integrate(g, [ef("Invoicing service will switch to MongoDB", "project.database")], "2025-03-03", "msg2")
    assert len(g.facts) == 2 and len(g.active_facts()) == 1
    assert "MongoDB" in g.active_facts()[0].statement

    integrate(g, [ef("Invoicing service uses MongoDB again", "project.database")], "2025-03-05", "msg3")
    assert len(g.facts) == 2
    assert g.active_facts()[0].mentions == 2


def test_esd_assistant_end_to_end_offline(monkeypatch):
    def parse(messages, schema, default):
        if schema is Extraction:
            return Extraction(facts=[ExtractedFact(kind="constraint", statement="User is allergic to nuts",
                                                   slot="user.allergy", entities=["nut"],
                                                   triggers=["macarons", "baking"], valid_from=None)])
        return fake_parse(messages, schema, default)

    install(monkeypatch, parse)
    a = ESDAssistant(path=None)
    a.observe("I'm allergic to nuts", "2025-02-20")
    ans = a.answer("Give me a recipe for macarons", "2025-03-06", recent=[])
    assert "User is allergic to nuts" in ans.card
    assert ans.used and ans.extra["card_tokens"] <= 300
