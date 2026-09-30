"""Data shapes shared by the whole project."""
from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal["constraint", "decision", "event", "fact"]


# --- What the extractor returns (OpenAI structured output) -----------------
# Structured outputs need every field required and no defaults,
# so optional values are typed `X | None` instead.
class ExtractedFact(BaseModel):
    kind: Kind
    statement: str
    slot: str | None
    entities: list[str]
    triggers: list[str]
    valid_from: str | None


class Extraction(BaseModel):
    facts: list[ExtractedFact]


# --- What we store ---------------------------------------------------------
class Fact(BaseModel):
    id: str
    kind: Kind
    statement: str
    slot: str | None = None
    entities: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)
    # Valid time: when this was true in the user's life.
    valid_from: str
    valid_to: str | None = None
    # Transaction time: when we learned it, and when we stopped believing it.
    recorded_at: str
    invalidated_at: str | None = None
    superseded_by: str | None = None
    mentions: int = 1
    last_seen: str | None = None
    source: str = ""

    def embed_text(self) -> str:
        if self.triggers:
            return f"{self.statement} | {', '.join(self.triggers)}"
        return self.statement

    @property
    def is_old(self) -> bool:
        return self.superseded_by is not None


class Hit(BaseModel):
    fact_id: str
    statement: str
    kind: Kind
    score: float
    reason: str
    via: str | None = None  # the concept that linked the question to this fact
    through: str | None = None  # entity id the graph walk reached this fact through


class Answer(BaseModel):
    text: str
    prompt_tokens: int = 0
    latency_s: float = 0.0
    card: str | None = None  # the memory text that was sent (card, triples, messages...)
    used: list[str] = Field(default_factory=list)  # node/edge ids that were sent
    extra: dict = Field(default_factory=dict)
