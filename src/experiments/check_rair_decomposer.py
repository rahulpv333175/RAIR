"""Phase 7A live RAIR decomposer check using Ollama."""

import json
import sys
from datetime import datetime, timezone
from typing import Any

from src.llm.ollama_client import (
    OllamaClient,
    OllamaError,
)
from src.rair.decomposer import (
    DecompositionError,
    RAIRDecomposer,
)
from src.rair.state import RAIRState
from src.settings import (
    PROJECT_ROOT,
    load_settings,
)


QUESTIONS = (
    (
        "toy-1",
        (
            "In which city was the author of "
            "The Glass Orchard born?"
        ),
    ),
    (
        "toy-2",
        (
            "What is the capital of the country "
            "where the inventor of the Silver "
            "Compass was born?"
        ),
    ),
    (
        "toy-3",
        (
            "Which university was founded earlier: "
            "the university attended by the author "
            "of The Amber River, or the university "
            "attended by the author of "
            "The Silent Peak?"
        ),
    ),
)


def main() -> int:
    report_path = (
        PROJECT_ROOT
        / "results"
        / "phase7a_decomposer_check.json"
    )

    report: dict[str, Any] = {
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "passed": False,
        "examples": [],
    }

    try:
        settings = load_settings()

        client = OllamaClient(
            settings
        )

        ready = client.check_ready()

        print(
            "[OK] Ollama server: "
            f"{ready['server'].get('version', 'unknown')}"
        )

        print(
            "[OK] Model: "
            f"{client.model}"
        )

        decomposer = RAIRDecomposer(
            client
        )

        max_rounds = int(
            settings["rair"]["max_rounds"]
        )

        for question_id, question in QUESTIONS:
            print(
                f"\n[RUN] {question_id}"
            )

            print(
                f"Question: {question}"
            )

            state = RAIRState(
                question_id=question_id,
                question=question,
                max_rounds=max_rounds,
            )

            gaps = decomposer.decompose(
                state
            )

            if not gaps:
                raise ValueError(
                    "Decomposer returned no gaps."
                )

            actionable = (
                state.actionable_gaps()
            )

            if not actionable:
                raise ValueError(
                    "Decomposition has no "
                    "initially actionable gap."
                )

            print(
                f"[OK] Generated {len(gaps)} gaps"
            )

            for gap in gaps:
                dependencies = (
                    ", ".join(
                        gap.depends_on
                    )
                    if gap.depends_on
                    else "<none>"
                )

                print(
                    f"  {gap.gap_id} "
                    f"[{gap.priority}]"
                )

                print(
                    f"     need: {gap.description}"
                )

                print(
                    "     depends_on: "
                    f"{dependencies}"
                )

            actionable_ids = [
                gap.gap_id
                for gap in actionable
            ]

            print(
                "[OK] Initially actionable: "
                + ", ".join(
                    actionable_ids
                )
            )

            report["examples"].append(
                {
                    "question_id": question_id,
                    "question": question,
                    "gaps": [
                        {
                            "gap_id":
                                gap.gap_id,
                            "description":
                                gap.description,
                            "priority":
                                gap.priority,
                            "depends_on":
                                list(
                                    gap.depends_on
                                ),
                        }
                        for gap in gaps
                    ],
                    "initially_actionable":
                        actionable_ids,
                }
            )

        report["passed"] = True

    except (
        OllamaError,
        DecompositionError,
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
        print("PHASE 7A PASSED")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())