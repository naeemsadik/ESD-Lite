"""Results page: the comparison table, a pass/fail grid, and charts."""
import json
from itertools import cycle, islice

import altair as alt
import pandas as pd
import streamlit as st

from esd import config, llm
from esd.demo import load_background
from eval.fillers import FILLERS

st.set_page_config(page_title="ESD Memory: Results", page_icon="📊", layout="wide")
st.title("📊 Results: five ways of remembering, same tests")

BLUE, GREY = "#2a78d6", "#a3a29d"
summary_path = config.RESULTS_DIR / "summary.json"
answers_path = config.RESULTS_DIR / "answers.json"


def bars(data: pd.DataFrame, field: str, title: str, fmt: str, order: list[str]) -> alt.Chart:
    color = alt.Color("group:N", scale=alt.Scale(domain=["Our method", "Other methods"], range=[BLUE, GREY]),
                      legend=alt.Legend(title=None, orient="top"))
    base = alt.Chart(data).encode(
        y=alt.Y("name:N", sort=order, title=None, axis=alt.Axis(labelOverlap=False, labelLimit=200)),
        x=alt.X(f"{field}:Q", title=title),
        tooltip=[alt.Tooltip("name:N", title="Assistant"), alt.Tooltip(f"{field}:Q", title=title, format=fmt)],
    )
    return (base.mark_bar(size=20, cornerRadiusEnd=4).encode(color=color)
            + base.mark_text(align="left", dx=4).encode(text=alt.Text(f"{field}:Q", format=fmt))).properties(height=240)


if summary_path.exists():
    summary = pd.DataFrame(json.loads(summary_path.read_text(encoding="utf-8")))
    rows = pd.DataFrame(json.loads(answers_path.read_text(encoding="utf-8")))
    st.caption(
        "Every assistant used the same OpenAI model, read the same background life and the same test "
        "conversations, and was marked by the same examiner AI."
    )
    table = summary.rename(columns={
        "name": "Assistant", "pass_rate": "Rules respected (%)", "passed": "Passed",
        "avg_prompt_tokens": "Avg tokens sent", "avg_memory_tokens": "Avg memory tokens",
        "avg_latency_s": "Avg response time (s)", "passed_development": "Development tests",
        "passed_held_out": "Held-out tests",
    })[["Assistant", "Rules respected (%)", "Passed", "Development tests", "Held-out tests", "Avg tokens sent",
        "Avg memory tokens", "Avg response time (s)"]]
    st.dataframe(table, hide_index=True)
    st.caption("Development tests were used while building our method. Held-out tests were written afterwards and "
               "not used for any tuning, so they are the fairer check.")

    esd = summary[summary["assistant"] == "esd"]
    if not esd.empty:
        st.markdown(
            f"**Compression (spec CCR):** our Memory Card is **{esd.iloc[0]['compression']:.1%} smaller** "
            "than the full conversation history in these tests."
        )

    st.subheader("Pass / fail per test")
    names = dict(zip(summary["assistant"], summary["name"]))
    grid = (
        rows.assign(mark=rows["passed"].map({True: "✅", False: "❌"}), name=rows["assistant"].map(names))
        .pivot_table(index=["set", "scenario", "category"], columns="name", values="mark", aggfunc="first")
        .reindex(columns=list(summary["name"]))
        .reset_index()
    )
    st.dataframe(grid, hide_index=True, height=(len(grid) + 1) * 35 + 3)  # every test visible, no scrolling

    st.subheader("At a glance")
    summary["group"] = summary["assistant"].map(lambda k: "Our method" if k == "esd" else "Other methods")
    order = list(summary["name"])
    c1, c2 = st.columns(2)
    c1.altair_chart(bars(summary, "pass_rate", "Rules respected (%)", ".0f", order), width="stretch")
    c2.altair_chart(bars(summary, "avg_prompt_tokens", "Tokens sent per question", ",.0f", order), width="stretch")
else:
    st.info("No test results yet. Run `python eval/run_eval.py` in the project folder, then refresh this page.")

# --- Cost as the conversation grows (token counting only, no API calls) -----------
st.subheader("Memory cost as the conversation grows")
st.caption(
    "Tokens of memory sent with every question. Full history pastes every past message, so it grows "
    "with each one. Our Memory Card has a hard limit, so it never goes above "
    f"{config.CARD_TOKEN_BUDGET} tokens. Messages are the demo's own background life and chit-chat, repeated."
)
pool = [f"[{m['date']}] {m['text']}" for m in load_background()] + [f"[2025-03-01] {f}" for f in FILLERS]
points = [10, 25, 50, 100, 200, 400, 800]
growth = []
for n in points:
    growth.append({"messages": n, "method": "Full history", "tokens": llm.count_tokens("\n".join(islice(cycle(pool), n)))})
    growth.append({"messages": n, "method": "ESD Memory Card (limit)", "tokens": config.CARD_TOKEN_BUDGET})
growth = pd.DataFrame(growth)
line_color = alt.Color("method:N", scale=alt.Scale(domain=["ESD Memory Card (limit)", "Full history"], range=[BLUE, GREY]),
                       legend=alt.Legend(title=None, orient="top"))
base = alt.Chart(growth).encode(
    x=alt.X("messages:Q", title="Messages in the conversation so far"),
    y=alt.Y("tokens:Q", title="Memory tokens sent per question"),
    color=line_color,
    tooltip=[alt.Tooltip("method:N", title="Method"), alt.Tooltip("messages:Q", title="Messages"),
             alt.Tooltip("tokens:Q", title="Tokens", format=",")],
)
labels = base.transform_filter(alt.datum.messages == points[-1]).mark_text(align="right", dy=-10, fontSize=12).encode(
    text=alt.Text("tokens:Q", format=","))
st.altair_chart((base.mark_line(strokeWidth=2) + base.mark_point(size=60, filled=True) + labels).properties(height=280),
                width="stretch")
crossover = next((n for n in points if growth.query("messages == @n and method == 'Full history'")["tokens"].iloc[0]
                  > config.CARD_TOKEN_BUDGET), None)
if crossover:
    st.caption(f"From about {crossover} messages on, pasting the full history costs more than our whole Memory Card.")

if summary_path.exists():
    with st.expander("Read every answer and the examiner's reason"):
        for _, r in rows.sort_values(["scenario", "assistant"]).iterrows():
            st.markdown(f"**{r['scenario']} · {names.get(r['assistant'], r['assistant'])} · "
                        f"{'✅ pass' if r['passed'] else '❌ fail'}**: {r['judge_reason']}")
            st.text(r["answer"][:1500])
