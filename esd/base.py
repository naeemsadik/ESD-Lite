"""The interface every assistant follows (ours and the baselines).

observe() hears a user message; answer() replies. All assistants share the
same answer prompt and model; only memory_block() differs.
"""
import time
from pathlib import Path

from . import llm
from .models import Answer
from .prompts import build_messages


class BaseAssistant:
    key = "base"
    name = "Base"
    label = "MEMORY"

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.load()

    # Subclasses override these -----------------------------------------------
    def load(self) -> None:
        pass

    def save(self) -> None:
        pass

    def observe(self, msg: str, ts: str) -> list:
        return []

    def memory_block(self, question: str, ts: str) -> tuple[str, list[str], dict]:
        """Return (memory text to send, ids of what was sent, extra info for the UI)."""
        return "", [], {}

    # Shared ------------------------------------------------------------------
    def answer(self, question: str, ts: str, recent: list[dict]) -> Answer:
        start = time.perf_counter()
        block, used, extra = self.memory_block(question, ts)
        messages = build_messages(ts, self.label, block, recent, question)
        text, prompt_tokens = llm.chat(messages)
        extra.setdefault("memory_tokens", llm.count_tokens(block))
        return Answer(
            text=text,
            prompt_tokens=prompt_tokens,
            latency_s=round(time.perf_counter() - start, 2),
            card=block,
            used=used,
            extra=extra,
        )

    def reset(self) -> None:
        if self.path and self.path.exists():
            self.path.unlink()
        self.load()
