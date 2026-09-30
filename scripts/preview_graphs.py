"""T8 check: build both graphs from the same short story and save them as HTML.

Writes data/preview_esd.html and data/preview_graph_rag.html. Open them in a
browser: the top graph should show the "replaced by" arrow, the bottom one a
red conflict. Uses throwaway memories, so the app's saved memory is untouched.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from baselines.graph_rag import GraphRAGAssistant  # noqa: E402
from esd import config  # noqa: E402
from esd.chat import ESDAssistant  # noqa: E402
from esd.demo import ingest  # noqa: E402
from esd.visualize import draw_esd, draw_graph_rag, esd_stats, graph_rag_stats  # noqa: E402

story = [
    {"date": "2025-02-20", "text": "Heads up for the future: I'm allergic to nuts, both peanuts and tree nuts."},
    {"date": "2025-02-20", "text": "My sister Rina is turning 25 next month."},
    {"date": "2025-02-20", "text": "For the new invoicing service we decided to use PostgreSQL."},
    {"date": "2025-02-22", "text": "Rina really hates chocolate, she won't touch anything chocolatey."},
    {"date": "2025-03-03", "text": "Change of plan: we're switching the invoicing service to MongoDB instead of PostgreSQL."},
]
question, ts = "What cake should I order for my sister's birthday?", "2025-03-10"

esd, grag = ESDAssistant(path=None), GraphRAGAssistant(path=None)
ingest([esd, grag], story)
ours = esd.answer(question, ts, []).model_dump()
theirs = grag.answer(question, ts, []).model_dump()
conflicts = grag.conflicts(esd.graph.changes())

config.DATA_DIR.mkdir(parents=True, exist_ok=True)
(config.DATA_DIR / "preview_esd.html").write_text(draw_esd(esd.graph, ours, question, 520), encoding="utf-8")
(config.DATA_DIR / "preview_graph_rag.html").write_text(
    draw_graph_rag(grag, theirs, conflicts, question, 520), encoding="utf-8")

print("OUR METHOD:", esd_stats(esd.graph, ours).replace("**", ""))
print("  why:", "; ".join(f"{h['statement']} [{h['reason']}]" for h in ours["extra"]["hits"][:4]))
print("  answer:", ours["text"][:300].replace("\n", " "))
print("CURRENT METHOD:", graph_rag_stats(grag, theirs, conflicts).replace("**", ""))
print("  matched:", theirs["extra"]["matched"])
print("  answer:", theirs["text"][:300].replace("\n", " "))
print(f"Saved {config.DATA_DIR / 'preview_esd.html'} and {config.DATA_DIR / 'preview_graph_rag.html'}")
