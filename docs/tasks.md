## Part 1: Writing memory (extraction, the dated graph, updates)
**Suggested: Farhan Al Imam Somuddro**

| | |
|---|---|
| **Owns** | Steps 1–3: typed fact extraction, the bi-temporal knowledge graph, and "replaced-by" revision without deleting anything |
| **Files** | `esd/extractor.py`, `esd/graph_store.py`, `esd/revision.py`, `esd/models.py`, plus the shared setup: `esd/llm.py` (OpenAI calls, embedding cache) and `esd/config.py` |
| **Presents** | The problem (why chatbots forget), then how a message becomes dated facts, with the Chittagong → Dhaka example |
| **Demo moment** | Set-up messages 1–8: the red rule node appears, then PostgreSQL goes grey with a "replaced by" arrow |
| **Must be able to answer** | What bi-temporal means, what AGM revision is, why the reason is written before the label, how "this week" becomes a date, and what happens when extraction goes wrong (the 1-in-40 wrong replacement) |

## Part 2: Reading memory and the demo app (retrieval, the Memory Card, the screen)
**Suggested: Naeem Abdullah Sadik**

| | |
|---|---|
| **Owns** | Steps 4–6: question expansion, trigger words, seeding, Personalized PageRank, the scoring formula, the 300-token Memory Card, the shared answer prompt, and the 70/30 app with both live graphs |
| **Files** | `esd/retriever.py`, `esd/memory_card.py`, `esd/chat.py`, `esd/prompts.py`, `app.py`, `esd/visualize.py`, `esd/chats.py` |
| **Presents** | How a question finds hidden links (macaron → almond flour → nut allergy), then **runs the live demo**: the six questions, pointing at both graphs |
| **Demo moment** | Questions 1–6: the ⭐ path in the top graph, and "Compare with the current method" under each answer |
| **Must be able to answer** | What Personalized PageRank is, why 300 tokens, why 4 seed places are reserved for the question's own matches, how old facts answer questions about the past, and why ours is slower (the extra expansion call) |

## Part 3: The comparison and evaluation (baselines, benchmark, results)
**Suggested: MD. Abid Rayhan Tazim**

| | |
|---|---|
| **Owns** | The 4 comparison methods (no memory, full history, vector RAG, standard Graph RAG); the benchmark (background life, fillers, 14 scenarios with the development/held-out split); the examiner; the evaluation runner; the Results page; the offline tests; and the paper |
| **Files** | `baselines/`, `eval/`, `pages/Results.py`, `results/`, `tests/`, `paper.tex` |
| **Presents** | How vector RAG and Graph RAG work and why they fail, how the benchmark is built, the results table (14/14, 13, 13, 9, 2), the token-growth chart, limitations, and future work |
| **Demo moment** | The Results page: the ✅/❌ grid and the growth chart |
| **Must be able to answer** | What dataset you used (your own synthetic set, and why), whether the tests were tuned on (the held-out split), how the examiner is checked (two lenient marks found), why full history also scored high, whether Graph RAG was weakened on purpose (no), and why 14 tests is only a pilot |
