# Demo script (about 6 minutes)

The full talk track, explanations and likely faculty questions are in [ESD_Presentation_Guide.docx](ESD_Presentation_Guide.docx). This page is the short version of its section 3.

The whole flow below was rehearsed in the app with `gpt-4o-mini` on 30 Sep 2026. **Our method passed 6 of 6 questions; the current method (standard Graph RAG) failed 5 of 6.**

**Before you start:**
1. Run `streamlit run app.py`.
2. In the sidebar, click **Reset everything**, then **Load demo history**. The date shows 17 Feb 2025.
3. Keep **"Also ask the current method"** switched on.

## Set-up (chat 1)

| # | Do | Type |
|---|---|---|
| 1 | Type | Heads up for the future: I'm allergic to nuts, both peanuts and tree nuts. |
| 2 | Type | For the new invoicing service we decided to use PostgreSQL. |
| 3 | Type | Please remember: never schedule any meetings for me before 10am. Mornings are for deep work. |
| 4 | Type | I live in Chittagong, near the port area. |
| 5 | **+1 day**, then type | My budget for a new laptop is strictly 500 dollars, I can't go above that. |
| 6 | Type | I'm training for the Dhaka marathon in June, so I've completely stopped drinking alcohol until the race. |
| 7 | **+1 week**, then type | Change of plan: we're switching the invoicing service to MongoDB. |
| 8 | Type | Big news: at the start of this week I moved from Chittagong to Dhaka for work. |
| 9 | **+1 week** | (the date is now 4 Mar 2025) |

After step 7, point at the graphs:
- **Top:** PostgreSQL turns grey, with a "replaced by" arrow.
- **Bottom:** PostgreSQL and MongoDB are both still stored as true, shown in red.

## Questions (click **➕ New chat** before each one)

| # | Question | Ours | Current method |
|---|---|---|---|
| Q1 | Give me a recipe for macarons I can bake this weekend. | Nut-free recipe | Almond-flour recipe |
| Q2 | Set up a daily standup time for my team and draft the invite. | 10:00 AM | 9:00 AM |
| Q3 | Which laptop should I buy? Give me three options. | All ≤ $500 | All above $500 |
| Q4 | Plan a fun Friday night out with my friends this week. | No alcohol | Ends at a bar |
| Q5 | Which city was I living in on 20 February? | Chittagong | Doesn't know |
| Q6 | Write the Python code to connect the invoicing service to its database. | MongoDB | MongoDB this time (failed 7 of 9 runs overall) |

**Cost:** ours sent 395–462 tokens per question, and the Memory Card never goes above 300. The full history at that point was about 1,180 tokens, and it keeps growing.

**If an answer differs from this table:** say so. Answers vary a little from run to run, and the Results page shows the full 14-test comparison.
