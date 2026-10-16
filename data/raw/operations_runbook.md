# RAGOps Operations and Quality Gates Runbook

## Deployment & Promotion Gates
1. **Quality Gates Philosophy**:
   - No RAG pipeline version candidate is deployed to production without clearing automated quality gates.
   - Quality metrics are evaluated against a golden benchmark dataset.

2. **Threshold Criteria**:
   - Minimum Retrieval Recall@5: 0.85
   - Minimum Answer Faithfulness: 0.90
   - Minimum Answer Relevance: 0.85
   - Maximum P95 Latency: 3000 milliseconds
   - Maximum Cost per 1,000 queries: $5.00

3. **Promotion Workflow**:
   - Execute benchmark evaluation: `ragops evaluate --dataset evaluation/datasets/golden.jsonl --version v2`.
   - Candidate evaluation results are compared against current active production baseline metrics.
   - If regressions in faithfulness or recall exceed 5%, automatic promotion is blocked.
   - Promotion manager records successful promotions in `promotion.json` with rollback capabilities.

4. **Monitoring & Incident Response**:
   - Prometheus scrapes application metrics at `/metrics`.
   - Tracing spans collect granular step latencies: query transformation, vector search, rerank, and LLM inference.
   - In case of provider degradation or high error rates, fallback mechanisms allow switching LLM models dynamically.
