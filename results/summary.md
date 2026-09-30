# Results

| Assistant | Rules respected (CCS) | Passed | Development tests | Held-out tests | Avg tokens sent | Avg memory tokens | Avg response time |
|---|---|---|---|---|---|---|---|
| No memory | 14.3% | 2/14 | 0/8 | 2/6 | 229 | 0 | 2.79s |
| Full history | 100.0% | 14/14 | 8/8 | 6/6 | 1,261 | 1,042 | 3.28s |
| Vector RAG | 92.9% | 13/14 | 7/8 | 6/6 | 329 | 105 | 2.85s |
| Standard Graph RAG | 50.0% | 7/14 | 2/8 | 5/6 | 271 | 49 | 4.51s |
| ESD-Lite (ours) | 100.0% | 14/14 | 8/8 | 6/6 | 488 | 274 | 4.81s |

Development tests were used while building ESD-Lite; held-out tests were written afterwards and not used for any tuning.

Compression for ESD-Lite (spec CCR): 73.7% smaller than the full history.

## Per scenario

| Scenario | Set | No memory | Full history | Vector RAG | Standard Graph RAG | ESD-Lite (ours) |
|---|---|---|---|---|---|---|
| s1_allergy | development | ❌ | ✅ | ❌ | ❌ | ✅ |
| s2_database | development | ❌ | ✅ | ✅ | ❌ | ✅ |
| s3_budget | development | ❌ | ✅ | ✅ | ❌ | ✅ |
| s4_timeline | development | ❌ | ✅ | ✅ | ❌ | ✅ |
| s5_multihop | development | ❌ | ✅ | ✅ | ✅ | ✅ |
| s6_goal | development | ❌ | ✅ | ✅ | ❌ | ✅ |
| s7_diet_change | development | ❌ | ✅ | ✅ | ✅ | ✅ |
| s8_meetings | development | ❌ | ✅ | ✅ | ❌ | ✅ |
| h1_gluten | held-out | ✅ | ✅ | ✅ | ✅ | ✅ |
| h2_mobile | held-out | ❌ | ✅ | ✅ | ✅ | ✅ |
| h3_time_limit | held-out | ❌ | ✅ | ✅ | ✅ | ✅ |
| h4_car_timeline | held-out | ❌ | ✅ | ✅ | ❌ | ✅ |
| h5_team_lunch | held-out | ❌ | ✅ | ✅ | ✅ | ✅ |
| h6_no_boats | held-out | ✅ | ✅ | ✅ | ✅ | ✅ |
