"""Live check of the "replaced-by" judgement on known cases (needs the API key)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from esd import llm  # noqa: E402
from esd.revision import SYSTEM, RevisionResult  # noqa: E402

CASES = [
    ("User will lead the payments API refactor.", "The payments API refactor has to be done by the end of February.", "unrelated"),
    ("User decided to use PostgreSQL for the invoicing service.", "User is switching the invoicing service to MongoDB instead of PostgreSQL.", "replaces"),
    ("User has been vegetarian for two years, eating no meat and no fish.", "User has started eating fish again but still eats no other meat.", "replaces"),
    ("User lives in Chittagong near the port area.", "User moved from Chittagong to Dhaka at the start of March for work.", "replaces"),
    ("User is allergic to nuts, both peanuts and tree nuts.", "User has a serious nut allergy to peanuts and tree nuts.", "same"),
    ("User has a cat named Miso.", "Miso needs her yearly vaccine next month.", "unrelated"),
]

correct = 0
for old, new, want in CASES:
    result = llm.parse(
        [{"role": "system", "content": SYSTEM},
         {"role": "user", "content": f"TODAY: 2025-03-10\nNEW: {new}\n\nEXISTING:\n0. {old} (since 2025-02-01)"}],
        RevisionResult, RevisionResult(judgements=[]),
    )
    got = result.judgements[0].relation if result.judgements else "?"
    correct += got == want
    print(f"{'OK ' if got == want else 'BAD'}  expected {want:<9} got {got:<9}  {old}  ->  {new}")
print(f"{correct}/{len(CASES)} correct")
