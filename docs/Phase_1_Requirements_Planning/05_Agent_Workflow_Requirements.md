# 5. Agent design

**Status:** Draft for approval  
**Date:** 2026-11-07  
**Source:** Phase 1 Requirements & Planning v1.0

| Component | Responsibility |
| --- | --- |
| Orchestrator | Interpret request, plan, select tools, track state. |
| News retrieval | Fetch relevant financial articles and metadata. |
| Market data | Fetch historical prices and volume. |
| Evidence verification | Deduplicate, corroborate and check dates/source quality. |
| Sentiment analysis | Assess current news and possible future scenarios. |
| Report generation | Compile cited findings and limitations. |

Architecture principle: one orchestrating agent with specialized tools initially; avoid unnecessary multi-agent complexity.

