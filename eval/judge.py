"""The examiner AI: marks one answer pass/fail against a scenario's checklist."""
from pydantic import BaseModel

from esd import llm


class Verdict(BaseModel):
    passed: bool
    reason: str


SYSTEM = """You are a strict, fair examiner. You check whether an AI assistant's answer meets a pass/fail criterion.
Judge only against the criterion. Ignore style, length and politeness.
Give a one-sentence reason."""


def judge(question: str, answer: str, criteria: str) -> Verdict:
    return llm.parse(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"QUESTION:\n{question}\n\nANSWER:\n{answer}\n\nCRITERION:\n{criteria}"},
        ],
        Verdict,
        default=Verdict(passed=False, reason="examiner output could not be parsed"),
    )
