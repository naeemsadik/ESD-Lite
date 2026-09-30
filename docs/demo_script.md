# Demo script (about 4 minutes)

**Before you start:**
1. Run `streamlit run app.py`.
2. Open the sidebar and click **Load demo history**. Both graphs fill up with the same ~40 messages, and the date jumps just past them.
3. Keep **"Also ask the current method"** switched on.

> Opening line: *"Both graphs on the right were built from exactly the same messages. The top one is our method; the bottom one is how today's standard Graph RAG systems remember."*

| # | Do this | Say / point at |
|---|---|---|
| 1 | In the current chat, type: **"Heads up for the future: I'm allergic to nuts, both peanuts and tree nuts."** | Top: a new **red rule** node. Bottom: a new triple, with no date and no type. |
| 2 | Type: **"For the new invoicing service we decided to use PostgreSQL."** | A blue decision node appears on top. |
| 3 | Click **+1 week**, then type: **"Change of plan: we're switching the invoicing service to MongoDB."** | Top: PostgreSQL turns **grey**, with an orange **"replaced by"** arrow to MongoDB. Bottom: both stay "true" and turn **red**, a conflict the current method can't see. |
| 4 | Click **+1 week**, then **➕ New chat**, and type: **"Give me a recipe for macarons I can bake this weekend."** | *"New chat, two weeks later, and 'macaron' shares no words with 'nut allergy'."* Top: the ⭐ question links through **"almond flour / nuts"** to the allergy. The answer is nut-free. |
| 5 | Open **"What the current method answered"** under the reply | Compare the two answers and what each method sent to the AI. |
| 6 | Type: **"Write the Python code to connect the invoicing service to its database."** | Ours uses MongoDB. Check what the current method used. |
| 7 | Point at the **Sent to AI** lines under both graphs | Ours: the Memory Card never goes above 300 tokens, however long memory gets. The line below it shows how big the full history already is, and that keeps growing. The current method may send *less* text, because it only sends what its word-matching finds. That's exactly why it missed the allergy. Be upfront about this. |
| 8 | Open the **Results** page (sidebar) | The ✅/❌ grid over 8 tests × 5 assistants, the two charts, and the growth chart (full history keeps climbing; our card stays capped). |

**What the rehearsal showed (30 Sep 2026, gpt-4o-mini):**
- Step 3: our memory marked PostgreSQL as replaced, and the current method's graph showed 1 red conflict.
- Step 4: ours gave a nut-free recipe (sunflower-seed flour instead of almond flour). The current method gave a classic almond-flour recipe; its keyword match found "banana bread" and "weekend", not the allergy.
- Step 6: ours wrote MongoDB code. The current method wrote code for both PostgreSQL and MongoDB.
- Cost: ours sent 449–909 tokens per question and the current method 186–680. The saving is against full history, and it grows with chat length.

**If something goes wrong:**
- Use **Reset everything** in the sidebar, then **Load demo history** again. It's instant after the first time.
- Answers vary a little between runs. Rehearse once so you know what your run shows, and report what actually happens.
