"""T6 check: our memory working end to end in the terminal (Checkpoint A).

Tells the assistant about a nut allergy and a database choice, changes the
database, chats about other things, then asks two questions weeks later.
Uses a throwaway memory, so the app's saved memory is not touched.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from esd import llm  # noqa: E402
from esd.chat import ESDAssistant  # noqa: E402
from eval.fillers import FILLERS  # noqa: E402

story = [
    ("2025-02-20", "Heads up for the future: I'm allergic to nuts, both peanuts and tree nuts."),
    ("2025-02-20", "For the new invoicing service we decided to use PostgreSQL."),
    *[("2025-02-21", f) for f in FILLERS[:6]],
    ("2025-03-03", "Change of plan: we're switching the invoicing service to MongoDB instead of PostgreSQL."),
    *[("2025-03-04", f) for f in FILLERS[6:16]],
]
questions = [
    ("2025-03-06", "Give me a recipe for macarons I can bake this weekend."),
    ("2025-03-06", "Write the Python code to connect the invoicing service to its database."),
]

esd = ESDAssistant(path=None)
for ts, msg in story:
    actions = esd.observe(msg, ts)
    for a in actions:
        extra = f"  (replaced: {a['old']})" if a["action"] == "replaced" else ""
        print(f"[{ts}] {a['action']:>8}: {a['fact']}{extra}")

recent = [{"role": "user", "content": m} for _, m in story[-4:]]
for ts, q in questions:
    ans = esd.answer(q, ts, recent)
    print("\n" + "=" * 80 + f"\nQ: {q}\n" + "-" * 80)
    print(ans.card)
    print("-" * 80 + f"\nWhy: " + "; ".join(f"{h['statement']} [{h['reason']}]" for h in ans.extra["hits"][:5]))
    print("-" * 80 + f"\n{ans.text}\n[{ans.prompt_tokens} tokens sent, {ans.latency_s}s]")

print(f"\nAPI use: {llm.USAGE}")
