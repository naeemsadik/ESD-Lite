"""Run every assistant through the test scenarios and write results/.

    python eval/run_eval.py                 # everything
    python eval/run_eval.py --only esd,graph_rag --limit 2

Each assistant first reads the same ~40-message background life (done once
and cached), then each scenario's cue messages plus filler chit-chat, and is
then asked the scenario's question. The examiner AI marks every answer.
"""
import argparse
import copy
import csv
import json
import pickle
import sys
from concurrent.futures import ThreadPoolExecutor
from itertools import cycle
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from baselines.graph_rag import GraphRAGAssistant  # noqa: E402
from baselines.simple import FullHistoryAssistant, NoMemoryAssistant, VectorRAGAssistant  # noqa: E402
from esd import config, llm  # noqa: E402
from esd.chat import ESDAssistant  # noqa: E402
from esd.demo import background_hash, load_background  # noqa: E402
from eval.fillers import FILLERS  # noqa: E402
from eval.judge import judge  # noqa: E402

ASSISTANTS = {
    cls.key: cls
    for cls in [NoMemoryAssistant, FullHistoryAssistant, VectorRAGAssistant, GraphRAGAssistant, ESDAssistant]
}
FILLERS_AFTER_CUE = 6
FILLERS_BEFORE_QUESTION = 10
CACHE_DIR = config.DATA_DIR / "eval_cache"
OURS = "esd"
BLUE, GREY, INK, MUTED = "#2a78d6", "#a3a29d", "#0b0b0b", "#52514e"


def build_base(key: str, background: list[dict]):
    """An assistant that has read the background life (cached on disk)."""
    path = CACHE_DIR / f"{key}_{background_hash()}.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    assistant = ASSISTANTS[key](path=None)
    for m in background:
        assistant.observe(m["text"], m["date"])
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(assistant))
    return assistant


def scenario_stream(scenario: dict, offset: int) -> list[tuple[str, str]]:
    """Cue messages, each followed by filler chit-chat so the cue leaves the recent window."""
    fillers = cycle(FILLERS[offset % len(FILLERS):] + FILLERS[: offset % len(FILLERS)])
    stream = []
    for i, cue in enumerate(scenario["cues"]):
        stream.append((cue["date"], cue["text"]))
        n = FILLERS_BEFORE_QUESTION if i == len(scenario["cues"]) - 1 else FILLERS_AFTER_CUE
        stream += [(cue["date"], next(fillers)) for _ in range(n)]
    return stream


def run_one(key: str, base, scenario: dict, offset: int, background: list[dict]) -> dict:
    assistant = copy.deepcopy(base)
    stream = scenario_stream(scenario, offset)
    for d, text in stream:
        assistant.observe(text, d)
    recent = [{"role": "user", "content": text} for _, text in stream[-config.RECENT_TURNS:]]
    q = scenario["question"]
    ans = assistant.answer(q["text"], q["date"], recent)
    verdict = judge(q["text"], ans.text, scenario["pass_criteria"])
    history = [(m["date"], m["text"]) for m in background] + stream
    return {
        "scenario": scenario["id"],
        "set": scenario.get("set", "development"),
        "category": scenario["category"],
        "assistant": key,
        "assistant_name": ASSISTANTS[key].name,
        "passed": verdict.passed,
        "judge_reason": verdict.reason,
        "prompt_tokens": ans.prompt_tokens,
        "memory_tokens": ans.extra.get("memory_tokens", 0),
        "history_tokens": llm.count_tokens("\n".join(f"[{d}] {t}" for d, t in history)),
        "latency_s": ans.latency_s,
        "answer": ans.text,
        "memory_sent": ans.card,
    }


def summarise(rows: list[dict], keys: list[str]) -> list[dict]:
    out = []
    for key in keys:
        mine = [r for r in rows if r["assistant"] == key]
        if not mine:
            continue
        n = len(mine)
        by_set = {name: [r for r in mine if r.get("set", "development") == name] for name in ("development", "held-out")}
        mem = sum(r["memory_tokens"] for r in mine) / n
        hist = sum(r["history_tokens"] for r in mine) / n
        out.append({
            "assistant": key,
            "name": ASSISTANTS[key].name,
            "pass_rate": round(100 * sum(r["passed"] for r in mine) / n, 1),
            "passed": f"{sum(r['passed'] for r in mine)}/{n}",
            "passed_development": f"{sum(r['passed'] for r in by_set['development'])}/{len(by_set['development'])}",
            "passed_held_out": f"{sum(r['passed'] for r in by_set['held-out'])}/{len(by_set['held-out'])}",
            "avg_prompt_tokens": round(sum(r["prompt_tokens"] for r in mine) / n),
            "avg_memory_tokens": round(mem),
            "avg_latency_s": round(sum(r["latency_s"] for r in mine) / n, 2),
            "compression": round(1 - mem / hist, 3) if hist else 0.0,
        })
    return out


def write_markdown(summary: list[dict], rows: list[dict], path: Path) -> None:
    lines = [
        "# Results",
        "",
        "| Assistant | Rules respected (CCS) | Passed | Development tests | Held-out tests | Avg tokens sent | Avg memory tokens | Avg response time |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in summary:
        lines.append(
            f"| {s['name']} | {s['pass_rate']}% | {s['passed']} | {s['passed_development']} | {s['passed_held_out']} | "
            f"{s['avg_prompt_tokens']:,} | {s['avg_memory_tokens']:,} | {s['avg_latency_s']}s |"
        )
    lines += ["", "Development tests were used while building ESD-Lite; held-out tests were written afterwards "
              "and not used for any tuning."]
    esd = next((s for s in summary if s["assistant"] == OURS), None)
    if esd:
        lines += ["", f"Compression for ESD-Lite (spec CCR): {esd['compression']:.1%} smaller than the full history."]
    scenarios = list(dict.fromkeys(r["scenario"] for r in rows))
    lines += ["", "## Per scenario", "", "| Scenario | Set | " + " | ".join(s["name"] for s in summary) + " |",
              "|---|---|" + "---|" * len(summary)]
    for sc in scenarios:
        marks = []
        for s in summary:
            r = next((r for r in rows if r["scenario"] == sc and r["assistant"] == s["assistant"]), None)
            marks.append("—" if r is None else ("✅" if r["passed"] else "❌"))
        test_set = next(r.get("set", "development") for r in rows if r["scenario"] == sc)
        lines.append(f"| {sc} | {test_set} | " + " | ".join(marks) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_chart(summary: list[dict], path: Path) -> None:
    """Two small charts (one measure each, never a shared dual axis)."""
    names = [s["name"] for s in summary]
    colors = [BLUE if s["assistant"] == OURS else GREY for s in summary]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), constrained_layout=True)
    panels = [
        (axes[0], [s["pass_rate"] for s in summary], "Rules respected (% of tests passed)", "{:.0f}%"),
        (axes[1], [s["avg_prompt_tokens"] for s in summary], "Tokens sent to the AI per question", "{:,.0f}"),
    ]
    for ax, values, title, fmt in panels:
        y = range(len(names))
        ax.barh(y, values, color=colors, height=0.55)
        ax.set_yticks(list(y), names, color=INK, fontsize=10)
        ax.invert_yaxis()
        ax.set_title(title, loc="left", color=INK, fontsize=11)
        ax.grid(axis="x", color="#e4e3df", linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color("#c9c8c3")
        ax.tick_params(axis="x", colors=MUTED, labelsize=9)
        ax.tick_params(axis="y", length=0)
        top = max(values) if values else 1
        for i, v in enumerate(values):
            ax.text(v + top * 0.01, i, fmt.format(v), va="center", color=INK, fontsize=9)
        ax.set_xlim(0, top * 1.15 if top else 1)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="comma-separated assistant keys: " + ", ".join(ASSISTANTS))
    parser.add_argument("--limit", type=int, help="only the first N scenarios")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--rejudge", action="store_true",
                        help="re-mark the saved answers with the current pass criteria (no new answers)")
    args = parser.parse_args()
    if args.rejudge:
        rejudge()
        return

    keys = [k for k in ASSISTANTS if not args.only or k in args.only.split(",")]
    scenarios = json.loads((config.EVAL_DIR / "scenarios.json").read_text(encoding="utf-8"))[: args.limit]
    background = load_background()

    print(f"Reading the background life into {len(keys)} assistants (cached after the first run)...")
    with ThreadPoolExecutor(len(keys)) as pool:
        bases = dict(zip(keys, pool.map(lambda k: build_base(k, background), keys)))

    jobs = [(k, s, i) for i, s in enumerate(scenarios) for k in keys]
    print(f"Running {len(jobs)} tests ({len(scenarios)} scenarios x {len(keys)} assistants)...")
    rows = []
    with ThreadPoolExecutor(args.workers) as pool:
        futures = [pool.submit(run_one, k, bases[k], s, i, background) for k, s, i in jobs]
        for f in futures:
            r = f.result()
            rows.append(r)
            print(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['scenario']:<16} {r['assistant_name']:<20} "
                  f"{r['prompt_tokens']:>6} tokens  {r['judge_reason']}")

    write_outputs(rows, keys)


def rejudge() -> None:
    scenarios = {s["id"]: s for s in json.loads((config.EVAL_DIR / "scenarios.json").read_text(encoding="utf-8"))}
    rows = json.loads((config.RESULTS_DIR / "answers.json").read_text(encoding="utf-8"))
    for r in rows:
        s = scenarios[r["scenario"]]
        r["set"] = s.get("set", "development")
        verdict = judge(s["question"]["text"], r["answer"], s["pass_criteria"])
        if verdict.passed != r["passed"]:
            print(f"  changed: {r['scenario']:<16} {r['assistant_name']:<20} "
                  f"{'PASS' if r['passed'] else 'FAIL'} -> {'PASS' if verdict.passed else 'FAIL'}  {verdict.reason}")
        r["passed"], r["judge_reason"] = verdict.passed, verdict.reason
    write_outputs(rows, [k for k in ASSISTANTS if any(r["assistant"] == k for r in rows)])


def write_outputs(rows: list[dict], keys: list[str]) -> None:
    config.RESULTS_DIR.mkdir(exist_ok=True)
    fields = [k for k in rows[0] if k not in ("answer", "memory_sent")]
    with open(config.RESULTS_DIR / "results.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    (config.RESULTS_DIR / "answers.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    summary = summarise(rows, keys)
    (config.RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    write_markdown(summary, rows, config.RESULTS_DIR / "summary.md")
    write_chart(summary, config.RESULTS_DIR / "chart.png")

    print("\n" + (config.RESULTS_DIR / "summary.md").read_text(encoding="utf-8"))
    print(f"API use: {llm.USAGE}")


if __name__ == "__main__":
    main()
