"""An offline stand-in for OpenAI, so tests run without a key or network."""
import re
import zlib

import numpy as np

from esd import llm

DIM = 512
_STOP = {"the", "a", "an", "is", "of", "to", "for", "and", "i", "my", "user", "should", "what", "get", "in"}


def _words(text: str) -> list[str]:
    words = re.findall(r"[a-z]+", text.lower())
    return [w[:-1] if w.endswith("s") and len(w) > 3 else w for w in words if w not in _STOP]


def fake_embed(texts: list[str]) -> np.ndarray:
    out = np.zeros((len(texts), DIM), dtype=np.float32)
    for i, t in enumerate(texts):
        for w in _words(t):
            out[i, zlib.crc32(w.encode()) % DIM] += 1.0
        if not out[i].any():
            out[i, 0] = 1.0
    return out


def install(monkeypatch, parse_fn=None) -> None:
    monkeypatch.setattr(llm, "embed", fake_embed)
    monkeypatch.setattr(llm, "chat", lambda messages, temperature=None: ("fake answer", llm.count_messages(messages)))
    if parse_fn:
        monkeypatch.setattr(llm, "parse", parse_fn)
