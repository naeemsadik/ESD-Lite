"""ESD Memory demo screen.

Left 70%: chat with our assistant (multiple chats, simulated date).
Right 30%: our memory graph (top) and the standard Graph RAG graph (bottom),
both built from exactly the same messages.

Run with:  streamlit run app.py
"""
import html
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import streamlit as st

from baselines.graph_rag import GraphRAGAssistant
from esd import config, demo, llm
from esd.chat import ESDAssistant
from esd.chats import delete_chat, load_chats, load_state, new_chat, save_chat, save_state
from esd.visualize import draw_esd, draw_graph_rag, esd_stats, graph_rag_stats

CHAT_HEIGHT = 590
PANEL_HEIGHT = 432
GRAPH_HEIGHT = 276
ENLARGED_HEIGHT = 620

# Interface tokens per theme. The accent belongs to "our method"; the neutral to the current method.
TOKENS = {
    "light": {"accent": "#2A78D6", "neutral": "#8A93A3", "muted": "#5A6376", "signal": "#C8372D",
              "tint": "rgba(42,120,214,.10)", "line": "#D9DFE8"},
    "dark": {"accent": "#3987E5", "neutral": "#6B7483", "muted": "#9AA3B2", "signal": "#E5645A",
             "tint": "rgba(57,135,229,.16)", "line": "#2A313D"},
}

st.set_page_config(page_title="ESD Memory", page_icon=":material/neurology:", layout="wide",
                   initial_sidebar_state="collapsed")

ss = st.session_state
DARK = (st.context.theme.type or "light") == "dark"
T = TOKENS["dark" if DARK else "light"]

st.html(f"""<style>
[data-testid="stMainBlockContainer"] {{ padding-top: 3.9rem; padding-bottom: .75rem; max-width: 1720px; }}
.esd-brand {{ display: flex; align-items: baseline; gap: .9rem; flex-wrap: wrap; }}
.esd-brand .name {{ font-size: 1.45rem; font-weight: 700; letter-spacing: -.01em; }}
.esd-brand .lede {{ color: {T['muted']}; font-size: .95rem; }}
.esd-date {{ text-align: right; line-height: 2.5rem; white-space: nowrap; }}
.esd-date .l {{ color: {T['muted']}; font-size: .85rem; margin-right: .5rem; }}
.esd-date .v {{ font-weight: 700; font-size: 1.05rem; font-variant-numeric: tabular-nums; }}
.st-key-panel_ours {{ box-shadow: inset 3px 0 0 {T['accent']}; }}
.st-key-panel_theirs {{ box-shadow: inset 3px 0 0 {T['neutral']}; }}
.esd-head .name {{ font-weight: 700; font-size: 1rem; }}
.esd-head .tag {{ display: inline-block; margin-left: .45rem; padding: 0 .45rem; border-radius: .4rem;
  font-size: .75rem; font-weight: 700; line-height: 1.5rem; vertical-align: 1px; }}
.esd-head .tag.ours {{ background: {T['tint']}; color: {T['accent']}; }}
.esd-head .tag.theirs {{ border: 1px solid {T['line']}; color: {T['muted']}; }}
.esd-head .desc {{ display: block; color: {T['muted']}; font-size: .82rem; margin-top: .1rem; }}
.esd-stats {{ display: flex; flex-wrap: wrap; gap: .35rem 1.2rem; }}
.esd-stat .v {{ font-weight: 700; font-size: 1.05rem; font-variant-numeric: tabular-nums; }}
.esd-stat .l {{ color: {T['muted']}; font-size: .8rem; margin-left: .3rem; }}
.esd-stat .n {{ color: {T['muted']}; font-size: .75rem; margin-left: .25rem; }}
.esd-stat.signal .v, .esd-stat.signal .l {{ color: {T['signal']}; }}
.esd-meta {{ color: {T['muted']}; font-size: .82rem; margin: -.35rem 0 .1rem; font-variant-numeric: tabular-nums; }}
.esd-col {{ font-weight: 700; padding-left: .55rem; margin-bottom: .2rem; }}
.esd-col.ours {{ box-shadow: inset 3px 0 0 {T['accent']}; }}
.esd-col.theirs {{ box-shadow: inset 3px 0 0 {T['neutral']}; }}
.esd-empty {{ max-width: 34rem; padding: 2.2rem .4rem .6rem; }}
.esd-empty .h {{ font-size: 1.25rem; font-weight: 700; margin-bottom: .4rem; }}
.esd-empty p {{ color: {T['muted']}; margin: 0 0 .5rem; line-height: 1.55; }}
.st-key-panel_ours iframe, .st-key-panel_theirs iframe, [data-testid="stDialog"] iframe {{ border: 1px solid {T['line']} !important; border-radius: .5rem; }}
[data-testid="stChatMessage"] h1, [data-testid="stChatMessage"] h2 {{ font-size: 1.2rem; padding: .6rem 0 .2rem; }}
[data-testid="stChatMessage"] h3, [data-testid="stChatMessage"] h4 {{ font-size: 1.05rem; padding: .5rem 0 .15rem; }}
[data-testid="stSidebar"] .esd-group {{ font-weight: 700; margin: .9rem 0 .15rem; }}
[data-testid="stSidebar"] .esd-group:first-child {{ margin-top: 0; }}
button:active {{ transform: translateY(1px); }}
@media (prefers-reduced-motion: reduce) {{ *, *::before, *::after {{ transition: none !important; animation: none !important; }} }}
</style>""")


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
    day = date.fromisoformat(c["created"]).strftime("%d %b")
    return f"{c['title']}  ({day}, #{chat_id[-4:]})"


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
def _friendly_error(e: Exception) -> str:
    name = type(e).__name__
    if name == "MissingKeyError":
        return "No OpenAI key is set. Add OPENAI_API_KEY to the environment and restart the app."
    if name == "AuthenticationError":
        return "OpenAI rejected the API key. Check OPENAI_API_KEY."
    if name == "RateLimitError":
        return "OpenAI refused the request: rate limit or spending limit reached. Wait a minute or check your OpenAI billing."
    if name in ("APIConnectionError", "APITimeoutError"):
        return "Couldn't reach OpenAI. Check the internet connection and try again."
    return f"Something went wrong ({name}): {e}"


def load_demo_history() -> None:
    try:
        if demo.snapshot_ready():
            demo.restore_snapshot()
            ss.esd.load()
            ss.grag.load()
        else:
            ss.esd.reset()
            ss.grag.reset()
            bar = st.sidebar.progress(0.0, text="Reading the background messages into both memories")
            demo.ingest(
                [ss.esd, ss.grag],
                demo.load_background(),
                progress=lambda i, n: bar.progress(i / n, text=f"{i} of {n} messages"),
            )
            demo.save_snapshot()
        background = demo.load_background()
        ss.sim_date = date.fromisoformat(max(m["date"] for m in background)) + timedelta(days=3)
        ss.history_tokens = sum(_history_line(m["date"], m["text"]) for m in background)
        _save_state()
        ss.flash = "Demo history loaded into both memories."
    except Exception as e:  # show the problem instead of crashing the demo
        ss.error = _friendly_error(e)
    st.rerun()


def _update_note(actions: list[dict], added: list[str]) -> str:
    counts = {k: sum(a["action"] == k for a in actions) for k in ("added", "replaced", "repeated")}
    note = f"Our memory: +{counts['added']} facts"
    if counts["replaced"]:
        note += f", {counts['replaced']} replaced"
    if counts["repeated"]:
        note += f", {counts['repeated']} repeated"
    return note + f". Current method: +{len(added)} triples."


def handle_message(prompt: str, box) -> None:
    chat = ss.chats[ss.current]
    ts = ss.sim_date.isoformat()
    recent = [{"role": m["role"], "content": m["content"]} for m in chat["messages"][-config.RECENT_TURNS:]]
    chat["messages"].append({"role": "user", "content": prompt, "ts": ts})
    if chat["title"] == "New chat":
        chat["title"] = prompt if len(prompt) <= 40 else prompt[:39] + "…"
    save_chat(chat)

    with box:
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(prompt)
        with st.chat_message("assistant", avatar=":material/neurology:"):
            try:
                with st.spinner("Both methods are answering"):
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
                with st.spinner("Updating both memories"):
                    with ThreadPoolExecutor(2) as pool:
                        f1 = pool.submit(ss.esd.observe, prompt, ts)
                        f2 = pool.submit(ss.grag.observe, prompt, ts)
                        ss.flash = _update_note(f1.result(), f2.result())
                ss.history_tokens += _history_line(ts, prompt)
                _save_state()
            except Exception as e:
                ss.error = _friendly_error(e)
    st.rerun()


# --- rendering ----------------------------------------------------------------------
def stat_row(items: list[dict]) -> None:
    parts = []
    for it in items:
        tone = " signal" if it.get("tone") == "signal" else ""
        note = f"<span class='n'>({html.escape(it['note'])})</span>" if it.get("note") else ""
        parts.append(f"<span class='esd-stat{tone}'><span class='v'>{html.escape(it['value'])}</span>"
                     f"<span class='l'>{html.escape(it['label'])}</span>{note}</span>")
    st.html(f"<div class='esd-stats'>{''.join(parts)}</div>")


def render_details(m: dict) -> None:
    ours, theirs = m.get("esd"), m.get("grag")
    if not ours:
        return
    ex = ours.get("extra", {})
    st.html(f"<div class='esd-meta'>{ours['prompt_tokens']:,} tokens sent, Memory Card "
            f"{ex.get('card_tokens', '?')} of {config.CARD_TOKEN_BUDGET}, {ours['latency_s']} s</div>")
    with st.expander("Compare with the current method", icon=":material/compare_arrows:"):
        left, right = st.columns(2, gap="medium")
        with left:
            st.html("<div class='esd-col theirs'>What the current method answered</div>")
            if theirs:
                st.markdown(theirs["text"])
                tex = theirs.get("extra", {})
                matched = ", ".join(f"{k} (from '{v}')" for k, v in tex.get("matched", {}).items()) or "nothing"
                st.caption(f"Sent {theirs['prompt_tokens']:,} tokens. Its keyword search matched: {matched}.")
                st.code(theirs.get("card") or "(nothing found in its graph)", language=None, wrap_lines=True)
            else:
                st.caption("Not asked. Turn on \"Also ask the current method\" in the sidebar.")
        with right:
            st.html("<div class='esd-col ours'>What our method sent</div>")
            concepts = ", ".join(ex.get("concepts", [])) or "none"
            st.caption(f"The question was expanded to: {concepts}.")
            st.code(ours.get("card") or "", language=None, wrap_lines=True)
            hits = ex.get("hits", [])
            if hits:
                used = set(ours.get("used", []))
                st.dataframe(
                    [{"On card": "Yes" if h["fact_id"] in used else "", "Fact": h["statement"],
                      "Why it was picked": h["reason"]} for h in hits],
                    hide_index=True,
                )


with st.sidebar:
    st.html("<div class='esd-group'>Demo data</div>")
    if st.button("Load demo history", icon=":material/history:", type="primary", width="stretch",
                 help="40 messages over six weeks, read into both memories"):
        load_demo_history()
    st.button("Reset memory", icon=":material/restart_alt:", on_click=on_reset_memory, width="stretch",
              help="Clears both memories and keeps the chats")
    st.button("Reset everything", icon=":material/delete_sweep:", on_click=on_reset_all, width="stretch",
              help="Clears both memories and all chats")
    st.html("<div class='esd-group'>This chat</div>")
    st.button("Delete this chat", icon=":material/delete:", on_click=on_delete_chat, width="stretch")
    st.html("<div class='esd-group'>Comparison</div>")
    st.toggle("Also ask the current method", key="compare",
              help="Each question is also answered by the standard Graph RAG, shown under our answer")
    st.divider()
    st.caption(f"Model {config.CHAT_MODEL}, embeddings {config.EMBED_MODEL}.")
    st.caption(f"This session used {llm.USAGE['prompt_tokens']:,} prompt and "
               f"{llm.USAGE['completion_tokens']:,} completion tokens.")

if ss.flash:
    st.toast(ss.flash)
    ss.flash = None

# --- header --------------------------------------------------------------------------
h_left, h_right = st.columns([6, 4], gap="medium", vertical_alignment="bottom")
with h_left:
    st.html("<div class='esd-brand'><span class='name'>ESD Memory</span>"
            "<span class='lede'>The same messages go into two memories. Ours is on top, the standard method below.</span></div>")
with h_right:
    d1, d2, d3 = st.columns([2.3, 1, 1.1], vertical_alignment="bottom")
    d1.html(f"<div class='esd-date'><span class='l'>Simulated date</span>"
            f"<span class='v'>{ss.sim_date.strftime('%d %b %Y')}</span></div>")
    d2.button("+1 day", on_click=shift_date, args=(1,), width="stretch")
    d3.button("+1 week", on_click=shift_date, args=(7,), width="stretch")

left, right = st.columns([7, 3], gap="medium")

with left:
    if ss.error:
        st.error(ss.error, icon=":material/error:")
        ss.error = None

    ids = sorted(ss.chats, key=lambda i: ss.chats[i].get("order", 0), reverse=True)
    c1, c2 = st.columns([5, 1.2], vertical_alignment="center")
    ss.chat_select = chat_label(ss.current)  # keep the dropdown in step with the open chat
    c1.selectbox("Chat", [chat_label(i) for i in ids], key="chat_select", on_change=on_select_chat,
                 label_visibility="collapsed")
    c2.button("New chat", icon=":material/add:", on_click=on_new_chat, width="stretch")

    chat = ss.chats[ss.current]
    box = st.container(height=CHAT_HEIGHT, border=True)
    with box:
        if not chat["messages"]:
            st.html("<div class='esd-empty'><div class='h'>Start with a message</div>"
                    "<p>Everything you send goes into both memories on the right. Memory carries across "
                    "chats, and the date buttons move time forward, so you can test what is remembered "
                    "weeks later.</p></div>")
            if not ss.esd.graph.facts:
                if st.button("Load demo history", key="empty_load", icon=":material/history:", type="primary"):
                    load_demo_history()
        for m in chat["messages"]:
            avatar = ":material/person:" if m["role"] == "user" else ":material/neurology:"
            with st.chat_message(m["role"], avatar=avatar):
                st.markdown(m["content"])
                if m["role"] == "assistant":
                    render_details(m)

    prompt = st.chat_input("Type a message")
    if prompt:
        handle_message(prompt, box)

with right:
    last = next((m for m in reversed(chat["messages"]) if m["role"] == "assistant"), None)
    question = last["question"] if last else None
    ours = last.get("esd") if last else None
    theirs = last.get("grag") if last else None
    conflicts = ss.grag.conflicts(ss.esd.graph.changes())

    panels = {
        "ours": ("Our method", "ESD", "Dated facts; replaced facts are kept as history",
                 lambda h: draw_esd(ss.esd.graph, ours, question, h, dark=DARK),
                 esd_stats(ss.esd.graph, ours, ss.history_tokens)),
        "theirs": ("Current method", "Graph RAG", "Standard triples, with no dates and no replacing",
                   lambda h: draw_graph_rag(ss.grag, theirs, conflicts, question, h, dark=DARK),
                   graph_rag_stats(ss.grag, theirs, conflicts)),
    }

    @st.dialog("Knowledge graph", width="large")
    def enlarge(key: str) -> None:
        name, tag, desc, draw, stats = panels[key]
        st.html(f"<div class='esd-head'><span class='name'>{name}</span><span class='tag {key}'>{tag}</span>"
                f"<span class='desc'>{desc}</span></div>")
        st.iframe(draw(ENLARGED_HEIGHT), height=ENLARGED_HEIGHT)
        stat_row(stats)

    for key, (name, tag, desc, draw, stats) in panels.items():
        with st.container(height=PANEL_HEIGHT, border=True, key=f"panel_{key}"):
            t, b = st.columns([4, 1.4], vertical_alignment="center")
            t.html(f"<div class='esd-head'><span class='name'>{name}</span><span class='tag {key}'>{tag}</span>"
                   f"<span class='desc'>{desc}</span></div>")
            if b.button("Enlarge", key=f"enlarge_{key}", icon=":material/open_in_full:", type="tertiary"):
                enlarge(key)
            st.iframe(draw(GRAPH_HEIGHT), height=GRAPH_HEIGHT)
            stat_row(stats)
