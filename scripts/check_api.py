"""T0 check: can we reach OpenAI with the key in .env?"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from esd import config, llm  # noqa: E402

text, tokens = llm.chat([{"role": "user", "content": "Say hello in five words."}])
print(f"chat ({config.CHAT_MODEL}): {text!r}  [{tokens} prompt tokens]")
vec = llm.embed(["hello world"])
print(f"embedding ({config.EMBED_MODEL}): length {vec.shape[1]}")
llm.embed(["hello world"])
print(f"second embed of the same text used the cache: API calls so far = {llm.USAGE['calls']} (expected 2)")
