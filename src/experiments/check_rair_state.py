"""Phase 6 deterministic RAIR state transition check.

No Ollama or BM25 calls are made here.
We manually simulate a two-hop RAIR state transition.
"""

import json
import sys
from datetime import datetime, timezone

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


def show_actionable(state: RAIRState) -> str:
    """Return actionable gap IDs for readable diagnostic output."""
    gaps = state.actionable_gaps()

    if not gaps:
        return "<none>"

    return ", ".join(
        gap.gap_id
        for gap in gaps
    )


def main() -> int:
    report_path = (
        PROJECT_ROOT
        / "results"
        / "phase6_rair_state_check.json"
    )

    report = {
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "passed": False,
    }

    try:
        settings = load_settings()

        max_rounds = int(
            settings["rair"]["max_rounds"]
        )

        state = RAIRState(
            question_id="toy-rair-1",
            question=(
                "In which city was the author of "
                "The Glass Orchard born?"
            ),
            max_rounds=max_rounds,
        )

        print(
            f"[OK] Created RAIR state "
            f"with max_rounds={max_rounds}"
        )

        # -------------------------------------------------
        # DECOMPOSITION
        # -------------------------------------------------

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
                    "Identify the city where "
                    "the author was born."
                ),
                priority="high",
                depends_on=("G1",),
            )
        )

        print(
            "[OK] Added 2 dependent gaps"
        )

        if show_actionable(state) != "G1":
            raise ValueError(
                "Expected only G1 to be "
                "actionable initially."
            )

        print(
            "[OK] Initially actionable: "
            f"{show_actionable(state)}"
        )

        # -------------------------------------------------
        # ROUND 1
        # -------------------------------------------------

        round_number = state.start_next_round()

        print(
            f"\n[ROUND {round_number}] "
            "Resolving G1"
        )

        state.record_query(
            QueryAttempt(
                round_number=round_number,
                gap_id="G1",
                query="The Glass Orchard author",
                retrieved_document_ids=(
                    "toy-rair-1:D1",
                ),
                success=True,
            )
        )

        evidence_1 = Evidence(
            document_id="toy-rair-1:D1",
            title="The Glass Orchard",
            sentence_indices=(0,),
            text=(
                "The Glass Orchard was "
                "written by Mira Solen."
            ),
        )

        fact_1 = VerifiedFact(
            fact_id="F1",
            statement=(
                "The author of The Glass "
                "Orchard is Mira Solen."
            ),
            gap_id="G1",
            evidence=(evidence_1,),
        )

        state.add_verified_fact(
            fact_1
        )

        state.resolve_gap(
            "G1"
        )

        print(
            "[OK] Added verified fact F1"
        )

        print(
            "[OK] Resolved G1"
        )

        if show_actionable(state) != "G2":
            raise ValueError(
                "Expected G2 to become "
                "actionable after G1."
            )

        print(
            "[OK] Now actionable: "
            f"{show_actionable(state)}"
        )

        # -------------------------------------------------
        # ROUND 2
        # -------------------------------------------------

        round_number = state.start_next_round()

        print(
            f"\n[ROUND {round_number}] "
            "Resolving G2"
        )

        state.record_query(
            QueryAttempt(
                round_number=round_number,
                gap_id="G2",
                query="Mira Solen birthplace city",
                retrieved_document_ids=(
                    "toy-rair-1:D2",
                ),
                success=True,
            )
        )

        evidence_2 = Evidence(
            document_id="toy-rair-1:D2",
            title="Mira Solen",
            sentence_indices=(0,),
            text=(
                "Mira Solen was born "
                "in Nerava."
            ),
        )

        fact_2 = VerifiedFact(
            fact_id="F2",
            statement=(
                "Mira Solen was born "
                "in Nerava."
            ),
            gap_id="G2",
            evidence=(evidence_2,),
        )

        state.add_verified_fact(
            fact_2
        )

        state.resolve_gap(
            "G2"
        )

        print(
            "[OK] Added verified fact F2"
        )

        print(
            "[OK] Resolved G2"
        )

        # -------------------------------------------------
        # FINAL STATE VALIDATION
        # -------------------------------------------------

        if not state.is_complete():
            raise ValueError(
                "State should be complete "
                "after both gaps are resolved."
            )

        if state.unresolved_gaps():
            raise ValueError(
                "Completed state still contains "
                "unresolved gaps."
            )

        if state.actionable_gaps():
            raise ValueError(
                "Completed state should not "
                "contain actionable gaps."
            )

        if len(state.verified_facts) != 2:
            raise ValueError(
                "Expected exactly two "
                "verified facts."
            )

        if len(state.query_history) != 2:
            raise ValueError(
                "Expected exactly two "
                "query attempts."
            )

        print(
            "\n[OK] All gaps resolved"
        )

        print(
            "[OK] Verified facts: "
            f"{len(state.verified_facts)}"
        )

        print(
            "[OK] Query attempts: "
            f"{len(state.query_history)}"
        )

        print(
            "[OK] Failed attempts: "
            f"{len(state.failed_attempts())}"
        )

        print(
            "[OK] RAIR state is complete"
        )

        # Save complete state for inspection.
        report.update(
            {
                "passed": True,
                "simulation": (
                    "deterministic_two_hop"
                ),
                "llm_used": False,
                "retriever_used": False,
                "state": state.to_dict(),
            }
        )

    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
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
        print("PHASE 6 PASSED")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())