"""All settings in one place. Values can be overridden in .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CHAT_MODEL = os.getenv("ESD_CHAT_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("ESD_EMBED_MODEL", "text-embedding-3-small")

_temp = os.getenv("ESD_TEMPERATURE", "0").strip().lower()
TEMPERATURE = None if _temp in ("", "none") else float(_temp)

# Size of the Memory Card (our text stand-in for the spec's K=64 soft prefix).
CARD_TOKEN_BUDGET = int(os.getenv("ESD_CARD_TOKEN_BUDGET", "300"))
# How many of the current chat's latest messages every assistant sees.
RECENT_TURNS = 4
# Upper limit on the triples the standard Graph RAG baseline may paste in.
GRAPH_RAG_TOKEN_CAP = 2000

# Fading speed per fact kind, per day since the fact was last mentioned
# (hand-set stand-in for the spec's learned lambda_r).
DECAY = {"constraint": 0.0, "decision": 0.005, "fact": 0.01, "event": 0.01}

DATA_DIR = Path(os.getenv("ESD_DATA_DIR", ROOT / "data"))
CHATS_DIR = DATA_DIR / "chats"
MEMORY_DIR = DATA_DIR / "memory"
SNAPSHOT_DIR = DATA_DIR / "demo_snapshot"
EMB_CACHE_PATH = DATA_DIR / "emb_cache.sqlite"
STATE_PATH = DATA_DIR / "state.json"
EVAL_DIR = ROOT / "eval"
RESULTS_DIR = Path(os.getenv("ESD_RESULTS_DIR", ROOT / "results"))
