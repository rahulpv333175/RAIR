"""Phase 7B live RAIR query-planner check."""

import json
import sys
from datetime import datetime, timezone
from typing import Any

from src.llm.ollama_client import (
    OllamaClient,
    OllamaError,
)
from src.rair.query_planner import (
    QueryPlanningError,
    RAIRQueryPlanner,
    select_next_gap,
)
from src.rair.state import (
    Evidence,
    Gap,
    QueryAttempt,
    RAIRState,
    VerifiedFact,
)
from src.settings import (
    PROJECT_ROOT,
    load_settings,
)


def make_state(
    max_rounds: int,
) -> RAIRState:
    state = RAIRState(
        question_id="toy-planner",
        question=(
            "In which city was the author of "
            "The Glass Orchard born?"
        ),
        max_rounds=max_rounds,
    )

    state.add_gap(
        Gap(
            gap_id="G1",
            description=(
                "Identify the author of "
                "The Glass Orchard."
            ),
            priority="high",
        )
    )

    state.add_gap(
        Gap(
            gap_id="G2",
            description=(
                "Identify the birth city of "
                "the author identified in G1."
            ),
            priority="high",
            depends_on=("G1",),
        )
    )

    return state


def add_author_fact(
    state: RAIRState,
) -> None:
    evidence = Evidence(
        document_id="toy-planner:D1",
        title="The Glass Orchard",
        sentence_indices=(0,),
        text=(
            "The Glass Orchard was written "
            "by Mira Solen."
        ),
    )

    state.add_verified_fact(
        VerifiedFact(
            fact_id="F1",
            statement=(
                "The author of The Glass "
                "Orchard is Mira Solen."
            ),
            gap_id="G1",
            evidence=(evidence,),
        )
    )

    state.resolve_gap(
        "G1"
    )


def main() -> int:
    report_path = (
        PROJECT_ROOT
        / "results"
        / "phase7b_query_planner_check.json"
    )

    report: dict[str, Any] = {
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "passed": False,
        "cases": [],
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
            f"[OK] Model: {client.model}"
        )

        planner = RAIRQueryPlanner(
            client
        )

        max_rounds = int(
            settings["rair"]["max_rounds"]
        )

        # -------------------------------------------
        # CASE 1
        # Initial gap: no verified knowledge yet.
        # -------------------------------------------

        print(
            "\n[CASE 1] Initial author gap"
        )

        state = make_state(
            max_rounds
        )

        gap = select_next_gap(
            state
        )

        query = planner.plan(
            state,
            gap,
        )

        print(
            f"[OK] Selected gap: {gap.gap_id}"
        )

        print(
            f"[OK] Planned query: {query}"
        )

        report["cases"].append(
            {
                "case":
                    "initial_gap",
                "gap_id":
                    gap.gap_id,
                "query":
                    query,
            }
        )

        # -------------------------------------------
        # CASE 2
        # G1 resolved. Query should now target
        # Mira Solen's birthplace.
        # -------------------------------------------

        print(
            "\n[CASE 2] Use verified bridge fact"
        )

        state = make_state(
            max_rounds
        )

        add_author_fact(
            state
        )

        gap = select_next_gap(
            state
        )

        query = planner.plan(
            state,
            gap,
        )

        if "mira" not in query.lower():
            raise ValueError(
                "Planner did not use the verified "
                "bridge entity Mira Solen."
            )

        print(
            f"[OK] Selected gap: {gap.gap_id}"
        )

        print(
            f"[OK] Planned query: {query}"
        )

        print(
            "[OK] Query uses verified bridge "
            "entity Mira Solen"
        )

        report["cases"].append(
            {
                "case":
                    "verified_bridge_fact",
                "gap_id":
                    gap.gap_id,
                "query":
                    query,
            }
        )

        # -------------------------------------------
        # CASE 3
        # Previous birthplace query failed.
        # Planner must produce a different query.
        # -------------------------------------------

        print(
            "\n[CASE 3] Reformulate failed query"
        )

        state = make_state(
            max_rounds
        )

        add_author_fact(
            state
        )

        state.record_query(
            QueryAttempt(
                round_number=1,
                gap_id="G2",
                query=(
                    "Mira Solen birthplace"
                ),
                retrieved_document_ids=(),
                success=False,
                failure_reason=(
                    "No positive-score documents."
                ),
            )
        )

        gap = select_next_gap(
            state
        )

        query = planner.plan(
            state,
            gap,
        )

        old_normalized = (
            RAIRQueryPlanner.normalize_query(
                "Mira Solen birthplace"
            )
        )

        new_normalized = (
            RAIRQueryPlanner.normalize_query(
                query
            )
        )

        if (
            new_normalized
            == old_normalized
        ):
            raise ValueError(
                "Planner repeated the failed query."
            )

        if "mira" not in query.lower():
            raise ValueError(
                "Reformulated query lost the "
                "verified bridge entity."
            )

        print(
            "[OK] Failed query: "
            "Mira Solen birthplace"
        )

        print(
            f"[OK] New query: {query}"
        )

        print(
            "[OK] Planner reformulated "
            "the failed query"
        )

        report["cases"].append(
            {
                "case":
                    "failed_query_reformulation",
                "previous_query":
                    "Mira Solen birthplace",
                "new_query":
                    query,
            }
        )

        report["passed"] = True

    except (
        OllamaError,
        QueryPlanningError,
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
        print(
            "PHASE 7B PASSED"
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())