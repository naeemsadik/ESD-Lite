"""ESD Memory demo screen.

Left 70%: chat with our assistant (multiple chats, simulated date).
Right 30%: our memory graph (top) and the standard Graph RAG graph (bottom),
both built from exactly the same messages.

Run with:  streamlit run app.py
"""
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import streamlit as st

from baselines.graph_rag import GraphRAGAssistant
from esd import config, demo, llm
from esd.chat import ESDAssistant
from esd.chats import delete_chat, load_chats, load_state, new_chat, save_chat, save_state
from esd.visualize import (
    draw_esd,
    draw_graph_rag,
    esd_stats,
    graph_rag_stats,
)

CHAT_HEIGHT = 610
PANEL_HEIGHT = 440
GRAPH_HEIGHT = 278
ENLARGED_HEIGHT = 620

st.set_page_config(page_title="ESD Memory", page_icon="🧠", layout="wide", initial_sidebar_state="collapsed")
st.markdown(
    """<style>
    [data-testid="stMainBlockContainer"], .block-container {padding-top: 2.6rem; padding-bottom: 0.5rem;}
    [data-testid="stChatMessage"] {padding: 0.45rem 0.7rem;}
    </style>""",
    unsafe_allow_html=True,
)

ss = st.session_state


# --- state -------------------------------------------------------------------
def _newest_chat_id() -> str:
    return max(ss.chats.values(), key=lambda c: c.get("order", 0))["id"]


def _create_chat() -> str:
    chat = new_chat(ss.sim_date.isoformat())
    chat["order"] = time.time()
    ss.chats[chat["id"]] = chat
    save_chat(chat)
    return chat["id"]


def _init() -> None:
    if ss.get("ready"):
        return
    ss.esd = ESDAssistant(config.MEMORY_DIR / "esd.json")
    ss.grag = GraphRAGAssistant(config.MEMORY_DIR / "graph_rag.json")
    state = load_state()
    ss.sim_date = date.fromisoformat(state["sim_date"])
    ss.history_tokens = state.get("history_tokens", 0)  # what a full-history assistant would send
    ss.chats = load_chats()
    ss.current = _newest_chat_id() if ss.chats else _create_chat()
    ss.compare = True
    ss.flash = None
    ss.error = None
    ss.ready = True


_init()


# --- callbacks (run before the page redraws) -----------------------------------
def on_new_chat() -> None:
    ss.current = _create_chat()


def chat_label(chat_id: str) -> str:
    c = ss.chats[chat_id]
    return f"💬 {c['title']}  ·  {c['created']}  ·  #{chat_id[-4:]}"


def on_select_chat() -> None:
    ss.current = next(i for i in ss.chats if chat_label(i) == ss.chat_select)


def _save_state() -> None:
    save_state({"sim_date": ss.sim_date.isoformat(), "history_tokens": ss.history_tokens})


def _history_line(ts: str, text: str) -> int:
    return llm.count_tokens(f"[{ts}] {text}") + 1


def shift_date(days: int) -> None:
    ss.sim_date += timedelta(days=days)
    _save_state()


def on_delete_chat() -> None:
    delete_chat(ss.current)
    ss.chats.pop(ss.current, None)
    ss.current = _newest_chat_id() if ss.chats else _create_chat()


def on_reset_memory() -> None:
    ss.esd.reset()
    ss.grag.reset()
    ss.history_tokens = 0
    _save_state()
    ss.flash = "Both memories cleared."


def on_reset_all() -> None:
    on_reset_memory()
    for chat_id in list(ss.chats):
        delete_chat(chat_id)
    ss.chats = {}
    ss.current = _create_chat()
    ss.flash = "Memories and chats cleared."


# --- actions -----------------------------------------------------------------------
def load_demo_history() -> None:
    try:
        if demo.snapshot_ready():
            demo.restore_snapshot()
            ss.esd.load()
            ss.grag.load()
        else:
            ss.esd.reset()
            ss.grag.reset()
            bar = st.sidebar.progress(0.0, text="Reading the background life into both memories…")
            demo.ingest(
                [ss.esd, ss.grag],
                demo.load_background(),
                progress=lambda i, n: bar.progress(i / n, text=f"{i}/{n} messages"),
            )
            demo.save_snapshot()
        background = demo.load_background()
        ss.sim_date = date.fromisoformat(max(m["date"] for m in background)) + timedelta(days=3)
        ss.history_tokens = sum(_history_line(m["date"], m["text"]) for m in background)
        _save_state()
        ss.flash = "Demo history loaded into both memories."
    except Exception as e:  # show the problem instead of crashing the demo
        ss.error = f"{type(e).__name__}: {e}"
    st.rerun()


def _update_note(actions: list[dict], added: list[str]) -> str:
    counts = {k: sum(a["action"] == k for a in actions) for k in ("added", "replaced", "repeated")}
    note = f"Our memory: +{counts['added']} facts"
    if counts["replaced"]:
        note += f", {counts['replaced']} replaced"
    if counts["repeated"]:
        note += f", {counts['repeated']} repeated"
    return note + f" · Current method: +{len(added)} triples"


def handle_message(prompt: str, box) -> None:
    chat = ss.chats[ss.current]
    ts = ss.sim_date.isoformat()
    recent = [{"role": m["role"], "content": m["content"]} for m in chat["messages"][-config.RECENT_TURNS:]]
    chat["messages"].append({"role": "user", "content": prompt, "ts": ts})
    if chat["title"] == "New chat":
        chat["title"] = prompt if len(prompt) <= 40 else prompt[:39] + "…"
    save_chat(chat)

    with box:
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                with st.spinner("Both methods are answering…"):
                    with ThreadPoolExecutor(2) as pool:
                        ours = pool.submit(ss.esd.answer, prompt, ts, recent)
                        theirs = pool.submit(ss.grag.answer, prompt, ts, recent) if ss.compare else None
                        a_esd = ours.result()
                        a_grag = theirs.result() if theirs else None
                chat["messages"].append({
                    "role": "assistant", "content": a_esd.text, "ts": ts, "question": prompt,
                    "esd": a_esd.model_dump(), "grag": a_grag.model_dump() if a_grag else None,
                })
                save_chat(chat)
                with st.spinner("Updating both memories…"):
                    with ThreadPoolExecutor(2) as pool:
                        f1 = pool.submit(ss.esd.observe, prompt, ts)
                        f2 = pool.submit(ss.grag.observe, prompt, ts)
                        ss.flash = _update_note(f1.result(), f2.result())
                ss.history_tokens += _history_line(ts, prompt)
                _save_state()
            except Exception as e:
                ss.error = f"{type(e).__name__}: {e}"
    st.rerun()


# --- rendering ----------------------------------------------------------------------
def render_details(m: dict) -> None:
    ours, theirs = m.get("esd"), m.get("grag")
    if ours:
        ex = ours.get("extra", {})
        with st.expander(f"Details: our Memory Card ({ex.get('card_tokens', '?')} tokens) and why these facts"):
            st.caption(
                f"Sent to AI: {ours['prompt_tokens']:,} tokens · {ours['latency_s']}s · "
                f"hidden concepts: {', '.join(ex.get('concepts', [])) or '-'}"
            )
            st.code(ours.get("card") or "", language=None)
            hits = ex.get("hits", [])
            if hits:
                used = set(ours.get("used", []))
                st.dataframe(
                    [
                        {"on card": "✓" if h["fact_id"] in used else "", "fact": h["statement"],
                         "why": h["reason"], "score": h["score"]}
                        for h in hits
                    ],
                    hide_index=True,
                )
    if theirs:
        ex = theirs.get("extra", {})
        with st.expander(f"What the current method answered ({theirs['prompt_tokens']:,} tokens sent)"):
            st.markdown(theirs["text"])
            matched = ", ".join(f"{k} ← '{v}'" for k, v in ex.get("matched", {}).items()) or "nothing"
            st.caption(f"Keywords: {', '.join(ex.get('keywords', [])) or '-'} · matched entities: {matched}")
            st.code(theirs.get("card") or "(no knowledge found)", language=None)


with st.sidebar:
    st.subheader("Demo controls")
    st.toggle("Also ask the current method (side-by-side answers)", key="compare")
    if st.button("Load demo history (~40 messages)"):
        load_demo_history()
    st.button("Reset memory (keep chats)", on_click=on_reset_memory)
    st.button("Delete this chat", on_click=on_delete_chat)
    st.button("Reset everything", on_click=on_reset_all)
    st.divider()
    st.caption(f"Model: {config.CHAT_MODEL} · Embeddings: {config.EMBED_MODEL}")
    st.caption(
        f"API use this session: {llm.USAGE['prompt_tokens']:,} prompt + "
        f"{llm.USAGE['completion_tokens']:,} completion tokens"
    )

if ss.flash:
    st.toast(ss.flash)
    ss.flash = None

left, right = st.columns([7, 3], gap="medium")

with left:
    if ss.error:
        st.error(ss.error)
        ss.error = None

    ids = sorted(ss.chats, key=lambda i: ss.chats[i].get("order", 0), reverse=True)
    c1, c2, c3, c4, c5 = st.columns([4.2, 1.5, 1.6, 1.0, 1.1], vertical_alignment="center")
    ss.chat_select = chat_label(ss.current)  # keep the dropdown in step with the open chat
    c1.selectbox("Chat", [chat_label(i) for i in ids], key="chat_select", on_change=on_select_chat,
                 label_visibility="collapsed")
    c2.button("➕ New chat", on_click=on_new_chat)
    c3.markdown(f"📅 **{ss.sim_date.strftime('%d %b %Y')}**")
    c4.button("+1 day", on_click=shift_date, args=(1,))
    c5.button("+1 week", on_click=shift_date, args=(7,))

    chat = ss.chats[ss.current]
    box = st.container(height=CHAT_HEIGHT, border=True)
    with box:
        if not chat["messages"]:
            st.caption(
                "Start chatting. Every message goes into **both** memories on the right: "
                "ours (top) and the current standard method (bottom). "
                "Memory carries over between chats; use the date buttons to jump ahead in time."
            )
        for m in chat["messages"]:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if m["role"] == "assistant":
                    render_details(m)

    prompt = st.chat_input("Type a message…")
    if prompt:
        handle_message(prompt, box)

with right:
    last = next((m for m in reversed(chat["messages"]) if m["role"] == "assistant"), None)
    question = last["question"] if last else None
    ours = last.get("esd") if last else None
    theirs = last.get("grag") if last else None
    conflicts = ss.grag.conflicts(ss.esd.graph.changes())

    panels = {
        "esd": ("🧠 Our method: ESD memory graph",
                lambda h: draw_esd(ss.esd.graph, ours, question, h),
                esd_stats(ss.esd.graph, ours, ss.history_tokens)),
        "grag": ("🕸️ Current method: standard Graph RAG",
                 lambda h: draw_graph_rag(ss.grag, theirs, conflicts, question, h),
                 graph_rag_stats(ss.grag, theirs, conflicts)),
    }

    @st.dialog("Knowledge graph", width="large")
    def enlarge(key: str) -> None:
        title, draw, stats = panels[key]
        st.markdown(f"**{title}**")
        st.iframe(draw(ENLARGED_HEIGHT), height=ENLARGED_HEIGHT)
        st.caption(stats)

    for key, (title, draw, stats) in panels.items():
        with st.container(height=PANEL_HEIGHT, border=True):
            t, b = st.columns([4, 1.25], vertical_alignment="center")
            t.markdown(f"**{title}**")
            if b.button("⤢ Enlarge", key=f"enlarge_{key}"):
                enlarge(key)
            st.iframe(draw(GRAPH_HEIGHT), height=GRAPH_HEIGHT)
            st.caption(stats)
