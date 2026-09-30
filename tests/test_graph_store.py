from esd.graph_store import MemoryGraph
from esd.models import Fact


def _fact(fid, statement, slot, ts, entities, kind="decision"):
    return Fact(id=fid, kind=kind, statement=statement, slot=slot, entities=entities, valid_from=ts, recorded_at=ts)


def test_supersede_keeps_old_fact_and_closes_it(tmp_path):
    g = MemoryGraph()
    g.add_fact(_fact("f_pg", "Project uses PostgreSQL", "project.database", "2025-02-20", ["postgresql"]))
    g.add_fact(_fact("f_mg", "Project uses MongoDB", "project.database", "2025-03-03", ["mongodb"]))
    g.supersede("f_pg", "f_mg", "2025-03-03")

    assert [f.id for f in g.active_facts("2025-03-10")] == ["f_mg"]
    assert [f.id for f in g.history("project.database")] == ["f_pg", "f_mg"]
    old = g.facts["f_pg"]
    assert old.valid_to == "2025-03-03" and old.invalidated_at == "2025-03-03" and old.superseded_by == "f_mg"
    assert [f.id for f in g.predecessors("f_mg")] == ["f_pg"]
    assert [(o.id, n.id) for o, n in g.changes()] == [("f_pg", "f_mg")]

    path = tmp_path / "m.json"
    g.save(path)
    g2 = MemoryGraph.load(path)
    assert set(g2.facts) == {"f_pg", "f_mg"}
    assert [f.id for f in g2.active_facts()] == ["f_mg"]
    assert [f.id for f in g2.predecessors("f_mg")] == ["f_pg"]


def test_valid_time_of_old_fact_ends_when_new_one_became_true():
    g = MemoryGraph()
    g.add_fact(_fact("f_ctg", "User lives in Chittagong", "user.home_city", "2025-02-18", ["chittagong"], "fact"))
    g.add_fact(_fact("f_dhk", "User lives in Dhaka", "user.home_city", "2025-03-01", ["dhaka"], "fact"))
    g.supersede("f_ctg", "f_dhk", "2025-03-10")  # told on 10 March, true since 1 March
    assert g.facts["f_ctg"].valid_to == "2025-03-01"
    assert g.facts["f_ctg"].invalidated_at == "2025-03-10"


def test_bump_counts_mentions_and_entities_are_shared():
    g = MemoryGraph()
    g.add_fact(_fact("f1", "Rina is user's sister", "rina.relation", "2025-02-20", ["Rina", "sister"], "fact"))
    g.add_fact(_fact("f2", "Rina dislikes chocolate", "rina.food", "2025-02-22", ["rina", "chocolate"], "fact"))
    g.bump("f1", "2025-03-01")
    assert g.facts["f1"].mentions == 2 and g.facts["f1"].last_seen == "2025-03-01"
    assert "e:rina" in g.fact_entity_ids("f1") and "e:rina" in g.fact_entity_ids("f2")
