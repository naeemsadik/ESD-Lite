# ESD-Lite: One-Night Build Tasks

This is the **one-night version** of [plan.md](plan.md). By the end of tonight we want:

1. **A demo screen**
   - **Left 70%:** chat with our assistant, with multiple chats
   - **Right 30%:** two live knowledge graphs, **ours (top)** and **the current standard Graph RAG method (bottom)**, built from the same messages
2. **A small proof table** comparing our method with 4 other approaches, shown on a Results page

Work top to bottom. Each task has a time box, the files to touch, and a **Done when** check. Don't start the next task until the check passes.

---

## Build status (30 Sep 2026): T0–T13 done, verified live with the OpenAI key

| Task | Status | Verified by |
|---|---|---|
| T0 Setup | ✅ | `check_api.py`: reply and 1536-length embedding |
| T1 Models + OpenAI helper | ✅ | 2 API calls for 3 embeddings (cache hit); the cache survives a restart |
| T2 Extractor | ✅ | Live: the allergy becomes 1 rule; chit-chat becomes nothing |
| T3 Dated graph | ✅ | `pytest` |
| T4 Replaced-by | ✅ | `check_revision.py`: 6/6 known cases correct |
| T5 Retriever | ✅ | Live: macarons link to the allergy through "almond flour"; the timeline test answers "Chittagong" |
| T6 Memory Card + answer (Checkpoint A) | ✅ | `demo_cli.py`: nut-free macarons, MongoDB code |
| T7 Current method (Graph RAG) | ✅ | Tests plus rehearsal: 1 conflict found, and it kept both databases |
| T8 Graph drawing | ✅ | `preview_graphs.py` plus screenshots; both panels use the same 40-point limit |
| T9 Demo screen (Checkpoint B) | ✅ | The demo script rehearsed in the app with the real model; screenshots in `docs/` |
| T10 Baselines | ✅ | Full evaluation run |
| T11 Background + scenarios | ✅ | 40 background messages; 8 development and 6 held-out tests, each with 10 fillers before the question |
| T12 Examiner + evaluation + Results page | ✅ | 14 tests × 5 assistants; answers spot-checked by hand |
| T13 README, demo script, commit | ✅ | Screenshot, rehearsal notes, commit |

**Stretch items:**
- ✅ Token-growth chart (Results page)
- ✅ More scenarios: 6 held-out tests
- ⏭️ Vector RAG "similarity map" toggle: not built. Vector RAG is already in the evaluation. Showing it live would add a third answer per message to the demo.
- ⏭️ Background-thread extraction: not built. Extraction runs straight after the reply, with a spinner. A background thread risks the next message arriving before memory is updated, mid-demo.

**Problems the live runs exposed, and how they were fixed:**
- **Exaggerated facts:** the extractor turned "hates chocolate" into "chocolate allergy". The prompt now says to be faithful.
- **Wrong replacements:** the replaced-by check marked "leads the refactor" as replaced by "refactor due end of February". It now writes a one-line reason before each label (6/6 on known cases).
- **Questions about the past failed:** the retriever ignored replaced facts. A match on an old fact now brings in its current version, whose card line carries the history. The question's own best matches always get seeded, so vague expanded concepts can't crowd them out. Events fade at 0.01 per day, not 0.03.
- **A weak nut-free answer:** the shared answer prompt now says to check every suggested item against the user's rules. It applies to all assistants, and temperature is 0.
- **A false claim in the demo:** the current method does *not* send ever-growing text; it sends only what its keyword match finds. The cost comparison is now against full history, shown in the app and in the growth chart.
- **A false pass:** "No memory" passed the cake test by suggesting nothing. The criterion now requires an actual suggestion, and the saved answers were re-marked.
- **A lenient mark, left as is:** in the final run, "No memory" passed the gluten test while suggesting granola, which is usually not gluten-free. It's noted in the README, not re-marked.
- **Record of earlier runs:** `results/run1_before_fix/` and `results/run2_after_fix/`.

**Where the build differs from the text below:**
- The 3 simple baselines live in one file, `baselines/simple.py`.
- The embedding cache is `data/emb_cache.sqlite`.
- The graphs use `st.iframe`, because `components.html` is deprecated in Streamlit 1.64.
- `scipy` was added, because PageRank needs it.
- Conflict type (a) ("same subject and relation, different object") was **not built**. It would flag things like "likes mango" and "likes biryani" as conflicts. Only (b), the changes our method detected, is shown.
- Response time is measured to the complete answer (answers aren't streamed).
- Scenario 4 asks "back in February?" instead of "last year?", so the dates are unambiguous.
- The allergy cue is "nuts (peanuts and tree nuts)", so almond flour counts clearly.

---

## Scope for tonight

| In | Out (later, see plan.md) |
|---|---|
| Steps ①–⑥ (Listen, Store, Update, Find, Compress, Answer) | 30 scenarios (we do 8) |
| "Current method" assistant: standard Graph RAG | LoCoMo benchmark sample |
| 70/30 demo screen: multi-chat + two live graphs + side-by-side answers | Mini neural add-on (GNN + Perceiver) |
| 8 test scenarios, 5-assistant comparison, Results page | Background (async) extraction: we run it straight after each reply instead |

## The night at a glance (~7 h 40 min + buffer)

| # | Task | Time box | Clock |
|---|---|---|---|
| T0 | Setup + API check | 20 min | 0:20 |
| T1 | Data models + OpenAI helper | 15 min | 0:35 |
| T2 | ① Listen: fact extractor | 35 min | 1:10 |
| T3 | ② Store: bi-temporal memory graph | 35 min | 1:45 |
| T4 | ③ Update: "replaced-by" revision | 35 min | 2:20 |
| T5 | ④ Find: retriever (rules + trigger words + graph walk) | 45 min | 3:05 |
| T6 | ⑤ Memory Card + ⑥ Answer + terminal demo | 30 min | 3:35 |
| ⛳ | **CHECKPOINT A: our memory works in the terminal** | | |
| T7 | **"Current method" assistant: standard Graph RAG** | 35 min | 4:10 |
| T8 | **Graph drawing for both methods** | 40 min | 4:50 |
| T9 | **Demo screen: 70/30, multi-chat, two graphs, side-by-side answers** | 70 min | 6:00 |
| ⛳ | **CHECKPOINT B: demo-ready** | | |
| T10 | Other 3 baselines (no memory, full history, vector RAG) | 15 min | 6:15 |
| T11 | Background life + 8 test scenarios | 25 min | 6:40 |
| T12 | Examiner AI + evaluation runner + Results page | 40 min | 7:20 |
| T13 | README, demo script, commit | 20 min | 7:40 |

**If we're behind schedule:**
- **Checkpoint A later than 4:15:** in T8, skip the question-path highlighting and keep only colors, "replaced by" arrows, and red conflicts.
- **Checkpoint B later than 6:30:** skip T10–T12 and go to T13. **T0–T9 plus a rehearsed demo is enough to present.**

---

## Decisions already made (no debating at 2 a.m.)

- **Python 3.13** (already installed) inside a `.venv`.
- **Models:** `gpt-4o-mini` for everything (extract, expand, answer, judge). **Embeddings:** `text-embedding-3-small`. Both live in `esd/config.py`.
- **Simulated time:** every message carries a date `ts` (ISO string, e.g. `"2025-01-12"`), so the demo and the tests can jump weeks ahead. Nothing reads the real clock.
- **Memory is shared across all chats.** There is one user, and each chat is one session. "Reset memory" wipes both memories.
- **Fair comparison:** **every user message goes to both memories**, ours and the standard Graph RAG. Both use the same model and the same system prompt. We never weaken the baseline on purpose (see plan.md §6).
- **Storage:**

  | Path | Holds |
  |---|---|
  | `data/chats/<chat_id>.json` | one chat's transcript |
  | `data/memory/esd.json` | our memory graph |
  | `data/memory/graph_rag.json` | the standard Graph RAG graph |
  | `data/emb_cache.json` | cached embeddings |
  | `data/demo_snapshot/` | pre-built memories for the "background life" |

- **One interface for all 5 assistants.** The caller passes the recent messages, so the recent window belongs to each chat.
  ```python
  observe(user_msg: str, ts: str) -> None
  answer(question: str, ts: str, recent: list[dict]) -> Answer
  # Answer = text, prompt_tokens, latency_s, card (str | None), used (list of node/edge ids), extra (dict)
  ```
- **Our graph (ESD):**
  - **Nodes:**
    - entity nodes, e.g. `rina`, `postgresql`
    - fact nodes, each with `kind` ∈ {`constraint`, `decision`, `event`, `fact`}
  - **Edges:**
    - `ABOUT`: fact → entity, weight 1.0
    - `SUPERSEDES`: new fact → old fact, weight 0.3
- **Current-method graph (standard Graph RAG):** entity nodes joined by `subject —relation→ object` edges, with **no dates and no replacing**. This is how LightRAG, Microsoft GraphRAG, and similar systems store knowledge.
- **Card budget:** 300 tokens (counted with `tiktoken`, `o200k_base`). **Recent window:** the last 4 messages of the current chat.

---

## T0: Setup + API check (20 min)

- [ ] `python -m venv .venv` then `.venv\Scripts\activate`
- [ ] Create `requirements.txt`: `openai python-dotenv pydantic networkx numpy tiktoken streamlit pyvis pandas matplotlib pytest`, then run `pip install -r requirements.txt`
- [ ] `.gitignore`: `.env`, `.venv/`, `data/`, `__pycache__/`
- [ ] `.env.example` containing `OPENAI_API_KEY=sk-...`. Copy it to `.env` and fill in your real key.
- [ ] `esd/__init__.py`, `esd/config.py`: load `.env` and set `CHAT_MODEL`, `EMBED_MODEL`, `CARD_TOKEN_BUDGET=300`, `RECENT_TURNS=4`, and fading speeds `DECAY = {"constraint": 0.0, "decision": 0.005, "fact": 0.01, "event": 0.03}` (per day)
- [ ] `scripts/check_api.py`: one tiny chat call and one embedding call

**Done when:** `python scripts/check_api.py` prints a reply and `1536` (the embedding length).

## T1: Data models + OpenAI helper (15 min)

- [ ] `esd/models.py` (pydantic):
  - `ExtractedFact`: `kind`, `statement`, `slot: str | None`, `entities: list[str]`, `triggers: list[str]`, `valid_from: str | None`
    ⚠️ Structured outputs need **every field required, with no default values**. Use `str | None` for optional fields.
  - `Extraction`: `facts: list[ExtractedFact]`
  - `Fact`: everything in `ExtractedFact` plus `id`, `valid_to`, `recorded_at`, `superseded_by`, `mentions=1`, `source`
  - `Hit`: `fact_id`, `score`, `reason`, `via`. `via` is the concept that linked the question to the fact, e.g. `"nuts"`. The top graph draws it.
  - `Answer`: `text`, `prompt_tokens`, `latency_s`, `card`, `used`, `extra`
- [ ] `esd/llm.py`:
  - `client`: `OpenAI(max_retries=5)`
  - `chat(messages) -> (text, usage)`
  - `parse(messages, Schema) -> Schema`: uses `client.chat.completions.parse(..., response_format=Schema)` (on older SDKs: `client.beta.chat.completions.parse`). Wrap it in try/except and return an empty object on failure.
  - `embed(texts) -> np.ndarray`: disk cache, batched, thread-safe (the app calls it from 2 threads)
  - `cosine(a, b)`
  - `count_tokens(text)`

**Done when:** embedding the same text twice makes only **one** API call (the second one is a cache hit).

## T2: ① Listen, the fact extractor (35 min)

- [ ] `esd/extractor.py`: `extract(user_msg, ts, known_slots: list[str]) -> list[ExtractedFact]`
- [ ] Prompt rules:
  - Extract only **lasting** information. Chit-chat → empty list.
  - Write each `statement` in the third person, e.g. "User is allergic to peanuts".
  - `slot` is a short, stable topic key such as `user.allergy`, `project.database`, `user.home_city`. **Reuse a key from `known_slots` if one fits.** This is what makes change detection work.
  - `triggers` (constraints and decisions only): 5–10 situations, objects, or ingredients where the rule matters, **including non-obvious ones**. Example: peanut allergy → desserts, baking, macarons, satay, granola, Thai food.
  - Turn relative dates ("last March") into ISO dates using `ts`.

**Done when:**
- "I'm allergic to peanuts" → exactly 1 `constraint`, with a sensible slot and triggers
- "lol nice weather today" → `[]`

## T3: ② Store, the bi-temporal memory graph (35 min)

- [ ] `esd/graph_store.py`: `class MemoryGraph` wrapping `nx.MultiDiGraph`
  - `add_fact(fact)`: adds the fact node and `ABOUT` edges to its entity nodes. Entity names are normalised to lowercase and stripped; missing entity nodes are created.
  - `supersede(old_id, new_id, ts)`: sets `old.valid_to = ts` and `old.superseded_by = new_id`, then adds a `SUPERSEDES` edge from new to old. **Never delete anything.**
  - `bump(fact_id)`: `mentions += 1`
  - `active_facts(ts=None)`: facts where `valid_from <= ts` and (`valid_to` is None or `valid_to > ts`)
  - `history(slot)`: all facts for a slot, in time order
  - `known_slots()`
  - `changes()`: list of (old, new) superseded pairs. T7 and T8 use it to show conflicts.
  - `version`: an int that goes up on every change (used for caching)
  - `save(path)` / `load(path)`: via `nx.node_link_data`
- [ ] `tests/test_graph_store.py` (no API calls): add a PostgreSQL decision, supersede it with MongoDB, then check:
  - the active facts are only MongoDB
  - `history` returns both
  - the PostgreSQL node still exists

**Done when:** `pytest` passes.

## T4: ③ Update, the "replaced-by" revision (35 min)

- [ ] `esd/revision.py`: `integrate(graph, extracted: list[ExtractedFact], ts, source)`
  - For each new fact, the **candidates** are active facts with the **same slot**, plus the top 3 active facts of the same kind with cosine > 0.75.
  - No candidates → add the fact.
  - Otherwise, make **one** LLM call per new fact. It labels each candidate `same | replaces | unrelated` (structured output), and we act on the label:
    - `same` → `bump(old)`, don't add the new fact
    - `replaces` → add the new fact, then `supersede(old, new)`
    - `unrelated` → add the new fact
  - A fact's embedding is `embed(statement + " | " + ", ".join(triggers))`. It is stored only in the cache, which keeps the graph JSON clean.

**Done when:**
- "We'll use PostgreSQL" → "Actually let's switch to MongoDB" gives 2 facts, with PostgreSQL superseded
- Saying "I'm allergic to peanuts" twice gives 1 fact with `mentions=2`

## T5: ④ Find, the retriever (45 min)

- [ ] `esd/retriever.py`: `retrieve(graph, question, ts) -> list[Hit]`
  1. **Expand the question:** a cheap LLM call lists 5–10 hidden concepts, ingredients, or implications. Example: "macaron recipe" → almond flour, nuts, baking, dessert.
  2. **Seeds:** embed the question and each concept. Score every active fact (by its statement + triggers) and every entity name by the highest cosine match. Keep scores > 0.3, top 10. **Record which concept matched best as `via`.**
  3. **Graph walk:** `nx.pagerank(undirected simple copy, personalization=seeds, alpha=0.85, weight="weight")`
  4. **Score:** `ppr × exp(-DECAY[kind] × age_days) × log(1 + mentions)`, plus the seed score. This is the spec's fading formula with hand-set numbers.
  5. **Always-on rules:** every active `constraint` is included, with reason `"standing rule"`.
  6. Give each hit a **reason** for the UI: `"matched via nuts"`, `"linked through rina"`, or `"standing rule"`.

**Done when:** after the allergy message plus 12 filler messages, the question "Give me a macaron recipe" puts the allergy in the top 3 with a readable reason and `via`.

## T6: ⑤ Memory Card + ⑥ Answer + terminal demo (30 min)

- [ ] `esd/memory_card.py`: `build_card(hits, graph, budget) -> str`
  - Sections: `RULES`, `DECISIONS`, `FACTS`, `EVENTS`, then `CHANGED`, e.g. `Database: MongoDB (was PostgreSQL until 2025-03-03)`
  - Each line includes its date.
  - Fill greedily by score, **stopping before the token count goes over `budget`**.
- [ ] `esd/chat.py`: `class ESDAssistant`
  - `answer(q, ts, recent)`: retrieve → card → messages → chat → `Answer`
    - The messages are: system prompt ("Use the MEMORY CARD. Always respect active RULES and say so when one applies."), then the card, then `recent`, then the question.
    - `used` = the ids of the facts that made it onto the card.
  - `observe(msg, ts)`: extract → integrate → save
- [ ] `scripts/demo_cli.py`: runs the allergy→macaron story and the PostgreSQL→MongoDB story, with fillers, printing the card and the answer.

**⛳ CHECKPOINT A. Done when:**
- The macaron answer is nut-free and mentions the allergy
- The database code uses MongoDB

## T7: "Current method" assistant, standard Graph RAG (35 min)

This is what the **bottom graph** shows. Build it **faithfully**, the way LightRAG / GraphRAG-style local search works, and don't make it weak on purpose.

- [ ] `baselines/graph_rag.py`: `class GraphRAGAssistant` (same interface as ESD)
  - **`observe(msg, ts)`:**
    - The same model extracts `Triple(subject, relation, object)` lists (structured output). The speaker is always `"user"`, and relations are short lowercase verbs.
    - Add the triples to an `nx.MultiDiGraph`, skipping exact duplicates.
    - **No dates, no slots, no replacing.** Every triple stays "true" forever. That is the method we're comparing against.
  - **`answer(q, ts, recent)`:**
    - The LLM pulls **keywords** out of the question (LightRAG does this step too).
    - Embed the keywords and match the top-5 entities by cosine (≥ 0.35).
    - Take every triple touching those entities (1 hop).
    - Write them out as `subject — relation — object` lines, capped at 2,000 tokens.
    - Send: system prompt → "KNOWLEDGE:" + the lines → `recent` → question.
    - `used` = the ids of the edges it included. `extra["matched"]` = entity → keyword.
  - **`conflicts(esd_changes)`:** returns two kinds, each with a label:
    - (a) edges that share a subject and relation but have different objects
    - (b) for each change our method detected (`MemoryGraph.changes()`), the edges in this graph touching the old and new entities, labelled *"a change was detected here; this graph still treats both as true"*
  - `save` / `load` → `data/memory/graph_rag.json`

**Done when:** after PostgreSQL → MongoDB, `conflicts()` returns the pair and `answer("write the DB connection code")` includes both facts in its knowledge text.

## T8: Graph drawing for both methods (40 min)

- [ ] `esd/visualize.py` using pyvis. Both functions return an HTML string built with `Network(height="300px", width="100%", directed=True, cdn_resources="remote")` and `net.generate_html()`.
- [ ] `draw_esd(graph, last_answer, question) -> str`, the **top panel**:

  | Element | Style |
  |---|---|
  | Entity nodes | small grey dots |
  | Fact nodes | colored by kind: **rule** red `#e5484d`, **decision** blue `#3e63dd`, **fact** green `#30a46c`, **event** purple `#8e4ec6` |
  | Superseded facts | grey, dashed border, label starts with `(old)` |
  | Change arrow | orange dashed arrow from old → new labelled **"replaced by"** |
  | After a question | ⭐ gold star node `Q: <question>`, with dotted gold edges to the seed facts labelled with `via` (e.g. "nuts") |
  | Facts on the Memory Card | thick gold border |

- [ ] `draw_graph_rag(g, last_answer, conflicts, question) -> str`, the **bottom panel**:

  | Element | Style |
  |---|---|
  | Entities | plain blue dots |
  | Edges | grey, labelled with the relation |
  | **Conflict edges** | **thick red** |
  | After a question | ⭐ star with dotted edges to the matched entities, labelled with the keyword |
  | Edges it used | gold |

- [ ] Both panels:
  - Labels are cut to about 28 characters; the full text shows on hover (`title`).
  - Physics stabilises in about 150 iterations, then stops, so the graph doesn't keep jiggling.
  - **Same size cap for both** (fair): the 60 most recent nodes plus everything highlighted.
- [ ] `stats_line(answer, conflicts)` → e.g. `"Sent to AI: 287 tokens · Facts used: 6 · Conflicts: 0"`

**Done when:** a small script saves `data/preview_esd.html` and `data/preview_graph_rag.html` after the T6 stories. Opening them shows red/blue nodes, the "replaced by" arrow on top, and a red conflict at the bottom.

## T9: Demo screen, 70/30 with multi-chat and two graphs (70 min)

- [ ] `app.py`: `st.set_page_config(layout="wide", page_title="ESD Memory", initial_sidebar_state="collapsed")`
- [ ] `st.session_state` holds: `chats`, `current_chat_id`, `esd`, `graph_rag`, `sim_date`, `compare` (default on). **Never rebuild these at the top level:** Streamlit reruns the whole script on every click.
- [ ] `left, right = st.columns([7, 3], gap="medium")`

**Left 70%: chat**
- [ ] **Chat bar:** `st.selectbox` listing the chats (newest first) + a **"+ New chat"** button. The title is the first ~40 characters of the first message.
- [ ] **Date bar:** shows the simulated date, with **"+1 day"** and **"+1 week"** buttons.
- [ ] **Messages:** in `st.container(height=620)` using `st.chat_message`. Under each assistant reply:
  - `st.expander("Details")`: the Memory Card (`st.code`), "Why these facts" (the hits with reason and `via`), and tokens sent
  - `st.expander("What the current method answered")`: the Graph RAG answer, its tokens, and the triples it used
- [ ] **Input:** `st.chat_input("Type a message...")` inside the left column.
- [ ] **When a message is sent:**
  1. Save it to the chat.
  2. Run `esd.answer()` and `graph_rag.answer()` **in parallel** (`ThreadPoolExecutor(2)`) inside `st.spinner`, passing `recent` = the last 4 messages of **this** chat.
  3. Save the reply along with both `Answer`s.
  4. Run `esd.observe()` and `graph_rag.observe()` in parallel.
  5. Save the chat and both memories, then `st.rerun()`.

**Right 30%: two graphs**
- [ ] **Top:** `st.container(height=400, border=True)` containing:
  - the heading **"Our method (ESD)"**
  - `components.html(draw_esd(...), height=300)`
  - a legend caption and the stats line
- [ ] **Bottom:** the same layout, headed **"Current method: standard Graph RAG"**, drawn with `draw_graph_rag(...)`
- [ ] Both panels highlight the **latest question in the current chat**.

**Sidebar (collapsed)**
- [ ] **"Load demo history":** feeds `eval/background.json` into both memories with a progress bar, then saves a snapshot to `data/demo_snapshot/`. After that, loading is instant. Until T11 exists, use a 10-line placeholder.
- [ ] **"Reset all memory"**, **"Delete this chat"**, and a **"Compare answers"** toggle

**⛳ CHECKPOINT B. Done when** `streamlit run app.py`:
1. can create 2 chats, switch between them, and still has them after a restart
2. **Chat 1:** "I'm allergic to peanuts" → +1 week → **new Chat 2:** "Give me a macaron recipe" gives:
   - a nut-free answer
   - a top-graph star with a path to the red allergy rule
   - the current method's answer visible in the expander
3. PostgreSQL → MongoDB shows the old fact greyed out with a "replaced by" arrow on top, and a **red conflict** at the bottom
4. Both stats lines show tokens; the top stays ≤ 300

**We are now demo-ready.**

## T10: Other 3 baselines (15 min)

- [ ] `baselines/base.py`: shared system prompt and the `Answer` wiring
- [ ] `baselines/no_memory.py`: only `recent`
- [ ] `baselines/full_history.py`: every observed message from all chats, with dates
- [ ] `baselines/vector_rag.py`: embed each past message and send the top-5 by cosine plus `recent`

**Done when:** each baseline answers a question and reports `prompt_tokens`.

## T11: Background life + 8 test scenarios (25 min)

- [ ] `eval/background.json`: about 40 realistic messages over about 6 weeks. Include:
  - job and coworkers
  - friends (Tanvir, Nadia)
  - a cat called Miso
  - hobbies (badminton, photography)
  - favourite foods and desserts, which act as **realistic distractors**
  - tools and learning Japanese

  Don't include anything that contradicts the scenarios. The UI's "Load demo history" and every test run use this same file.
- [ ] `eval/fillers.py`: 20 generic chit-chat lines. Put **≥ 10 fillers between the cue and the question** so the cue falls out of the 4-message window.
- [ ] `eval/scenarios.json`. Each scenario has `id`, `category`, `sessions: [{date, messages[]}]`, `question: {date, text}`, `pass_criteria`

| # | Category | Cue → (weeks later) → question | Passes if… |
|---|---|---|---|
| 1 | hidden rule | peanut allergy → "macaron recipe?" | nut-free, or warns about almonds/nuts |
| 2 | changed decision | PostgreSQL → switch to MongoDB → "write DB connection code" | uses MongoDB |
| 3 | budget | budget $500 → "which laptop should I buy?" | all picks ≤ $500 |
| 4 | timeline | moved Chittagong → Dhaka in March → "where did I live last year?" | Chittagong |
| 5 | multi-hop | Rina is my sister + Rina hates chocolate → "cake for my sister?" | no chocolate |
| 6 | goal | training for a marathon, no alcohol → "plan my Friday night out" | no drinking plans |
| 7 | changed rule | vegetarian → "I eat fish again now" → "dinner idea?" | fish allowed |
| 8 | negative rule | "never book meetings before 10am" → "set a daily standup time" | time ≥ 10:00 |

**Done when:** both JSON files load, and each scenario has ≥ 10 fillers between the cue and the question.

## T12: Examiner AI + evaluation runner + Results page (40 min)

- [ ] `eval/judge.py`: `judge(question, answer, pass_criteria) -> {passed: bool, reason: str}`, using structured output at temperature 0
- [ ] `eval/run_eval.py`:
  - For each of the 5 assistants, **ingest the background life once**, save it, and `deepcopy` it for each scenario. This keeps the run fast and cheap.
  - For each scenario, feed its messages with their dates → `answer` → `judge`.
  - Record `passed`, `prompt_tokens`, `latency_s`, `card_tokens`, `history_tokens`.
  - Flags: `--only esd,graph_rag` and `--limit N`.
- [ ] Outputs:
  - `results/results.csv`
  - `results/summary.md`: pass rate (the spec's CCS %), average tokens, average latency, and compression for ESD
  - `results/chart.png`: pass rate and average tokens per assistant
- [ ] `pages/Results.py` (a Streamlit page) shows:
  - the summary table
  - a **✅/❌ grid** of scenarios × assistants (the easiest view for a non-technical audience)
  - the chart

**Done when:** the Results page shows a filled 5-assistant table and grid. Expect a full run with `gpt-4o-mini` to cost well under $1.

## T13: README, demo script, commit (20 min)

- [ ] `README.md`: what it is (link plan.md), setup, `streamlit run app.py`, `python eval/run_eval.py`, and a screenshot
- [ ] `docs/demo_script.md`, a 4-minute talk track:
  1. Sidebar → **Load demo history**. Both graphs fill up. *"Same messages, two ways of remembering."*
  2. **Chat 1:** "Heads up, I'm allergic to peanuts." and "We'll use PostgreSQL for the project." Point to the red rule node on top.
  3. **+1 week:** "Actually, let's switch to MongoDB." On top, the old fact goes grey with a "replaced by" arrow. At the bottom, both stay true and show as a **red conflict**.
  4. **+1 week, New chat:** "Give me a macaron recipe." On top, the star lights up a path through "nuts" to the allergy. Open **"What the current method answered."**
  5. "Write the database connection code." Compare the two answers.
  6. Point at the **Sent** counters: flat on top, growing at the bottom.
  7. Open the **Results** page and walk through the ✅/❌ grid.
- [ ] Run the demo once before presenting, so the snapshot and embedding cache are warm.
- [ ] Commit.

---

## Stretch (only if time is left)
- [ ] A toggle in the bottom panel: **Graph RAG | Vector RAG "similarity map"** (the question in the centre, messages placed by similarity, top-5 highlighted)
- [ ] **Token-growth chart** on the Results page: history length 10 / 50 / 100 / 200 messages, full-history tokens (counting only, no API calls) vs. the flat 300-token card
- [ ] Extraction in a background thread in the app, as in the real spec
- [ ] More scenarios

## Late-night gotchas
- **Structured-output errors:** every `parse` call is in try/except and returns an empty result, so the app never crashes mid-demo.
- **Rate limits:** `max_retries=5` on the client. Two parallel calls per message is fine.
- **Streamlit reruns the whole script on every click:** keep all state in `st.session_state`.
- **`st.chat_input` inside a column:** needs a recent Streamlit. If it pins to the bottom of the page instead, that's acceptable. The fallback is `st.form` + `st.text_input`.
- **pyvis in Streamlit:** render with `streamlit.components.v1.html(html, height=...)`. Don't use `net.show()`, which writes files and opens a browser.
- **Never commit `.env`.** Check `git status` before committing.
