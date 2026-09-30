"""Thin helpers around the OpenAI API: chat, structured output, cached embeddings."""
import hashlib
import logging
import sqlite3
import threading

import numpy as np
import openai
import tiktoken
from openai import OpenAI

from . import config

log = logging.getLogger("esd.llm")

_client: OpenAI | None = None
_client_lock = threading.Lock()
_emb_lock = threading.Lock()
_emb_mem: dict[str, np.ndarray] = {}
_emb_db: sqlite3.Connection | None = None
_enc = tiktoken.get_encoding("o200k_base")

USAGE = {"prompt_tokens": 0, "completion_tokens": 0, "embedding_tokens": 0, "calls": 0}
_usage_lock = threading.Lock()


class MissingKeyError(RuntimeError):
    pass


# Errors that mean "stop and tell the user" rather than "skip this one item".
_FATAL = (
    MissingKeyError,
    openai.AuthenticationError,
    openai.PermissionDeniedError,
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.NotFoundError,
)


def client() -> OpenAI:
    global _client
    with _client_lock:
        if _client is None:
            if not config.OPENAI_API_KEY or config.OPENAI_API_KEY.startswith("sk-..."):
                raise MissingKeyError(
                    "OPENAI_API_KEY is missing. Copy .env.example to .env and add your key."
                )
            _client = OpenAI(api_key=config.OPENAI_API_KEY, max_retries=5, timeout=90)
        return _client


def _track(usage, embedding: bool = False) -> None:
    if usage is None:
        return
    with _usage_lock:
        USAGE["calls"] += 1
        if embedding:
            USAGE["embedding_tokens"] += getattr(usage, "total_tokens", 0) or 0
        else:
            USAGE["prompt_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
            USAGE["completion_tokens"] += getattr(usage, "completion_tokens", 0) or 0


def _temperature_kwargs(temperature: float | None) -> dict:
    if config.TEMPERATURE is None:
        return {}
    return {"temperature": config.TEMPERATURE if temperature is None else temperature}


def chat(messages: list[dict], temperature: float | None = None) -> tuple[str, int]:
    """Return (reply text, prompt tokens actually billed)."""
    resp = client().chat.completions.create(
        model=config.CHAT_MODEL, messages=messages, **_temperature_kwargs(temperature)
    )
    _track(resp.usage)
    prompt_tokens = resp.usage.prompt_tokens if resp.usage else count_messages(messages)
    return resp.choices[0].message.content or "", prompt_tokens


def parse(messages: list[dict], schema, default):
    """Structured output parsed into `schema`; returns `default` if the model output is unusable."""
    try:
        resp = client().chat.completions.parse(
            model=config.CHAT_MODEL,
            messages=messages,
            response_format=schema,
            **_temperature_kwargs(0.0),
        )
        _track(resp.usage)
        parsed = resp.choices[0].message.parsed
        return parsed if parsed is not None else default
    except _FATAL:
        raise
    except Exception as e:  # malformed output, refusals, length limits...
        log.warning("structured output failed (%s): %s", schema.__name__, e)
        return default


# --- Embeddings with a SQLite disk cache --------------------------------------
def _db() -> sqlite3.Connection:
    global _emb_db
    if _emb_db is None:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        _emb_db = sqlite3.connect(config.EMB_CACHE_PATH, check_same_thread=False)
        _emb_db.execute("CREATE TABLE IF NOT EXISTS emb (key TEXT PRIMARY KEY, vec BLOB)")
    return _emb_db


def _key(text: str) -> str:
    return hashlib.sha1(f"{config.EMBED_MODEL}|{text}".encode("utf-8")).hexdigest()


def _lookup(keys: list[str]) -> None:
    """Pull any keys not yet in memory from the disk cache (caller holds the lock)."""
    todo = [k for k in keys if k not in _emb_mem]
    for i in range(0, len(todo), 500):
        chunk = todo[i : i + 500]
        rows = _db().execute(
            f"SELECT key, vec FROM emb WHERE key IN ({','.join('?' * len(chunk))})", chunk
        ).fetchall()
        for k, blob in rows:
            _emb_mem[k] = np.frombuffer(blob, dtype=np.float32)


def embed(texts: list[str]) -> np.ndarray:
    """Embed texts, reusing cached vectors. Returns an (n, d) float32 array."""
    if not texts:
        return np.zeros((0, 1), dtype=np.float32)
    texts = [t if t.strip() else "(empty)" for t in texts]
    keys = [_key(t) for t in texts]
    with _emb_lock:
        _lookup(keys)
        missing = list(dict.fromkeys(t for t, k in zip(texts, keys) if k not in _emb_mem))
    for i in range(0, len(missing), 256):
        batch = missing[i : i + 256]
        resp = client().embeddings.create(model=config.EMBED_MODEL, input=batch)
        _track(resp.usage, embedding=True)
        with _emb_lock:
            rows = []
            for text, item in zip(batch, resp.data):
                vec = np.asarray(item.embedding, dtype=np.float32)
                _emb_mem[_key(text)] = vec
                rows.append((_key(text), vec.tobytes()))
            _db().executemany("INSERT OR REPLACE INTO emb VALUES (?, ?)", rows)
            _db().commit()
    with _emb_lock:
        return np.stack([_emb_mem[k] for k in keys])


def cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Pairwise cosine similarity between rows of a (n, d) and b (m, d) -> (n, m)."""
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)), dtype=np.float32)
    a = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
    b = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return a @ b.T


def count_tokens(text: str) -> int:
    return len(_enc.encode(text or ""))


def count_messages(messages: list[dict]) -> int:
    return sum(count_tokens(m.get("content", "")) + 4 for m in messages) + 2
