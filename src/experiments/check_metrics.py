"""Phase 5 evaluation-metric sanity checks.

This script does not run RAIR, KAIR, retrieval, or Ollama.
Gold labels are used only to verify the evaluation functions.
"""

import json
import sys
from datetime import datetime, timezone
from typing import Any

from src.datasets.hotpotqa import load_hotpotqa
from src.evaluation.metrics import (
    answer_f1,
    exact_match,
    normalize_answer,
    retrieval_metrics,
)
from src.settings import PROJECT_ROOT, load_settings


def main() -> int:
    report_path = (
        PROJECT_ROOT
        / "results"
        / "phase5_metrics_check.json"
    )

    report: dict[str, Any] = {
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "passed": False,
    }

    try:
        settings = load_settings()

        dataset_path = (
            PROJECT_ROOT
            / settings["dataset"]["path"]
        )

        print(
            f"[RUN] Loading {dataset_path}",
            flush=True,
        )

        examples = load_hotpotqa(
            dataset_path
        )

        if len(examples) < 3:
            raise ValueError(
                "Need at least three HotpotQA examples."
            )

        print(
            f"[OK] Loaded {len(examples)} "
            "HotpotQA questions"
        )

        rows = []

        # Evaluation sanity check only:
        # feed each gold answer back into the evaluator.
        for example in examples[:3]:
            gold = example.gold.answer

            perfect_em = exact_match(
                gold,
                gold,
            )

            perfect_f1 = answer_f1(
                gold,
                gold,
            )

            if perfect_em != 1.0:
                raise ValueError(
                    "Gold answer failed "
                    "exact-match self-check."
                )

            if perfect_f1 != 1.0:
                raise ValueError(
                    "Gold answer failed "
                    "F1 self-check."
                )

            rows.append(
                {
                    "question_id":
                        example.task.question_id,
                    "question":
                        example.task.question,
                    "gold_answer":
                        gold,
                    "normalized_gold":
                        normalize_answer(gold),
                    "self_exact_match":
                        perfect_em,
                    "self_answer_f1":
                        perfect_f1,
                }
            )

        print(
            "[OK] Gold answer self-check: "
            "EM=1.0, F1=1.0"
        )

        # Deliberately incorrect answer.
        wrong_prediction = (
            "__definitely_wrong__"
        )

        wrong_gold = (
            examples[0].gold.answer
        )

        wrong_em = exact_match(
            wrong_prediction,
            wrong_gold,
        )

        wrong_f1 = answer_f1(
            wrong_prediction,
            wrong_gold,
        )

        if (
            wrong_em != 0.0
            or wrong_f1 != 0.0
        ):
            raise ValueError(
                "Deliberately wrong answer "
                "received evaluation credit."
            )

        print(
            "[OK] Deliberately wrong answer: "
            "EM=0.0, F1=0.0"
        )

        # Synthetic retrieval evaluation:
        #
        # Gold:      D1, D2
        # Retrieved: D1, D2, X
        #
        # TP = 2
        # precision = 2/3
        # recall = 2/2 = 1
        # F1 = 0.8
        retrieval = retrieval_metrics(
            ["D1", "D2", "X"],
            ["D1", "D2"],
        )

        expected_precision = 2 / 3
        expected_recall = 1.0
        expected_f1 = 0.8

        if abs(
            retrieval.precision
            - expected_precision
        ) > 1e-12:
            raise ValueError(
                "Retrieval precision "
                "sanity check failed."
            )

        if abs(
            retrieval.recall
            - expected_recall
        ) > 1e-12:
            raise ValueError(
                "Retrieval recall "
                "sanity check failed."
            )

        if abs(
            retrieval.f1
            - expected_f1
        ) > 1e-12:
            raise ValueError(
                "Retrieval F1 "
                "sanity check failed."
            )

        print(
            "[OK] Retrieval metric sanity check: "
            f"P={retrieval.precision:.3f}, "
            f"R={retrieval.recall:.3f}, "
            f"F1={retrieval.f1:.3f}"
        )

        print(
            "\n--- FIRST 3 GOLD ANSWERS ---"
        )

        for row in rows:
            print(
                f"{row['question_id']}: "
                f"{row['gold_answer']!r} "
                f"-> "
                f"{row['normalized_gold']!r}"
            )

        report.update(
            {
                "passed": True,
                "num_dataset_examples":
                    len(examples),
                "examples": rows,
                "synthetic_retrieval_check": {
                    "retrieved": [
                        "D1",
                        "D2",
                        "X",
                    ],
                    "gold": [
                        "D1",
                        "D2",
                    ],
                    "precision":
                        retrieval.precision,
                    "recall":
                        retrieval.recall,
                    "f1":
                        retrieval.f1,
                },
                "wrong_answer_check": {
                    "prediction":
                        wrong_prediction,
                    "exact_match":
                        wrong_em,
                    "answer_f1":
                        wrong_f1,
                },
                "notes": [
                    (
                        "Gold answers are used "
                        "only by evaluation."
                    ),
                    (
                        "Document retrieval metrics "
                        "are set-based."
                    ),
                    (
                        "Sentence-level supporting-fact "
                        "evaluation will remain "
                        "separate from document-level "
                        "retrieval evaluation."
                    ),
                ],
            }
        )

    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
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
            "[FAIL] Could not save report: "
            f"{exc}",
            file=sys.stderr,
        )
        return 1

    print(
        f"\n[SAVED] {report_path}"
    )

    if report["passed"]:
        print("PHASE 5 PASSED")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())