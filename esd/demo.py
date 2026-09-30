"""Load the shared "background life" into memories (used by the app and the evaluation)."""
import hashlib
import json
import shutil
from concurrent.futures import ThreadPoolExecutor

from . import config

BACKGROUND_PATH = config.EVAL_DIR / "background.json"
SNAPSHOT_FILES = ["esd.json", "graph_rag.json"]


def load_background() -> list[dict]:
    return json.loads(BACKGROUND_PATH.read_text(encoding="utf-8"))


# Code that decides what gets written into memory. If any of it changes,
# saved memories (demo snapshot, evaluation cache) are rebuilt.
MEMORY_CODE = ["esd/extractor.py", "esd/revision.py", "esd/graph_store.py", "esd/models.py",
               "baselines/graph_rag.py", "baselines/simple.py"]


def background_hash() -> str:
    """Fingerprint of the background life, the memory-writing code and the models."""
    # Line endings are normalised so a Windows and a Linux checkout give the same fingerprint.
    h = hashlib.sha1(BACKGROUND_PATH.read_bytes().replace(b"\r\n", b"\n"))
    h.update(f"{config.CHAT_MODEL}|{config.EMBED_MODEL}|{config.TEMPERATURE}".encode())
    for rel in MEMORY_CODE:
        h.update((config.ROOT / rel).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


def ingest(assistants: list, messages: list[dict], progress=None) -> None:
    """Feed messages, in order, to every assistant (the assistants run in parallel)."""
    with ThreadPoolExecutor(max(1, len(assistants))) as pool:
        for i, m in enumerate(messages, start=1):
            list(pool.map(lambda a: a.observe(m["text"], m["date"]), assistants))
            if progress:
                progress(i, len(messages))


def snapshot_ready() -> bool:
    meta = config.SNAPSHOT_DIR / "meta.json"
    if not meta.exists() or not all((config.SNAPSHOT_DIR / f).exists() for f in SNAPSHOT_FILES):
        return False
    return json.loads(meta.read_text(encoding="utf-8")).get("background") == background_hash()


def save_snapshot() -> None:
    config.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for f in SNAPSHOT_FILES:
        shutil.copy(config.MEMORY_DIR / f, config.SNAPSHOT_DIR / f)
    (config.SNAPSHOT_DIR / "meta.json").write_text(json.dumps({"background": background_hash()}), encoding="utf-8")


def restore_snapshot() -> None:
    config.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    for f in SNAPSHOT_FILES:
        shutil.copy(config.SNAPSHOT_DIR / f, config.MEMORY_DIR / f)
