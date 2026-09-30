"""Step 1, Listen: turn one user message into typed facts (spec 4.1)."""
from . import llm
from .models import Extraction, ExtractedFact

SYSTEM = """You are the memory writer for a personal AI assistant. Read ONE user message and extract only information worth remembering for weeks or months.

Kinds:
- constraint: a lasting rule, limit or restriction the assistant must respect: allergies, diets, budgets, deadlines, health limits, "never/always do X", commitments that rule things out.
- decision: a choice the user has made: tools, frameworks, databases, plans, purchases.
- event: something that happened or will happen at a particular time: moved house, started a job, a trip, a birthday.
- fact: any other lasting fact about the user or the people and things in their life: relationships, likes and dislikes, job, pets, habits.

Rules:
- Greetings, chit-chat, questions and requests with no lasting information -> return an empty list.
- Be faithful: record what the user actually said. Never turn a dislike or preference into an allergy, a medical condition or a rule, and never add details the user did not state. Likes, dislikes and preferences are "fact", unless the user states them as a rule to follow.
- statement: short, third person, self-contained. Name people with their relation, e.g. "User works as a nurse", "Sam (user's brother) is vegan".
- slot: a short, stable snake_case topic key such as "user.diet", "project.frontend_framework", "user.home_city", "sam.job". If one of the KNOWN SLOTS fits, reuse it exactly. Use the same slot when a statement updates or replaces an earlier one on the same topic.
- entities: the key people and things mentioned, lowercase and singular (e.g. "sam", "react", "lactose"). Use "user" only if nothing else fits.
- triggers: for constraints and decisions, list 6-10 concrete situations, objects, foods, activities or requests where this will matter later, including non-obvious ones. Example: lactose intolerance -> pizza, ice cream, latte, cheesecake, paneer, creamy sauces, milkshakes, chocolate bars. For facts and events, add 2-5 triggers only if the fact clearly matters in specific situations, otherwise [].
- valid_from: ISO date (YYYY-MM-DD) when this became true in the user's life. Resolve relative dates ("last March", "since yesterday") using TODAY. If unknown, use TODAY."""


def extract(user_msg: str, ts: str, known_slots: list[str]) -> list[ExtractedFact]:
    user = (
        f"TODAY: {ts}\n"
        f"KNOWN SLOTS: {', '.join(known_slots) if known_slots else '(none)'}\n\n"
        f"USER MESSAGE:\n{user_msg}"
    )
    result = llm.parse(
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
        Extraction,
        default=Extraction(facts=[]),
    )
    return result.facts
