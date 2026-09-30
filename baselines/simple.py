"""The three simpler comparison assistants."""
import json

import numpy as np

from esd import llm
from esd.base import BaseAssistant

TOP_K = 5


class _LogAssistant(BaseAssistant):
    """Keeps a plain log of (date, message)."""

    def load(self) -> None:
        self.log: list[tuple[str, str]] = []
        if self.path and self.path.exists():
            self.log = [tuple(x) for x in json.loads(self.path.read_text(encoding="utf-8"))]

    def save(self) -> None:
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.log), encoding="utf-8")

    def observe(self, msg: str, ts: str) -> list:
        self.log.append((ts, msg))
        self.save()
        return []


class NoMemoryAssistant(BaseAssistant):
    """Only sees the recent messages of the current chat."""

    key = "no_memory"
    name = "No memory"
    label = "MEMORY (none: only the recent messages)"


class FullHistoryAssistant(_LogAssistant):
    """Pastes every past message into the prompt."""

    key = "full_history"
    name = "Full history"
    label = "FULL CONVERSATION HISTORY"

    def memory_block(self, question: str, ts: str) -> tuple[str, list[str], dict]:
        return "\n".join(f"[{d}] {m}" for d, m in self.log), [], {}


class VectorRAGAssistant(_LogAssistant):
    """Standard dense-vector RAG: top-k past messages by cosine similarity."""

    key = "vector_rag"
    name = "Vector RAG"
    label = "RETRIEVED PAST MESSAGES"

    def memory_block(self, question: str, ts: str) -> tuple[str, list[str], dict]:
        if not self.log:
            return "", [], {}
        sims = llm.cosine_matrix(llm.embed([question]), llm.embed([m for _, m in self.log]))[0]
        top = [int(i) for i in np.argsort(-sims)[:TOP_K]]
        block = "\n".join(f"[{self.log[i][0]}] {self.log[i][1]}" for i in top)
        return block, [str(i) for i in top], {"scores": [round(float(sims[i]), 3) for i in top]}
