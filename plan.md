# ESD Memory: Project Plan (Basic Demo Version)

*Written in plain English. You do not need a technical background to read it.*

---

## 1. The problem in one paragraph

AI chatbots forget things. Say you tell an assistant on Monday, *"I'm allergic to peanuts,"* and on Friday you ask, *"Give me a macaron recipe."* It will often suggest a recipe that contains nuts. There are two reasons:

1. **Long chats get too big.** The AI can only read a limited amount of text at once. Sending the whole history every time is slow and costs money.
2. **Normal search doesn't see hidden links.** Most memory systems search old messages for *similar words*. "Macaron recipe" and "peanut allergy" have no words in common, so the search never finds the allergy. The research spec calls this the **Cue-Trigger Disconnect**.

## 2. Our idea in one paragraph

We give the AI **a notebook that organises itself**. After each message, a helper writes down the important facts (people, things, rules, decisions, and *when* they happened) and connects them like a **mind map**. When a new question arrives, we **follow the connections** in the mind map (*macaron → almond flour → nuts → allergy*), so we find what matters even when the words don't match. We then give the AI a **short memory card of fixed size**, not the whole chat history. The cost stays about the same whether the chat has 10 messages or 10,000.

## 3. What changes because we use the OpenAI API

The full research spec assumes we run **our own AI model on very powerful graphics cards** (4–8 NVIDIA A100 GPUs). We will use **OpenAI's online models** through an API key instead. That works well for a demo, but it changes a few parts:

| Part | Full research version | Our demo version | Why we changed it |
|---|---|---|---|
| The AI model | Our own 70-billion-parameter model on big GPUs | An OpenAI model over the internet (for example `gpt-4o-mini`) | No expensive hardware needed. We pay a small amount per use. |
| How memory is given to the AI | Squeezed into **64 hidden number-vectors** placed inside the model ("soft prefix") | Squeezed into a **short, fixed-size text Memory Card** (about 300 tokens, roughly 220 words) | OpenAI models only accept text. There is no way to put raw vectors inside them. |
| Choosing what to remember | A trained neural network (GNN + Perceiver) | **Following the mind-map links** plus simple scoring rules | Training needs big GPUs and lots of data. Following the links does the same job in a simpler way. |
| Where the memory is stored | A graph database server (Memgraph/FalkorDB in Docker) | A Python mind-map library (NetworkX), saved to a file | Simpler. Runs on any laptop. |
| Speed tricks | Custom vLLM + CUDA caching | Reuse saved work when nothing has changed | vLLM only works with models you host yourself. |

**Key message:** the four ideas that make ESD special are **all kept**:
1. An organised memory graph (mind map)
2. Time tracking, and marking "this replaced that" without deleting anything
3. Finding hidden connections that normal search misses
4. A fixed memory budget, so cost doesn't grow with chat length

The only change is the last step, how memory is handed to the AI: a compact **text card** replaces **hidden vectors**.

## 4. How the demo works, step by step

```
 You type a message
        │
        ▼
 ① LISTEN      A small AI reads the message and pulls out facts
        │
        ▼
 ② STORE       Facts go into the mind map, each with dates
        │
        ▼
 ③ UPDATE      If a fact changes, the old one is marked "replaced" (never deleted)
        │
 ─── later, a new question arrives ───
        │
        ▼
 ④ FIND        Follow the mind-map links to find what matters
        │
        ▼
 ⑤ COMPRESS    Write the most important facts onto a small Memory Card
        │
        ▼
 ⑥ ANSWER      Send Memory Card + recent messages + question to OpenAI
```

### Step ① Listen (spec: "Asynchronous Schema Extraction")
After every message, a low-cost OpenAI model reads it and fills in a fixed form with four kinds of facts:
- **Things** (entities): "PostgreSQL", "my sister Rina", "macarons"
- **Rules** (constraints): "allergic to peanuts", "budget under $500"
- **Decisions**: "we will use PostgreSQL for the database"
- **Events**: "moved to Dhaka in March"

This runs **after** the reply is sent, so the user never waits for it.

### Step ② Store with dates (spec: "Bi-Temporal Knowledge Graph")
Each fact becomes a point in the mind map, and related facts are connected by lines. Every fact gets **two dates**:
- **When it was true in real life** (e.g., "lived in Chittagong from 2019 to March 2025")
- **When we wrote it down** (the time of the message)

With both dates, the system can answer questions like *"Where did I live before I moved?"*

### Step ③ Update without deleting (spec: "AGM Belief Revision")
Suppose the user says, *"Actually, let's switch to MongoDB."* We do **not** erase PostgreSQL. Instead we:
1. Mark the PostgreSQL decision as "true until today."
2. Add the new MongoDB decision as "true from today."
3. Draw a **REPLACED-BY** arrow from the old fact to the new one.

So the AI always knows the **current** answer and can still explain the **history**. To spot these changes, we compare each new fact with the most similar old facts and ask the AI: *"Does the new one replace the old one?"*

### Step ④ Find what matters (spec: "Relational Graph Walk")
When a question arrives, we find the right facts in four ways:
- **Always-on rules:** active rules such as allergies, budgets, and deadlines are always considered, because they are few and important.
- **Following links:** we start at the facts closest to the question and spread outward along the mind-map lines, like water flowing through connected pipes. Facts that are close and well connected score higher. (Technical name: *Personalized PageRank*.)
- **Hidden-link helper:** when we store a rule, we also ask the AI *"In what situations would this rule matter?"* For a peanut allergy, it lists things like baking, desserts, satay sauce, and snack bars. These **trigger words** are saved with the rule, so a later question about macarons links straight to the allergy. We also expand each new question the same way (*macaron → almond flour, nuts, baking*).
- **Fading:** old facts that are rarely used slowly lose score over time. Rules and decisions fade much more slowly. (We use the spec's fading formula with hand-set numbers in place of learned ones.)

### Step ⑤ Compress into a Memory Card (spec: "Perceiver Resampler / Soft Prefix")
We take the top-scoring facts and write them onto a short card with a **hard size limit** of about 300 tokens. For example:

```
MEMORY CARD
Rules:     • Allergic to peanuts and tree nuts (since 12 Jan)
Decisions: • Database = MongoDB (replaced PostgreSQL on 3 Mar)
People:    • Rina = sister, birthday 14 Jun, dislikes chocolate
Recent:    • Planning a birthday dessert for Rina
```

The card is always the same size, however long the chat gets. This is our text version of the spec's "64 soft tokens."

### Step ⑥ Answer
We send the Memory Card, the last few messages, and the new question to the OpenAI model, and it answers. For example, it now suggests a **nut-free** dessert and explains why.

## 5. What we will build

| # | Deliverable | What it is |
|---|---|---|
| 1 | **Memory engine** | The Python code for steps ① to ⑥ |
| 2 | **Demo web app** | A chat screen with **multiple chats** and **two live knowledge graphs side by side**: ours and the current standard method's (see 5.1) |
| 3 | **"Current method" assistant** | A faithful copy of today's standard **Graph RAG** approach, built from the same messages, so the audience can compare the two graphs and the two answers |
| 4 | **Test conversations** | About 30 scripted multi-session chats, each hiding an important fact early and testing it later |
| 5 | **Comparison experiment** | Our system against 4 other approaches on the same tests |
| 6 | **Results report** | Tables and charts that show the difference |
| 7 | *(Optional)* **Mini neural add-on** | A small learned "fact picker" that runs on a normal computer (see section 10) |

### 5.1 The demo screen

```
+----------------------------------------------+----------------------------+
| Chat: [Weekend plans v]  [+ New chat]        |  OUR METHOD (ESD)          |
| Date: 12 Mar 2025    [+1 day] [+1 week]      |  live memory graph         |
|----------------------------------------------|                            |
|  You: Give me a macaron recipe               |  (question) -> nuts ->     |
|                                              |      [RULE] peanut allergy |
|  AI:  Here is a nut-free version, because    |                            |
|       you told me you are allergic to        |  PostgreSQL --replaced-->  |
|       peanuts...                             |      MongoDB               |
|                                              |  Card: never over 300      |
|       > Details                              +----------------------------+
|       > What the current method answered     |  CURRENT METHOD            |
|                                              |  (standard Graph RAG)      |
|                                              |  PostgreSQL AND MongoDB    |
|                                              |  both 'true' -> conflict   |
|                                              |  Sends only what its       |
|                                              |  word-match finds          |
| [ Type a message...                 ] Send   |                            |
+----------------------------------------------+----------------------------+
                 70% of the screen                    30%
```
*(Numbers are examples.)*

**Left 70%: the chat**
- You chat with our assistant, just like ChatGPT.
- **Multiple chats:** a "+ New chat" button and a list to switch between chats. Each chat is like a separate day's conversation. **Memory carries over between chats**, just like a real assistant: mention your allergy in one chat, then ask for a recipe in a new chat a week later.
- **A date control** lets us jump forward a day or a week, so the demo can show memory over weeks in a few minutes.
- Under every answer:
  - **"Details"** shows the Memory Card we sent and why each fact was chosen.
  - **"What the current method answered"** shows the standard method's answer to the same question, for a direct comparison.

**Right 30%, top: our knowledge graph (ESD)**
- Colored points for rules, decisions, facts, and events, each with dates.
- Old facts are greyed out, with a **"replaced by" arrow** to the new fact.
- When you ask a question, a **star** appears for your question, and the path it followed lights up (*question → nuts → peanut allergy*).
- A counter shows how much we sent to the AI. The Memory Card **never goes above 300 tokens**. Next to it, we show how big the full chat history already is. That is what an assistant would have to send if it pasted everything, and it keeps growing.

**Right 30%, bottom: the current method's knowledge graph (standard Graph RAG)**
- The same messages, stored the way today's common systems (such as LightRAG and Microsoft GraphRAG) store them: simple "thing → relation → thing" links, **with no dates and no replacing**.
- Contradictions stay side by side. PostgreSQL *and* MongoDB are both "true", and we highlight them in red as a conflict.
- When you ask a question, only facts with **similar words** light up.
- A counter shows how much it sent to the AI. It can be small, because it only sends what its word-matching finds. That is also why it misses hidden links.

**What to point at during the demo:** the top and bottom graphs react differently to the same conversation:

| You do this | Top graph (ours) | Bottom graph (current method) |
|---|---|---|
| Change a decision (PostgreSQL → MongoDB) | Old fact greyed out, "replaced by" arrow | Both kept as true, shown as a red conflict |
| Ask something with a hidden link (macaron) | Path lights up to the allergy | Nothing near the allergy lights up |
| Ask about the past ("where did I live last year?") | Dates on every fact answer it | No dates, so it can't tell old from new |
| Keep chatting for weeks | Memory Card stays at most 300 tokens, while the full history keeps growing | Sends only what its word-matching finds: small, but it misses things |

## 6. How we will prove it works

We run **five assistants** through the same test conversations:

| Assistant | How it remembers | Expected weakness |
|---|---|---|
| **A. No memory** | Only the last few messages | Forgets everything older |
| **B. Full history** | Pastes the entire chat every time | Accurate but slow and expensive; cost keeps growing |
| **C. Normal search** (standard vector RAG) | Searches old messages for similar words | Misses hidden links (macaron vs. allergy) |
| **D. Standard Graph RAG** (the "current method" in the demo) | Builds a knowledge graph of "thing → relation → thing" links, finds entries with similar words, and pastes them in as text | Keeps old and new facts side by side (contradictions) and misses hidden links, because it only finds entries whose words match |
| **E. ESD-Lite (ours)** | Mind map with dates + "replaced by" + link-following + Memory Card | Should be accurate **and** cheap |

**Fair-test rule:** every assistant uses the same OpenAI model, the same messages, and the same examiner. The standard methods are built the way the published systems work. We do **not** weaken them on purpose. If we did, anyone checking the results would see it, and the comparison would prove nothing. Before each test, every assistant's memory is filled with the same ~40-message "background life" (job, friends, hobbies, food), so the memory is realistically full and not a toy with five facts.

### Test conversation types
- **Hidden rule:** "I'm allergic to peanuts" … later … "Suggest a macaron recipe."
- **Changed decision:** "Use PostgreSQL" … "Switch to MongoDB" … "Write the database connection code."
- **Budget limit:** "My budget is $500" … later … "Which laptop should I buy?"
- **Timeline:** "I moved from Chittagong to Dhaka in March" … "Where did I live last year?"
- **Multi-step:** "Rina is my sister" + "Rina hates chocolate" … "What cake should I get for my sister?"

We will also test on a **small sample of LoCoMo**, a well-known public benchmark of long conversations, so the results can be compared with published research.

### What we measure
| Measure | Plain meaning |
|---|---|
| **Rule-following score** (spec: CCS %) | Did the answer respect the old rule? A separate "examiner" AI marks each answer pass/fail against a clear checklist, and we check a sample by hand. |
| **Correct answers** (%) | Were factual questions answered correctly? |
| **Tokens per question** | How much text we sent to OpenAI (this is what we pay for) |
| **Response time** | How long the user waited for the complete answer |
| **Compression** (spec: CCR) | How much smaller the Memory Card is than the full chat |

**What we hope to show:** ESD-Lite follows rules almost as well as "Full history", and much better than "Normal search" and "Standard Graph RAG" on hidden-link and changed-fact tests, while its memory cost stays **flat** (at most 300 tokens) as the conversation grows. With a short demo history, pasting the full history is still cheap. The saving grows with every message, which is why the Results page includes a growth chart. We will report the actual numbers, even where they come out differently. The results also appear on a **Results page** inside the demo app.

## 7. Timeline (about 6 weeks)

| Week | Focus | Result at the end of the week |
|---|---|---|
| 1 | Setup + **Listen** step | Messages turn into clean, structured facts |
| 2 | **Store** + **Update** steps | Mind map with dates; "replaced-by" works and nothing is deleted |
| 3 | **Find** + **Compress** + **Answer** steps | Full working memory chat in the terminal |
| 4 | **Demo web app** + **current-method assistant** | 70/30 screen: multiple chats on the left; our graph (top) and the standard Graph RAG graph (bottom) on the right |
| 5 | **Tests + comparison** | 30 test chats, 4 comparison assistants, examiner AI, first results |
| 6 | **Results + polish** | Charts, final report, rehearsed demo |
| 7 *(optional)* | **Mini neural add-on** | Learned fact picker compared with the rule-based one |

## 8. What we need

- **A normal laptop or PC.** No graphics card is needed; everything heavy runs on OpenAI's servers.
- **Python 3.11 or newer** (free; this PC already has 3.13)
- **An OpenAI API key** with billing turned on. Set a **monthly spending limit** (e.g., $20) in the OpenAI dashboard.
- **Internet connection**

**Estimated cost:** with a low-cost model (e.g., `gpt-4o-mini`) and the cheap embedding model (`text-embedding-3-small`), development should cost a few dollars, and one full run of the experiment should cost **under about $5**. Prices change, so check OpenAI's pricing page. The model name is **one line in a settings file**, so we can switch to a newer or stronger model at any time.

**Free software we'll use:** `openai` (talks to OpenAI), `networkx` (the mind map), `pydantic` (checks the fact format), `numpy` (maths), `streamlit` + `pyvis` (demo web page and mind-map drawing), `pandas` + `matplotlib` (results and charts), `python-dotenv` (keeps the API key secret), `pytest` (automatic tests).

## 9. Project folder layout (for the developer)

```
ESD_Memory/
├── plan.md                  ← this document
├── .env                     ← secret API key (never uploaded to GitHub)
├── requirements.txt
├── esd/                     ← the memory engine
│   ├── config.py            model names, card size, fading speeds
│   ├── extractor.py         ① Listen: message → facts
│   ├── graph_store.py       ② Store: mind map with two dates per fact
│   ├── revision.py          ③ Update: "replaced-by" logic
│   ├── retriever.py         ④ Find: always-on rules, link-following, trigger words, fading
│   ├── memory_card.py       ⑤ Compress: fixed-size Memory Card
│   ├── chat.py              ⑥ Answer
│   └── visualize.py         draws both knowledge graphs for the demo screen
├── baselines/               the 4 comparison assistants
│   ├── graph_rag.py         the "current method" (standard Graph RAG), shown in the bottom graph
│   └── ...                  no memory, full history, normal search
├── eval/
│   ├── background.json      the shared ~40-message "background life"
│   ├── scenarios/           the ~30 test conversations
│   ├── judge.py             the examiner AI
│   └── run_eval.py          runs everything and makes the results table + charts
├── app.py                   the demo screen (chats + two graphs)
├── pages/Results.py         the results page inside the app
├── data/                    saved chats and both memories (not uploaded to GitHub)
└── tests/                   automatic checks (e.g., "old fact is kept but marked replaced")
```

## 10. Optional: the mini neural add-on

If the main demo is finished early, we can add a small version of the spec's neural part that **runs on a normal CPU**:
- A **small graph neural network** reads the mind map and gives every fact an importance score.
- A **small Perceiver** with 64 "slots" looks over those facts. Each slot picks the facts it pays most attention to.
- The facts the slots pick go onto the Memory Card.

We can't feed the 64 vectors directly into OpenAI, but we *can* use them to **choose** what goes on the card. This shows the spec's GNN + Perceiver idea working in a small form. It is trained on our own test conversations, and we compare it with the hand-made scoring rules.

## 11. What is left for the full research version later

These parts need big GPUs or a self-hosted model, so they are **not** in this demo:
- Training the full GNN + Perceiver on large datasets (spec Stage 1 and Stage 2 training)
- Putting the 64 soft vectors directly inside an open model such as Llama
- vLLM speed caching with a custom CUDA kernel
- Full benchmark runs (LoCoMo-Plus, MSC, Stateful SWE-bench)

The demo is designed so these can be **plugged in later**. The Memory Card builder (step ⑤) is one replaceable piece, and everything before it (steps ① to ④) stays the same.

## 12. Risks and how we handle them

| Risk | What we do about it |
|---|---|
| The fact extractor makes mistakes | Use OpenAI's "structured output" mode so facts always come back in the same format; show all facts in the demo so mistakes are visible; add automatic tests |
| A change is detected wrongly (e.g., something marked "replaced" that wasn't) | Only compare with the most similar old facts; nothing is ever deleted, so a mistake can be undone; the timeline makes it visible |
| API costs grow | Cheap model by default, saved embeddings, and a monthly spending limit |
| The API key leaks | Keep it in a `.env` file that is never uploaded to GitHub |
| The examiner AI is unfair | Give it a clear pass/fail checklist and check a sample of its marks by hand |

## 13. Glossary

| Word | Simple meaning |
|---|---|
| **API** | A way for our program to send text to OpenAI and get an answer back over the internet |
| **Token** | A small piece of text (about ¾ of a word). OpenAI charges per token. |
| **RAG** | "Retrieval-Augmented Generation": look up relevant notes first, then answer |
| **Graph RAG** | RAG where the notes are stored as a knowledge graph. Today's common versions have no dates and never mark facts as replaced. This is the "current method" in our demo. |
| **Embedding** | A list of numbers that represents the meaning of a text, so we can measure how similar two texts are |
| **Knowledge graph / mind map** | Facts stored as points, joined by labelled lines ("Rina —is sister of→ user") |
| **Bi-temporal** | Every fact has two dates: when it was true, and when we learned it |
| **Belief revision (AGM)** | A formal way of updating what you believe when new information contradicts old information |
| **Cue-Trigger Disconnect** | The important old fact (cue) and the new question (trigger) share no words, so normal search misses it |
| **Soft prefix** | In the full research version, memory turned into hidden number-vectors placed inside the AI. In our demo, a text Memory Card replaces it. |
| **GNN / Perceiver** | Types of neural networks. A GNN reads graphs; a Perceiver squeezes many inputs into a fixed number of slots. |
