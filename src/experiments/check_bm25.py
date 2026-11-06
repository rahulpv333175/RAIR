"""Phase 4 BM25 diagnostic on HotpotQA.

Gold supporting facts are consulted only after retrieval for evaluation.
They never influence queries, indexing, ranking, or document selection.
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from src.datasets.hotpotqa import load_hotpotqa
from src.retrieval.bm25 import BM25Retriever
from src.retrieval.document_store import DocumentStore
from src.settings import PROJECT_ROOT, load_settings


def gold_support_titles(example: Any) -> set[str]:
    """Evaluation-only view of supporting-document titles."""
    return {
        title
        for title, _sentence_id in example.gold.supporting_facts
    }


def evaluate_example(
    example: Any,
    *,
    top_k: int,
) -> dict[str, Any]:
    task = example.task

    store = DocumentStore(
        task.question_id,
        task.documents,
    )

    retriever = BM25Retriever(store)

    # Retrieval uses ONLY the question and document pool.
    # No gold answer or supporting-fact information is used here.
    results = retriever.search(
        task.question,
        top_k=top_k,
    )

    retrieved_titles = [
        result.document.title
        for result in results
    ]

    # Gold information enters only AFTER retrieval has completed.
    gold_titles = gold_support_titles(example)

    retrieved_gold_titles = gold_titles.intersection(
        retrieved_titles
    )

    return {
        "question_id": task.question_id,
        "question": task.question,
        "pool_size": len(task.documents),
        "query": task.question,
        "retrieved": [
            {
                "rank": result.rank,
                "document_id": result.document.document_id,
                "title": result.document.title,
                "score": result.score,
            }
            for result in results
        ],
        "gold_support_titles": sorted(gold_titles),
        "retrieved_gold_titles": sorted(retrieved_gold_titles),
        "gold_document_recall": (
            len(retrieved_gold_titles) / len(gold_titles)
            if gold_titles
            else None
        ),
        "all_gold_documents_retrieved": (
            gold_titles.issubset(set(retrieved_titles))
            if gold_titles
            else None
        ),
    }


def main() -> int:
    report_path = (
        PROJECT_ROOT
        / "results"
        / "phase4_bm25_check.json"
    )

    report: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": False,
    }

    try:
        settings = load_settings()

        dataset_path = (
            PROJECT_ROOT
            / settings["dataset"]["path"]
        )

        top_k = int(settings["retrieval"]["top_k"])

        if settings["retrieval"]["method"] != "bm25":
            raise ValueError(
                "retrieval.method must be bm25."
            )

        if settings["retrieval"]["corpus_scope"] != "per_question":
            raise ValueError(
                "retrieval.corpus_scope must be per_question."
            )

        print(
            f"[RUN] Loading {dataset_path}",
            flush=True,
        )

        examples = load_hotpotqa(dataset_path)

        print(
            f"[OK] Loaded {len(examples)} questions"
        )

        # First 20 records are used only as an implementation diagnostic.
        # This is NOT our eventual benchmark sample.
        diagnostic_examples = examples[:20]

        evaluations = [
            evaluate_example(
                example,
                top_k=top_k,
            )
            for example in diagnostic_examples
        ]

        recall_values = [
            row["gold_document_recall"]
            for row in evaluations
            if row["gold_document_recall"] is not None
        ]

        complete_count = sum(
            row["all_gold_documents_retrieved"] is True
            for row in evaluations
        )

        no_result_count = sum(
            len(row["retrieved"]) == 0
            for row in evaluations
        )

        pool_sizes = Counter(
            row["pool_size"]
            for row in evaluations
        )

        mean_recall = (
            sum(recall_values) / len(recall_values)
            if recall_values
            else 0.0
        )

        print(
            f"[INFO] BM25 top_k: {top_k}"
        )

        print(
            f"[INFO] Diagnostic questions: {len(evaluations)}"
        )

        print(
            "[INFO] Pool sizes (documents: questions): "
            f"{dict(sorted(pool_sizes.items()))}"
        )

        print(
            f"[INFO] Mean gold-document recall@{top_k}: "
            f"{mean_recall:.3f}"
        )

        print(
            "[INFO] Questions with every gold support "
            f"document retrieved: "
            f"{complete_count}/{len(evaluations)}"
        )

        print(
            "[INFO] Queries returning no positive-score "
            f"documents: "
            f"{no_result_count}/{len(evaluations)}"
        )

        print("\n--- FIRST 3 RETRIEVALS ---")

        for row in evaluations[:3]:
            print(
                f"\nQuestion ID: {row['question_id']}"
            )

            print(
                f"Question: {row['question']}"
            )

            if not row["retrieved"]:
                print("  <no BM25 results>")
            else:
                for result in row["retrieved"]:
                    print(
                        f"  #{result['rank']} "
                        f"{result['title']} "
                        f"(score={result['score']:.4f})"
                    )

            print(
                "  Gold support titles: "
                + (
                    ", ".join(row["gold_support_titles"])
                    or "<none>"
                )
            )

            print(
                "  Retrieved gold titles: "
                + (
                    ", ".join(row["retrieved_gold_titles"])
                    or "<none>"
                )
            )

        report.update(
            {
                "passed": True,
                "retrieval": {
                    "method": "bm25",
                    "top_k": top_k,
                    "corpus_scope": "per_question",
                    "k1": 1.5,
                    "b": 0.75,
                },
                "diagnostic_subset": {
                    "selection": "first_20_dataset_records",
                    "purpose": (
                        "Implementation diagnostic only; "
                        "not benchmark evaluation."
                    ),
                    "num_questions": len(evaluations),
                },
                "mean_gold_document_recall": mean_recall,
                "complete_gold_document_questions": complete_count,
                "no_positive_score_questions": no_result_count,
                "results": evaluations,
                "gold_usage": (
                    "Supporting facts used only after retrieval "
                    "for diagnostic evaluation."
                ),
            }
        )

    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
    ) as exc:
        report["error"] = str(exc)

        print(
            f"[FAIL] {exc}",
            file=sys.stderr,
        )

    try:
        report_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        report_path.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    except OSError as exc:
        print(
            f"[FAIL] Could not save report: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        f"\n[SAVED] {report_path}"
    )

    if report["passed"]:
        print("PHASE 4 PASSED")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())