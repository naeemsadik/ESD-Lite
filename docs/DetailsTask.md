# DetailsTask.md: who presents what, and how to prepare

This file splits the project into **three parts, one per team member**. For each part it lists:
- what that member is responsible for
- how their part works, with the exact files and lines
- what they say in the presentation
- the numbers they must know
- the questions they must be able to answer
- a hands-on checklist to prepare with

Swap the names if a different split fits better. Whoever presents a part must be able to answer questions about it.

> **One rule for all three of you:** the paper's Acknowledgment says the project was built with help from an AI coding assistant. If anyone asks, give the same answer: *we used an AI coding assistant, and each of us is responsible for understanding and defending our own part.* Then prove it by explaining your part in your own words, and by opening your code when asked.

---

## Team overview

| # | Member | Part | Main folders | Talk time |
|---|---|---|---|---|
| 1 | **Farhan Al Imam Somuddro** | Writing memory: extraction, the dated graph, updates | `esd/extractor.py`, `esd/graph_store.py`, `esd/revision.py`, `esd/models.py`, `esd/llm.py`, `esd/config.py` | about 4 min |
| 2 | **Naeem Abdullah Sadik** | Reading memory and the demo app: retrieval, the Memory Card, the screen | `esd/retriever.py`, `esd/memory_card.py`, `esd/chat.py`, `esd/prompts.py`, `esd/base.py`, `app.py`, `esd/visualize.py` | about 6 min (includes the live demo) |
| 3 | **MD. Abid Rayhan Tazim** | Comparison and evaluation: baselines, benchmark, results, paper | `baselines/`, `eval/`, `pages/Results.py`, `results/`, `tests/`, `paper.tex` | about 5 min |

**Running order:** Farhan → Naeem (live demo) → Abid → questions for everyone.

**Handover lines:**
- Farhan → Naeem: *"Now that memory is stored, Naeem will show how the assistant finds the right fact when a question comes in."*
- Naeem → Abid: *"That was one live run. Abid will show how we tested it properly against four other methods."*

---

## What all three must know

Read this part together. Anyone can be asked these.

**The one-sentence pitch.** ESD-Lite stores chat memory as a dated knowledge graph that marks old facts as replaced instead of deleting them. It finds hidden links (macarons → almond flour → nut allergy), and it sends the AI a small Memory Card of at most 300 tokens instead of the whole history.

**Final results** (run 4, 30 Sep 2026, `gpt-4o-mini`, temperature 0, 14 tests):

| Method | Passed | Dev (8) | Held-out (6) | Avg tokens sent | Avg time |
|---|---|---|---|---|---|
| **ESD-Lite (ours)** | **14/14** | 8/8 | 6/6 | 488 | 4.85 s |
| Full history | 13/14 | 8/8 | 5/6 | 1,263 | 3.07 s |
| Vector RAG | 13/14 | 7/8 | 6/6 | 331 | 3.20 s |
| Standard Graph RAG | 9/14 | 4/8 | 5/6 | 275 | 4.03 s |
| No memory | 2/14 | 0/8 | 2/6 | 231 | 2.30 s |

**Things all three must never claim:**
- that the demo uses soft-prefix vectors, a trained GNN, a Perceiver or vLLM (these are future work)
- statistical significance (14 tests is a pilot)
- results on LoCoMo or MSC (we didn't run them)
- that we are "always better than full history" (accuracy was similar; our advantage is cost that doesn't grow)

**Where the details are:**
- [docs/ESD_Presentation_Guide.docx](docs/ESD_Presentation_Guide.docx): the full guide, including 24 prepared answers
- [docs/demo_script.md](docs/demo_script.md): the demo steps
- [paper.tex](paper.tex): the paper
- [results/summary.md](results/summary.md): the raw results

---

## Part 1: Writing memory (Farhan Al Imam Somuddro)

### What you are responsible for
Everything that happens **when a user message arrives**: turning it into typed facts (step 1), storing them in a dated graph (step 2), and updating old facts without deleting them (step 3). You also own the shared plumbing every part uses: the OpenAI helper and the settings.

### How your part works

**Step 1: Extraction** ([esd/extractor.py](esd/extractor.py))
- [`extract()` at line 38](esd/extractor.py#L38) sends one message to `gpt-4o-mini` and receives facts in a fixed format through OpenAI **structured output**. The format is defined in [`ExtractedFact` in esd/models.py:12](esd/models.py#L12).
- Each fact has:
  - `kind`: one of `constraint`, `decision`, `event`, `fact`
  - `statement`: a short third-person sentence
  - `slot`: a topic key like `user.home_city`
  - `entities`
  - `triggers`: situations where a rule matters, e.g. nut allergy → desserts, baked goods, trail mix
  - `valid_from`
- The rules are in the `SYSTEM` prompt at [line 7](esd/extractor.py#L7). Key points:
  - chit-chat → nothing
  - **reuse existing slots**, which makes changes detectable
  - list non-obvious triggers
  - **be faithful**: a dislike must never become an allergy
- [`calendar()` at line 25](esd/extractor.py#L25) computes anchor dates **in code**: yesterday, this week's and last week's Monday, and this and last month's start. The model then *picks* a date instead of calculating one. This fixed a real bug where "at the start of this week" was being read as the wrong day.

**Step 2: The bi-temporal graph** ([esd/graph_store.py](esd/graph_store.py))
- `MemoryGraph` ([line 31](esd/graph_store.py#L31)) is a NetworkX graph with **fact nodes** and **entity nodes**. The links are `ABOUT` (fact → entity) and `SUPERSEDES` (new fact → old fact).
- Every fact has **two timelines** ([`Fact` in esd/models.py:26](esd/models.py#L26)):
  - **valid time** (`valid_from`, `valid_to`): when it was true in the user's life
  - **transaction time** (`recorded_at`, `invalidated_at`): when we learned it, and when we stopped believing it
- [`supersede()` at line 53](esd/graph_store.py#L53) closes the old fact and links it; **nothing is ever deleted**. [Line 57](esd/graph_store.py#L57) sets the old fact's end date to the day the new fact became true.
- [`active_facts()` (line 76)](esd/graph_store.py#L76), [`current_version()` (line 93)](esd/graph_store.py#L93) and [`changes()` (line 104)](esd/graph_store.py#L104) are what the other two parts read.
- Memory is saved as JSON ([`save()`, line 138](esd/graph_store.py#L138)).

**Step 3: Non-destructive revision (AGM-style)** ([esd/revision.py](esd/revision.py))
- [`_candidates()` at line 41](esd/revision.py#L41): current facts with the **same slot**, plus up to **4** facts with cosine similarity ≥ **0.6**.
- The model sees the new fact and each candidate. It **writes a one-sentence reason first**, then chooses `same` / `replaces` / `unrelated` ([`Judgement`, line 19](esd/revision.py#L19)).
- [`integrate()` at line 58](esd/revision.py#L58) acts on the label:
  - `same` → count a repeat ([line 93](esd/revision.py#L93))
  - `replaces` → add the new fact and call `supersede` ([line 100](esd/revision.py#L100))
  - `unrelated` → just add the new fact
- **Why the reason comes first:** without it, the model made mistakes, e.g. "leads the refactor" was marked as replaced by "refactor due end of February". With it, 6 of 6 known check cases were correct.

**Shared plumbing** ([esd/llm.py](esd/llm.py), [esd/config.py](esd/config.py))
- [`chat()` (line 72)](esd/llm.py#L72) makes normal calls; [`parse()` (line 82)](esd/llm.py#L82) makes structured calls.
- [`embed()` (line 127)](esd/llm.py#L127) gets embeddings (`text-embedding-3-small`, 1,536 numbers per text), with a **SQLite cache** so the same text is never paid for twice.
- The settings in `config.py` are the model names, temperature 0, the 300-token card budget, the recent window of 4, and the fade rates.

### Your presentation (about 4 minutes)
1. **The problem (1 min).** Chatbots forget. Pasting the whole history is expensive and still misses things. Normal search looks for similar words: "macaron recipe" shares no words with "nut allergy".
2. **Step 1 (1 min).** Show a stored fact. The allergy record has kind, slot, entities, **triggers** and dates. Explain triggers as the model predicting when a rule will matter.
3. **Step 2 (1 min).** Two timelines. Example: the user said on 25 Feb that they moved to Dhaka on 24 Feb. So "lives in Chittagong" is valid until 24 Feb, and we stopped believing it on 25 Feb.
4. **Step 3 (1 min).** Old facts are replaced, never deleted. The model writes a reason before choosing a label. In the app, PostgreSQL turns grey with a "replaced by" arrow.

**Your demo moment:** Naeem types the set-up messages. As he does, point at the red rule node appearing, then at PostgreSQL turning grey with the orange "replaced by" arrow.

### Numbers you must know
- **4** kinds of fact; **6–10** triggers per rule
- **2** timelines per fact
- Revision candidates: same slot, plus up to **4** with similarity ≥ **0.6**
- Revision check: **6 of 6** correct. Date check: **5 of 6** (the sixth, "last Monday" said on a Thursday, is ambiguous English)
- The background life gives **33–37 facts** in our memory
- **1 of 40** background messages caused a wrong replacement: a new hobby replaced an old one. Nothing was lost, because the old fact is kept.

### Questions you must be able to answer
| Question | Short answer |
|---|---|
| What does bi-temporal mean? | Two timelines per fact: when it was true in real life, and when the system knew it. Example: the Chittagong → Dhaka move. |
| What is AGM belief revision? How did you use it? | AGM is a 1985 theory of changing beliefs consistently when new information contradicts old. We close the old fact's time ranges and link it to the new one; nothing is deleted. |
| Why does the model write a reason before the label? | Label-only judging made mistakes; asking for the reason first fixed them (6/6 on our check cases). |
| What if extraction is wrong? | It happens (1 of 40). Nothing is deleted, so the old fact still shows as history. The graph is visible, and the prompt tells the model to stay faithful. |
| Why use slots? | So the same topic always gets the same key, which makes changes easy to detect (`user.home_city`). |
| How do you handle "last week" and other relative dates? | Code computes the anchor dates; the model only picks one. This fixed a real bug. |
| Why OpenAI and not a local model? | Our PCs can't run a large model; the API is cheap. The model name is one setting. |

### Prep checklist (do all of these)
- [ ] Read guide sections **4.2, 4.3 and 4.4** and the Q&A answers on bi-temporal, AGM and extraction errors.
- [ ] Open the three files above and read each function linked. Explain `supersede()` aloud in your own words.
- [ ] Run `python scripts/demo_cli.py` and read what gets **added / replaced**.
- [ ] Run `python scripts/check_revision.py` and see the 6 cases with their labels.
- [ ] Run `python -m pytest tests/test_graph_store.py` (no key needed).
- [ ] Open `data/memory/esd.json` and find the allergy fact. Point to its `triggers`, `valid_from` and `recorded_at`.
- [ ] Explain your 4 minutes to Naeem and Abid without slides.

### Weaknesses to admit if asked
- Extraction runs straight after each reply rather than in the background as the spec describes. A background thread risked race conditions in a live demo.
- Replacement judging is done by an LLM and can be wrong (1 of 40).

---

## Part 2: Reading memory and the demo app (Naeem Abdullah Sadik)

### What you are responsible for
Everything that happens **when a question arrives**: finding the relevant facts (step 4), packing them into the Memory Card (step 5), and answering (step 6). You also own **the demo screen**: the 70/30 app with multiple chats, simulated dates, and both live graphs. You run the **live demo**.

### How your part works

**Step 4: Retrieval** ([esd/retriever.py](esd/retriever.py), [`retrieve()` at line 61](esd/retriever.py#L61))
1. **Expand the question** ([line 66](esd/retriever.py#L66)). The model lists 6–10 concepts the question implies. For "macaron recipe" these include almond flour, egg whites and baking.
2. **Find seeds.** Embed the question and each concept, then compare them with every fact (its statement **plus its triggers**) and every entity.
   - Up to **10** seeds are chosen, with minimum similarity **0.20**.
   - **4 places are reserved** for the question's own best matches ([line 112](esd/retriever.py#L112)), so vague concepts can't crowd them out.
   - **Old facts are searched too** ([line 95](esd/retriever.py#L95)). If an old fact matches, its *current* version becomes the seed, and that card line carries the history.
3. **Follow links** with **Personalized PageRank** ([line 128](esd/retriever.py#L128), damping **0.85**). Think of water poured on the seeds flowing along the links. It reaches facts two steps away: sister → Rina → "Rina dislikes chocolate".
4. **Score** ([line 141](esd/retriever.py#L141)):
   `score = (seed + 0.5 × link) × exp(−λ × days since last mentioned) × log2(1 + mentions)`.
   - λ = 0 for rules, 0.005 for decisions, and 0.01 for facts and events.
   - This is the spec's fading-weight formula, with measured similarity in place of the learned part.
5. **Rules are always considered** ([line 169](esd/retriever.py#L169)). Other facts are limited to the best **12**.

**Step 5: The Memory Card** ([esd/memory_card.py](esd/memory_card.py), [`build_card()` at line 40](esd/memory_card.py#L40))
- Four sections: RULES, DECISIONS, FACTS, EVENTS. Every line has its dates, and replaced facts appear inside the line of the fact that replaced them ([`_line()`, line 20](esd/memory_card.py#L20)).
- Lines are added in score order, rules first. A line is skipped if the card would go over **300 tokens** ([line 50](esd/memory_card.py#L50)).
- This is our text version of the spec's "64 soft tokens": the card never grows, however long the chat gets.

**Step 6: The answer** ([esd/prompts.py](esd/prompts.py), [esd/base.py](esd/base.py))
- [`ASSISTANT_PROMPT` (line 8)](esd/prompts.py#L8) is **shared by every method we compare**. That is what makes the comparison fair. It includes today's date and weekday, and tells the model to respect rules, check every suggested item against them, and prefer the latest information.
- [`BaseAssistant.answer()` (line 38)](esd/base.py#L38) sends: prompt + memory + the last 4 messages + the question. Only the memory block differs between methods.
- [esd/chat.py](esd/chat.py) wires steps 1–6 together (`ESDAssistant`).

**The demo app** ([app.py](app.py), [esd/visualize.py](esd/visualize.py))
- [`handle_message()` (line 162)](app.py#L162) sends every message to **both** our method and the standard Graph RAG:
  - the two answers run in parallel ([line 177](app.py#L177))
  - then both memories are updated in parallel ([line 188](app.py#L188))
- [`draw_esd()` (line 99)](esd/visualize.py#L99) draws the top graph:
  - colours by kind; old facts grey with an orange "replaced by" arrow
  - the ⭐ question with the gold path it followed
- [`draw_graph_rag()` (line 198)](esd/visualize.py#L198) draws the bottom graph, with conflicts in red.
- Both graphs are limited to **40 points** each, so the comparison is fair. Each panel has an **⤢ Enlarge** button.
- The sidebar has: Load demo history (instant, from a saved snapshot), Reset everything, and the compare toggle.

### Your presentation (about 6 minutes, mostly live)
1. **Retrieval in one breath (1 min).** Expand the question, match facts and triggers, follow links, always keep rules, fit to 300 tokens.
2. **The live demo (5 min).** Follow [docs/demo_script.md](docs/demo_script.md) exactly:
   - 8 set-up messages, then two **+1 week** clicks
   - 6 questions, each in a **➕ New chat**
   - after each answer, open **"What the current method answered"**
   - point at the ⭐ path in the top graph and the red conflict in the bottom graph
3. **Say this line:** *"The current method's answers aren't random. It matched 'standing desk' to 'daily standup' and 'banana bread' to 'macarons'. Similar words aren't the same as relevant meaning."*

**Expected results** (rehearsed 30 Sep; ours passed 6 of 6):

| Question | Ours | Current method |
|---|---|---|
| Macarons | nut-free | almond flour |
| Standup | 10:00 | 9:00 |
| Laptop | all ≤ $500 | all above $500 |
| Friday night | no alcohol | ends at a bar |
| City on 20 Feb | Chittagong | doesn't know |
| DB code | MongoDB | MongoDB this time (it failed 7 of 9 runs overall) |

### Numbers you must know
- Seeds: up to **10**, **4** reserved, minimum **0.20**. PageRank damping **0.85**. Top **12** facts. Card ≤ **300** tokens (218–300 in practice).
- Tokens per question: ours **488** on average vs full history **1,263** (**61% fewer**). In the demo, ours was 395–462.
- Full history goes over our whole card after about **25 messages**. At 800 messages it's **14,922** tokens.
- Our response time: **4.85 s**, the slowest. Vector RAG takes 3.20 s. The cause is one extra call to expand the question.

### Questions you must be able to answer
| Question | Short answer |
|---|---|
| What is Personalized PageRank and why use it? | A graph score that starts from chosen seed points and follows links. It reaches facts two steps away (sister → Rina → chocolate). HippoRAG uses the same idea. |
| Isn't question expansion just asking the LLM? | Yes, and that's the point. The model uses its world knowledge *before* the search (macarons contain almond flour). Plain similarity search can't do that. Triggers do the same thing at write time. |
| Why 300 tokens? | It mirrors the spec's fixed budget of 64 soft tokens, in text. It's one setting (`ESD_CARD_TOKEN_BUDGET`). |
| Why reserve 4 seeds for the question? | Vague concepts once pushed out the right fact. That caused our only failure in run 1, the timeline test. |
| How do you answer "where did I live on 20 Feb"? | Old facts are searched too. The match brings in the current fact, whose card line shows the old one with its dates. |
| Why is yours slower? | One extra model call to expand the question. It could run in parallel with the embedding step, or be cached. |
| Is the comparison fair? | Same model, same prompt ([esd/prompts.py](esd/prompts.py)), same messages, same examiner. Only the memory differs. |
| Why is the Graph RAG conflict shown in red? | We use the changes our method detected to *find* both facts in its graph. Its graph really does store both as true; the red colour just points them out. |

### Prep checklist
- [ ] Read guide sections **3, 4.5, 4.6, 4.7 and 7**.
- [ ] Open [esd/retriever.py](esd/retriever.py) and walk through `retrieve()` (lines 61–174) aloud. Explain the scoring line in your own words.
- [ ] **Run the full demo at least twice** on the presentation laptop, with the internet connection you'll have on the day.
- [ ] Practise **Enlarge**, zooming by scrolling, and hovering over a point to show its dates.
- [ ] Practise recovery: sidebar → **Reset everything** → **Load demo history** (takes 2 seconds).
- [ ] Open a Details expander under an answer, and read out the Memory Card and "why these facts".
- [ ] Explain your part to Farhan and Abid without slides.

### Weaknesses to admit if asked
- Slower than vector RAG, and it sends more tokens than the retrieval baselines. The saving is against full history.
- The graphs get crowded at a small size. That's what **Enlarge** is for.
- Answers can vary slightly between runs, so rehearse on the day.

---

## Part 3: Comparison and evaluation (MD. Abid Rayhan Tazim)

### What you are responsible for
Proving whether the method works:
- the **four comparison methods**
- the **benchmark** (test data)
- the **examiner** and **evaluation runner**
- the **Results page**
- the **offline tests**
- the **paper**

You present how the other methods work, how we tested, the results, the limitations and the future work.

### How your part works

**The comparison methods** ([baselines/](baselines))
- **No memory** and **Full history** ([baselines/simple.py](baselines/simple.py)): full history pastes every past message with its date.
- **Vector RAG** ([`VectorRAGAssistant`, line 50](baselines/simple.py#L50)): each message is embedded, and the **top 5** by cosine similarity are sent ([line 61](baselines/simple.py#L61)).
- **Standard Graph RAG** ([baselines/graph_rag.py](baselines/graph_rag.py)), built in the style of LightRAG / GraphRAG local search:
  - [`observe()` (line 92)](baselines/graph_rag.py#L92): the LLM extracts (subject, relation, object) triples. There are **no dates**, and a triple is **never retired**.
  - [`memory_block()` (line 105)](baselines/graph_rag.py#L105): the LLM extracts keywords, which are matched to the **top 5 entities** (similarity ≥ **0.35**). All triples **1 hop** away are sent as text, up to **2,000 tokens**.
  - [`conflicts()` (line 150)](baselines/graph_rag.py#L150) is used only for the red colouring in the app.
- Every method inherits [`BaseAssistant`](esd/base.py#L14), so they all use the same prompt and model.

**The benchmark** ([eval/](eval)). Written by our team, with AI assistance.
- [eval/background.json](eval/background.json): **40** messages from one invented user over 6 weeks (6 Jan–14 Feb 2025). It includes near-misses that similarity search confuses with the right fact (banana bread, rasmalai, "standing desk").
- [eval/fillers.py](eval/fillers.py): **20** chit-chat lines.
- [eval/scenarios.json](eval/scenarios.json): **14** scenarios, **8 development** and **6 held-out** (the held-out ones were written after the fixes and never used for tuning). Each has dated cue messages, a question weeks later, and a written pass/fail rule.

**The runner** ([eval/run_eval.py](eval/run_eval.py))
1. [`build_base()` (line 47)](eval/run_eval.py#L47): each method reads the background life once. The result is cached, and rebuilt automatically if the memory code changes.
2. [`scenario_stream()` (line 60)](eval/run_eval.py#L60) builds the test stream: each cue is followed by **6 fillers**, and the last cue by **10**. This pushes the cue out of the 4-message recent window, so only long-term memory can answer.
3. [`run_one()` (line 71)](eval/run_eval.py#L71): copy the base, feed it the stream, ask the question, and have the examiner mark the answer.
4. [`judge()` in eval/judge.py:17](eval/judge.py#L17): `gpt-4o-mini` at temperature 0 marks pass/fail against the written rule and gives a one-line reason.
5. The runner writes `results/summary.md`, `results.csv`, `answers.json` and `chart.png`. [`rejudge()` (line 217)](eval/run_eval.py#L217) re-marks saved answers after a criterion changes.

**Results page** ([pages/Results.py](pages/Results.py)): the table, the ✅/❌ grid, two bar charts, and the **token-growth chart**.

**Tests** ([tests/](tests)): **12** offline tests that use a fake OpenAI stand-in, so they need no key.

### Your presentation (about 5 minutes)
1. **The other methods (1.5 min).**
   - Vector RAG: the top 5 similar messages. It misses hidden links.
   - Standard Graph RAG: triples with no dates and no replacement, found by keyword matching. It keeps both databases as "true".
2. **How we tested (1 min).** 40 background messages, cues, fillers, a question weeks later, a written rule, and an examiner. 8 development and 6 held-out tests. Same model and prompt for everyone.
3. **Results (1.5 min).** The table: 14/14, 13, 13, 9, 2. Then:
   - on the allergy test, only ours and full history passed
   - full history suggested banana-boat rides despite the "no boats" rule
   - show the growth chart: full history climbs to about 15,000 tokens by 800 messages, while ours stays at 300 or less
4. **Limits and future work (1 min).**
   - This is a pilot: 14 tests, written by us, with short histories.
   - Next steps: the neural soft-prefix version on an open model; LoCoMo and LongMemEval; independent tests; human raters.

**Your demo moment:** the **Results** page, with the ✅/❌ grid and the growth chart.

### Numbers you must know
- The final results table above. Know it by heart.
- **40 / 20 / 14**: background messages / fillers / scenarios. **8** development, **6** held-out.
- The run history:
  - run 1: ours **7/8**, which led to the retriever fix
  - run 2: **8/8**
  - run 3: **14/14**, when the held-out tests were added
  - run 4 (final): **14/14**, after the date fix
- Graph RAG varied: **7/14** in run 3, **9/14** in run 4.
- Compression (CCR): **73.9%**. Tokens: ours **488**, full history **1,263**.
- The final run made **714** API calls. The whole project used a little over a million tokens, well under a dollar.
- The examiner's hand check found **2** lenient marks, both helping "No memory":
  - the cake test (it suggested nothing); we fixed that criterion
  - the gluten test (it suggested granola); left as marked

### Questions you must be able to answer
| Question | Short answer |
|---|---|
| What dataset did you use? | No training dataset; we didn't train anything. For testing we built our own synthetic benchmark (40 background messages, 14 scenarios), because we had to control exactly which fact is planted and which question needs it. LoCoMo is the next step. |
| Who wrote the tests? | Our team, with AI assistance. That's a limitation: the tests aren't independent. The held-out split stops us tuning to them. |
| Did you tune on the test set? | The 8 development tests were used while building, and every run is saved. The 6 held-out tests were never used for tuning; ours passed all 6. |
| Why did full history score so high? Why not just use it? | The histories are short (about 1,000 tokens). Its cost grows with every message (about 15,000 tokens at 800 messages), and it still missed the "no boats" rule once. |
| Was Graph RAG weakened on purpose? | No. Same model, prompt, messages and examiner, built like LightRAG local search. Its failures come from its design: no dates, no replacement, keyword matching. Show [baselines/graph_rag.py](baselines/graph_rag.py). |
| How do you know the examiner is right? | Written criteria, temperature 0, a reason for every mark, and a hand check (2 lenient marks found and reported). Human raters would be the next improvement. |
| Is 14 tests enough? | No; it's a pilot, and we don't claim statistical significance. |
| Why aren't the paper's LoCoMo results there? | We didn't run LoCoMo; that's future work. The paper reports only what we measured. |

### Prep checklist
- [ ] Read guide sections **5, 6, 7, 10, 13 and 14**, and the whole Q&A section.
- [ ] Open [eval/scenarios.json](eval/scenarios.json). Read all 14, and be able to explain any one of them end to end.
- [ ] Open [results/summary.md](results/summary.md) and [results/answers.json](results/answers.json). Find vector RAG's almond-flour answer on `s1_allergy` and full history's banana-boat answer on `h6_no_boats`.
- [ ] Run `python -m pytest` (12 tests, no key needed).
- [ ] Run a small real evaluation: `python eval/run_eval.py --only esd,vector_rag --limit 2`. It costs a few cents, and you'll see the runner work. **Afterwards restore the full results** by running `git checkout results/`, because a small run overwrites them.
- [ ] Read [paper.tex](paper.tex), especially the Results, Limitations and Future Work sections.
- [ ] Explain your part to Farhan and Naeem without slides.

### Weaknesses to admit if asked
- Small, synthetic benchmark written by the builders; short histories; one model family both answers and marks.
- We didn't compare against HippoRAG 2 or Zep directly.

---

## Who answers which questions

| If the question is about… | Answers | Backup |
|---|---|---|
| Extraction, slots, triggers, dates, bi-temporal, AGM, replacements | Farhan | Naeem |
| Retrieval, expansion, PageRank, scoring, Memory Card, the app, latency | Naeem | Farhan |
| Dataset, benchmark, baselines, fairness, results, the examiner, limits, future work, the paper | Abid | Naeem |
| "Why does it work?" (the big picture) | Naeem | Abid |
| "Did you use AI?" | Anyone: the same one-line answer | |

---

## Rehearsal plan

| When | What |
|---|---|
| **Day 1** | Each person reads their own section of this file and the matching guide sections, then opens their files and reads every linked function. |
| **Day 2** | Each person explains their part to the other two in 3–4 minutes, without slides. The other two ask questions from that person's table. |
| **Day 3** | A full run-through with a timer (15 minutes), including the live demo on the presentation laptop. |
| **Day 3** | Mock Q&A: each person asks the others 5 questions from the guide's Q&A section. |
| **On the day, 30 min before** | Start the app → Reset everything → Load demo history → check that the date shows 17 Feb 2025 → open the Results page in a second tab → check the internet. |

**Final checklist on the day**
- [ ] The laptop is charged, and the internet works (the app needs OpenAI).
- [ ] `.venv\Scripts\activate` → `streamlit run app.py`
- [ ] Sidebar: **Reset everything** → **Load demo history** → the date shows **17 Feb 2025**
- [ ] "Also ask the current method" is **on**
- [ ] The Results page is open in a second tab
- [ ] [docs/demo_script.md](docs/demo_script.md) is printed or open on a phone
