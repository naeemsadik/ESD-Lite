"""The answer prompt shared by every assistant, so the comparison is fair.

The only thing that differs between assistants is the memory block they
put under the line.
"""

ASSISTANT_PROMPT = """You are a helpful personal assistant with long-term memory of earlier conversations with this user.
Today's date is {ts}.

Below the line is your memory ({label}). Use it:
- Always respect the user's constraints and rules (allergies, diets, budgets, schedules, commitments). Before answering, check every item you suggest (ingredients, products, prices, times, activities) against them and replace anything that breaks one. If a rule affects your answer, say so briefly.
- If memory contains conflicting information, go with the most recent.
- Use dates to reason about time.
- If memory doesn't cover something, just answer normally.
- Keep answers concise.

----- {label} -----
{block}"""


def build_messages(ts: str, label: str, block: str, recent: list[dict], question: str) -> list[dict]:
    system = ASSISTANT_PROMPT.format(ts=ts, label=label, block=block.strip() or "(empty)")
    return (
        [{"role": "system", "content": system}]
        + [{"role": m["role"], "content": m["content"]} for m in recent]
        + [{"role": "user", "content": question}]
    )
