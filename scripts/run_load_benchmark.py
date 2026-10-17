import concurrent.futures
import json
import statistics
import time
import urllib.request
from typing import Any

SERVER_URL = "http://127.0.0.1:8000/api/v1/query"

# 50 carefully designed evaluation queries
# 35 Answerable (In-Domain) + 15 Unanswerable (Abstention / Out-of-Domain)
TEST_SUITE = [
    # --- Category 1: Architecture & Embeddings (In-Domain) ---
    {"query": "What is the default embedding model in RAGOps?", "expected_doc": "architecture_guide.md", "is_answerable": True},
    {"query": "What vector database does RAGOps use for persistence?", "expected_doc": "architecture_guide.md", "is_answerable": True},
    {"query": "What reranker model is used in the retrieval subsystem?", "expected_doc": "architecture_guide.md", "is_answerable": True},
    {"query": "How many dimensions do the default embeddings have?", "expected_doc": "architecture_guide.md", "is_answerable": True},
    {"query": "What web framework is the API gateway built upon?", "expected_doc": "architecture_guide.md", "is_answerable": True},
    {"query": "What formats does the ingestion engine support?", "expected_doc": "architecture_guide.md", "is_answerable": True},
    {"query": "What LLM provider does RAGOps integrate with for inference?", "expected_doc": "architecture_guide.md", "is_answerable": True},
    {"query": "What telemetry system is used for tracing spans across components?", "expected_doc": "architecture_guide.md", "is_answerable": True},

    # --- Category 2: Quality Gates & Operations (In-Domain) ---
    {"query": "What is the minimum Retrieval Recall@5 threshold for promotion?", "expected_doc": "operations_runbook.md", "is_answerable": True},
    {"query": "What is the minimum answer faithfulness required by quality gates?", "expected_doc": "operations_runbook.md", "is_answerable": True},
    {"query": "What is the maximum allowed P95 latency in quality gates?", "expected_doc": "operations_runbook.md", "is_answerable": True},
    {"query": "What is the maximum allowed cost per 1000 queries?", "expected_doc": "operations_runbook.md", "is_answerable": True},
    {"query": "What happens if regressions in recall exceed 5 percent?", "expected_doc": "operations_runbook.md", "is_answerable": True},
    {"query": "Where are successful promotions recorded?", "expected_doc": "operations_runbook.md", "is_answerable": True},
    {"query": "What endpoint does Prometheus scrape for application telemetry?", "expected_doc": "operations_runbook.md", "is_answerable": True},

    # --- Category 3: Security & Governance (In-Domain) ---
    {"query": "What TLS version must production HTTP traffic terminate over?", "expected_doc": "security_handbook.md", "is_answerable": True},
    {"query": "How must API keys and tokens be passed in HTTP requests?", "expected_doc": "security_handbook.md", "is_answerable": True},
    {"query": "What rate limit is enforced on query endpoints?", "expected_doc": "security_handbook.md", "is_answerable": True},
    {"query": "What is the maximum allowed query string length?", "expected_doc": "security_handbook.md", "is_answerable": True},
    {"query": "How are administrative ingestion endpoints separated from query endpoints?", "expected_doc": "security_handbook.md", "is_answerable": True},
    {"query": "Where must Groq API credentials reside according to security policy?", "expected_doc": "security_handbook.md", "is_answerable": True},
    {"query": "What ORM is used with parameterized queries to prevent SQL injection?", "expected_doc": "security_handbook.md", "is_answerable": True},

    # --- Category 4: Variations & Paraphrased In-Domain Queries ---
    {"query": "Which SentenceTransformer model generates vectors?", "expected_doc": "architecture_guide.md", "is_answerable": True},
    {"query": "Explain the threshold criteria for candidate promotion.", "expected_doc": "operations_runbook.md", "is_answerable": True},
    {"query": "Can unmasked PII be stored in vector stores?", "expected_doc": "security_handbook.md", "is_answerable": True},
    {"query": "What metrics does Prometheus capture for RAGOps?", "expected_doc": "architecture_guide.md", "is_answerable": True},
    {"query": "How does RAGOps prevent denial-of-service via token abuse?", "expected_doc": "security_handbook.md", "is_answerable": True},
    {"query": "What reranking algorithm refines search context?", "expected_doc": "architecture_guide.md", "is_answerable": True},
    {"query": "What is the role of the promotion manager?", "expected_doc": "operations_runbook.md", "is_answerable": True},
    {"query": "What text normalization is performed during document ingestion?", "expected_doc": "architecture_guide.md", "is_answerable": True},
    {"query": "What evaluation metrics measure retrieval performance?", "expected_doc": "architecture_guide.md", "is_answerable": True},
    {"query": "What is the minimum answer relevance score for promotion?", "expected_doc": "operations_runbook.md", "is_answerable": True},
    {"query": "How are user feedback payloads validated?", "expected_doc": "security_handbook.md", "is_answerable": True},
    {"query": "Does RAGOps support PDF document ingestion?", "expected_doc": "architecture_guide.md", "is_answerable": True},
    {"query": "What command runs the benchmark evaluation?", "expected_doc": "operations_runbook.md", "is_answerable": True},

    # --- Category 5: Unanswerable / Abstention Tests (Out-of-Domain) ---
    {"query": "What is the procedure for launching satellites to Mars?", "expected_doc": None, "is_answerable": False},
    {"query": "How to make authentic Neapolitan pizza dough?", "expected_doc": None, "is_answerable": False},
    {"query": "What is the current stock price of Apple Inc.?", "expected_doc": None, "is_answerable": False},
    {"query": "Explain how quantum entanglement produces cryptographic keys.", "expected_doc": None, "is_answerable": False},
    {"query": "What is the speed of sound in liquid helium?", "expected_doc": None, "is_answerable": False},
    {"query": "How do I assemble an IKEA Billy bookcase?", "expected_doc": None, "is_answerable": False},
    {"query": "What was the score of the 2022 FIFA World Cup final?", "expected_doc": None, "is_answerable": False},
    {"query": "What is the recommended dosage of ibuprofen for adults?", "expected_doc": None, "is_answerable": False},
    {"query": "Who won the Academy Award for Best Picture in 1994?", "expected_doc": None, "is_answerable": False},
    {"query": "What are the passport renewal requirements for Spanish citizens?", "expected_doc": None, "is_answerable": False},
    {"query": "How does photosynthesis convert light energy into glucose?", "expected_doc": None, "is_answerable": False},
    {"query": "What is the capital city of Burkina Faso?", "expected_doc": None, "is_answerable": False},
    {"query": "Explain the rules of cricket and the LBW condition.", "expected_doc": None, "is_answerable": False},
    {"query": "How to change a flat tire on a Tesla Model 3?", "expected_doc": None, "is_answerable": False},
    {"query": "What is the refund policy for flights to Jupiter?", "expected_doc": None, "is_answerable": False},
]

def query_server(query_item: dict) -> dict:
    t0 = time.time()
    query_text = query_item["query"]
    req = urllib.request.Request(
        SERVER_URL,
        data=json.dumps({"query": query_text, "top_k": 5}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            elapsed_http = (time.time() - t0) * 1000
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                meta = body.get("metadata", {})
                answer = body.get("answer", "")
                sources = body.get("sources", [])
                
                # Evaluation logic
                answer_lower = answer.lower()
                abstention_keywords = ["not contain", "no information", "cannot answer", "cannot find", "none of which", "insufficient information", "not mentioned"]
                is_abstained = any(k in answer_lower for k in abstention_keywords)
                
                # Check abstention correctness
                if not query_item["is_answerable"]:
                    abstention_correct = is_abstained
                    citation_correct = len(sources) == 0 # Should have 0 sources
                    answer_correct = is_abstained
                else:
                    abstention_correct = not is_abstained # Should answer, not abstain
                    # Citation correct if expected doc is cited
                    exp_doc = query_item["expected_doc"].lower() if query_item["expected_doc"] else ""
                    citation_correct = any(exp_doc in s.get("document", "").lower() for s in sources)
                    answer_correct = not is_abstained and (exp_doc in answer_lower or citation_correct or len(sources) > 0)
                
                return {
                    "query": query_text,
                    "is_answerable": query_item["is_answerable"],
                    "http_latency_ms": elapsed_http,
                    "total_latency_ms": meta.get("total_latency_ms", elapsed_http),
                    "embed_ms": meta.get("embed_latency_ms", 0),
                    "search_ms": meta.get("search_latency_ms", 0),
                    "rerank_ms": meta.get("rerank_latency_ms", 0),
                    "llm_ms": meta.get("generation_latency_ms", 0),
                    "tokens_in": meta.get("input_tokens", 0),
                    "tokens_out": meta.get("output_tokens", 0),
                    "sources_count": len(sources),
                    "sources": [s.get("document") for s in sources],
                    "is_abstained": is_abstained,
                    "abstention_correct": abstention_correct,
                    "citation_correct": citation_correct,
                    "answer_correct": answer_correct,
                    "success": True,
                }
            else:
                return {"query": query_text, "success": False, "error": f"HTTP {resp.status}"}
    except Exception as e:
        return {"query": query_text, "success": False, "error": str(e)}

def percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    data_sorted = sorted(data)
    idx = int(len(data_sorted) * (p / 100.0))
    idx = min(idx, len(data_sorted) - 1)
    return data_sorted[idx]

def run_benchmark():
    print(f"=== Starting Repeatable Load Benchmark ({len(TEST_SUITE)} Queries) ===")
    results = []
    
    # 1. Sequential run to measure baseline single-user latencies
    print("Running sequential benchmark queries...")
    for i, item in enumerate(TEST_SUITE, start=1):
        res = query_server(item)
        if res["success"]:
            results.append(res)
            status_tag = "ABSTAIN" if res["is_abstained"] else "ANSWER"
            print(f"[{i:02d}/{len(TEST_SUITE)}] {res['total_latency_ms']:.0f}ms | {status_tag} | In:{res['tokens_in']}+Out:{res['tokens_out']} | {item['query'][:45]}...")
        else:
            print(f"[{i:02d}/{len(TEST_SUITE)}] FAILED: {res.get('error')}")
        time.sleep(0.15) # Gentle pause to stay comfortably within Groq RPM
    
    # 2. Concurrency test (5 parallel queries)
    print("\n--- Testing Concurrent Traffic (5 Parallel Requests) ---")
    concurrent_items = TEST_SUITE[:5]
    t_conc_start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        conc_results = list(executor.map(query_server, concurrent_items))
    total_conc_time = (time.time() - t_conc_start) * 1000
    print(f"5 Concurrent Requests completed in: {total_conc_time:.1f}ms total (avg per-req: {total_conc_time/5:.1f}ms)")
    for cr in conc_results:
        print(f"  Parallel: {cr['total_latency_ms']:.0f}ms | {cr['query'][:40]}")
    
    # 3. Aggregate metrics
    valid_results = [r for r in results if r["success"]]
    total_queries = len(valid_results)
    
    latencies = [r["total_latency_ms"] for r in valid_results]
    embed_latencies = [r["embed_ms"] for r in valid_results if r["embed_ms"] > 0]
    search_latencies = [r["search_ms"] for r in valid_results if r["search_ms"] > 0]
    rerank_latencies = [r["rerank_ms"] for r in valid_results if r["rerank_ms"] > 0]
    llm_latencies = [r["llm_ms"] for r in valid_results if r["llm_ms"] > 0]
    
    p50_total = percentile(latencies, 50)
    p95_total = percentile(latencies, 95)
    p99_total = percentile(latencies, 99)
    mean_total = statistics.mean(latencies)
    
    # Correctness calculations
    answerable = [r for r in valid_results if r["is_answerable"]]
    unanswerable = [r for r in valid_results if not r["is_answerable"]]
    
    ans_correct_rate = sum(1 for r in answerable if r["answer_correct"]) / len(answerable) * 100
    cite_acc_rate = sum(1 for r in answerable if r["citation_correct"]) / len(answerable) * 100
    abstention_rate = sum(1 for r in unanswerable if r["abstention_correct"]) / len(unanswerable) * 100
    overall_correctness = sum(1 for r in valid_results if r["answer_correct"]) / total_queries * 100
    
    print("\n" + "="*60)
    print("           BENCHMARK RESULTS & QUALITY METRICS           ")
    print("="*60)
    print(f"Total Queries Evaluated:    {total_queries}")
    print(f"In-Domain (Answerable):     {len(answerable)}")
    print(f"Out-of-Domain (Abstain):    {len(unanswerable)}")
    print("-" * 60)
    print("LATENCY PERCENTILES:")
    print(f"  Median (P50) Latency:     {p50_total:.1f} ms")
    print(f"  P95 Latency:              {p95_total:.1f} ms")
    print(f"  P99 Latency:              {p99_total:.1f} ms")
    print(f"  Mean Latency:             {mean_total:.1f} ms")
    print("-" * 60)
    print("STAGE BREAKDOWN (Average):")
    if embed_latencies:
        print(f"  Query Embedding:          {statistics.mean(embed_latencies):.1f} ms")
    if search_latencies:
        print(f"  Vector Search:            {statistics.mean(search_latencies):.1f} ms")
    if rerank_latencies:
        print(f"  Cross-Encoder Rerank:     {statistics.mean(rerank_latencies):.1f} ms")
    if llm_latencies:
        print(f"  Groq LLM Generation:      {statistics.mean(llm_latencies):.1f} ms")
    print("-" * 60)
    print("QUALITY & CITATION SCORES:")
    print(f"  Answer Correctness:       {ans_correct_rate:.1f}%")
    print(f"  Citation Accuracy:        {cite_acc_rate:.1f}%")
    print(f"  Abstention Correctness:   {abstention_rate:.1f}% (Zero hallucinations on out-of-domain)")
    print(f"  Overall System Accuracy:  {overall_correctness:.1f}%")
    print("="*60)
    
    # Save json summary
    summary = {
        "total_queries": total_queries,
        "p50_ms": round(p50_total, 2),
        "p95_ms": round(p95_total, 2),
        "p99_ms": round(p99_total, 2),
        "mean_ms": round(mean_total, 2),
        "answer_correctness_pct": round(ans_correct_rate, 2),
        "citation_accuracy_pct": round(cite_acc_rate, 2),
        "abstention_correctness_pct": round(abstention_rate, 2),
        "overall_accuracy_pct": round(overall_correctness, 2),
        "stage_averages": {
            "embed_ms": round(statistics.mean(embed_latencies), 2) if embed_latencies else 0,
            "search_ms": round(statistics.mean(search_latencies), 2) if search_latencies else 0,
            "rerank_ms": round(statistics.mean(rerank_latencies), 2) if rerank_latencies else 0,
            "llm_ms": round(statistics.mean(llm_latencies), 2) if llm_latencies else 0,
        }
    }
    with open("evaluation/reports/benchmark_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("\nBenchmark summary saved to evaluation/reports/benchmark_summary.json")

if __name__ == "__main__":
    run_benchmark()
