"""Saving and loading the demo app's chats and simulated date."""
import json
import uuid
from datetime import date

from . import config


def new_chat(ts: str) -> dict:
    return {"id": "c_" + uuid.uuid4().hex[:8], "title": "New chat", "created": ts, "messages": []}


def load_chats() -> dict[str, dict]:
    chats = {}
    if config.CHATS_DIR.exists():
        for p in config.CHATS_DIR.glob("*.json"):
            chat = json.loads(p.read_text(encoding="utf-8"))
            chats[chat["id"]] = chat
    return chats


def save_chat(chat: dict) -> None:
    config.CHATS_DIR.mkdir(parents=True, exist_ok=True)
    (config.CHATS_DIR / f"{chat['id']}.json").write_text(json.dumps(chat, indent=1), encoding="utf-8")


def delete_chat(chat_id: str) -> None:
    p = config.CHATS_DIR / f"{chat_id}.json"
    if p.exists():
        p.unlink()


def load_state() -> dict:
    if config.STATE_PATH.exists():
        return json.loads(config.STATE_PATH.read_text(encoding="utf-8"))
    return {"sim_date": date.today().isoformat()}


def save_state(state: dict) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.STATE_PATH.write_text(json.dumps(state), encoding="utf-8")
