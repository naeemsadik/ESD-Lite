# Results

| Assistant | Rules respected (CCS) | Passed | Avg tokens sent | Avg memory tokens | Avg response time |
|---|---|---|---|---|---|
| No memory | 0.0% | 0/8 | 229 | 0 | 2.42s |
| Full history | 100.0% | 8/8 | 1,265 | 1,046 | 3.02s |
| Vector RAG | 87.5% | 7/8 | 332 | 106 | 2.94s |
| Standard Graph RAG | 25.0% | 2/8 | 265 | 43 | 4.25s |
| ESD-Lite (ours) | 100.0% | 8/8 | 489 | 275 | 4.08s |

Compression for ESD-Lite (spec CCR): 73.7% smaller than the full history.

## Per scenario

| Scenario | No memory | Full history | Vector RAG | Standard Graph RAG | ESD-Lite (ours) |
|---|---|---|---|---|---|
| s1_allergy | ❌ | ✅ | ❌ | ❌ | ✅ |
| s2_database | ❌ | ✅ | ✅ | ❌ | ✅ |
| s3_budget | ❌ | ✅ | ✅ | ❌ | ✅ |
| s4_timeline | ❌ | ✅ | ✅ | ❌ | ✅ |
| s5_multihop | ❌ | ✅ | ✅ | ✅ | ✅ |
| s6_goal | ❌ | ✅ | ✅ | ❌ | ✅ |
| s7_diet_change | ❌ | ✅ | ✅ | ✅ | ✅ |
| s8_meetings | ❌ | ✅ | ✅ | ❌ | ✅ |
