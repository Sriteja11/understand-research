import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.app.db.database import init_db
from backend.app.services.indexing_service import get_indexing_service
from backend.app.services.evaluation_service import get_evaluation_service

async def main():
    print("Initializing database and ensuring seed papers are indexed...")
    init_db()
    idx_service = get_indexing_service()
    idx_service.index_seed_documents()

    print("Starting evaluation run...")
    eval_service = get_evaluation_service()
    summary = await eval_service.run_evaluation()

    print("\n" + "=" * 60)
    print(f"EVALUATION REPORT (Run ID: {summary.run_id})")
    print("=" * 60)
    print(f"Total Test Questions:     {summary.total_questions}")
    print(f"Retrieval Hit Rate:       {summary.retrieval_hit_rate * 100:.1f}%")
    print(f"Citation Accuracy:        {summary.citation_accuracy * 100:.1f}%")
    print(f"Answer Groundedness:      {summary.groundedness_rate * 100:.1f}%")
    print(f"Refusal Accuracy:         {summary.refusal_accuracy * 100:.1f}%")
    print(f"Average Response Latency: {summary.avg_latency_ms:.1f} ms")
    print("=" * 60)

    print("\nDetailed Question Results:")
    for r in summary.results:
        hit_mark = "PASS" if r.retrieval_hit else "FAIL"
        cite_mark = "PASS" if r.citation_correct else "FAIL"
        ground_mark = "PASS" if r.grounded else "FAIL"
        refusal_mark = "PASS" if r.refusal_correct else "FAIL"
        print(f"[{r.question_id}] ({r.question_type:<15}) Hit:{hit_mark} | Cite:{cite_mark} | Ground:{ground_mark} | Refusal:{refusal_mark} | {r.latency_ms:.0f}ms")
        print(f"  Q: {r.question_text[:75]}")
        print(f"  A: {r.answer_preview[:90]}...")
        print()

    print(f"Report exported to evaluation/results/eval_{summary.run_id}.json and eval_latest.csv")

if __name__ == "__main__":
    asyncio.run(main())

