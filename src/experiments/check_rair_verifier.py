"""Phase 7F live RAIR verifier integration check."""

import json
import sys
from datetime import datetime, timezone
from typing import Any

from src.llm.ollama_client import (
    OllamaClient,
    OllamaError,
)
from src.rair.evidence_filter import (
    EvidenceFilterError,
    RAIREvidenceFilter,
)
from src.rair.fact_extractor import (
    CandidateFact,
    FactExtractionError,
    RAIRFactExtractor,
)
from src.rair.query_planner import (
    QueryPlanningError,
    RAIRQueryPlanner,
)
from src.rair.retrieval_step import (
    RAIRRetrievalStep,
    RetrievalStepError,
)
from src.rair.state import (
    Evidence,
    Gap,
    RAIRState,
)
from src.rair.verifier import (
    RAIRVerifier,
    VerificationError,
)
from src.retrieval.document_store import (
    Document,
    DocumentStore,
)
from src.settings import (
    PROJECT_ROOT,
    load_settings,
)


def make_store() -> DocumentStore:
    documents = (
        Document(
            document_id="toy-verify:D1",
            question_id="toy-verify",
            title="The Glass Orchard",
            sentences=(
                (
                    "The Glass Orchard was "
                    "written by Mira Solen."
                ),
                (
                    "The novel was published "
                    "in 1998."
                ),
            ),
        ),
        Document(
            document_id="toy-verify:D2",
            question_id="toy-verify",
            title="Mira Solen",
            sentences=(
                (
                    "Mira Solen was born "
                    "in the city of Nerava."
                ),
            ),
        ),
        Document(
            document_id="toy-verify:D3",
            question_id="toy-verify",
            title="Orchards",
            sentences=(
                (
                    "An orchard is land "
                    "planted with fruit trees."
                ),
            ),
        ),
    )

    return DocumentStore(
        "toy-verify",
        documents,
    )


def make_state(
    max_rounds: int,
) -> RAIRState:
    state = RAIRState(
        question_id="toy-verify",
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


def decision_to_dict(
    decision: Any,
) -> dict[str, Any]:
    return {
        "candidate_id":
            decision.candidate_id,
        "supported_by_evidence":
            decision.supported_by_evidence,
        "relevant_to_gap":
            decision.relevant_to_gap,
        "answer_type_ok":
            decision.answer_type_ok,
        "contains_unresolved_placeholder":
            decision.contains_unresolved_placeholder,
        "resolves_gap":
            decision.resolves_gap,
        "reason":
            decision.reason,
        "accepted":
            decision.accepted,
    }


def main() -> int:
    report_path = (
        PROJECT_ROOT
        / "results"
        / "phase7f_verifier_check.json"
    )

    report: dict[str, Any] = {
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "passed": False,
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

        retrieval_step = RAIRRetrievalStep(
            planner,
            top_k=int(
                settings["retrieval"]["top_k"]
            ),
        )

        evidence_filter = RAIREvidenceFilter(
            client
        )

        fact_extractor = RAIRFactExtractor(
            client
        )

        verifier = RAIRVerifier(
            client
        )

        max_rounds = int(
            settings["rair"]["max_rounds"]
        )

        store = make_store()

        # ==================================================
        # CASE 1
        # Real pipeline: supported candidate should promote.
        # ==================================================

        print(
            "\n[CASE 1] Verify supported candidate"
        )

        state = make_state(
            max_rounds
        )

        retrieval = retrieval_step.run(
            state,
            store,
        )

        print(
            f"[OK] Query: {retrieval.query}"
        )

        evidence = evidence_filter.filter(
            state,
            retrieval.gap,
            retrieval,
        )

        if not evidence:
            raise ValueError(
                "Evidence Filter returned "
                "no evidence."
            )

        candidates = fact_extractor.extract(
            state,
            retrieval.gap,
            evidence,
        )

        if not candidates:
            raise ValueError(
                "Fact Extractor returned "
                "no candidates."
            )

        print(
            "[OK] Candidate facts:"
        )

        for candidate in candidates:
            print(
                f"  {candidate.candidate_id}: "
                f"{candidate.statement}"
            )

        decisions, promoted = (
            verifier.verify_and_commit(
                state,
                retrieval.gap,
                candidates,
            )
        )

        print(
            "[OK] Verification decisions:"
        )

        for decision in decisions:
            print(
                f"  {decision.candidate_id}: "
                f"accepted={decision.accepted}, "
                f"resolves_gap="
                f"{decision.resolves_gap}"
            )

            print(
                f"     reason: "
                f"{decision.reason}"
            )

        if not promoted:
            raise ValueError(
                "Verifier promoted no "
                "supported facts."
            )

        if not any(
            "mira solen"
            in fact.statement.lower()
            for fact in promoted
        ):
            raise ValueError(
                "Promoted facts do not "
                "identify Mira Solen."
            )

        if not state.get_gap(
            "G1"
        ).resolved:
            raise ValueError(
                "Supported author fact "
                "did not resolve G1."
            )

        actionable = [
            gap.gap_id
            for gap in state.actionable_gaps()
        ]

        if actionable != [
            "G2"
        ]:
            raise ValueError(
                "Expected G2 to become "
                "actionable after G1."
            )

        print(
            "[OK] Supported candidate entered "
            "verified shared knowledge"
        )

        print(
            "[OK] G1 resolved"
        )

        print(
            "[OK] G2 is now actionable"
        )

        # ==================================================
        # CASE 2
        # Deliberately unsupported claim must be rejected.
        # ==================================================

        print(
            "\n[CASE 2] Reject unsupported candidate"
        )

        bad_state = make_state(
            max_rounds
        )

        source_document = store.get(
            "toy-verify:D1"
        )

        bad_evidence = Evidence(
            document_id=source_document.document_id,
            title=source_document.title,
            sentence_indices=(0,),
            text=source_document.sentence(
                0
            ),
        )

        bad_candidate = CandidateFact(
            candidate_id="C1",
            statement=(
                "The author of The Glass "
                "Orchard is Rowan Vale."
            ),
            gap_id="G1",
            evidence=(
                bad_evidence,
            ),
        )

        bad_decisions, bad_promoted = (
            verifier.verify_and_commit(
                bad_state,
                bad_state.get_gap(
                    "G1"
                ),
                (
                    bad_candidate,
                ),
            )
        )

        bad_decision = (
            bad_decisions[0]
        )

        print(
            "[OK] Unsupported decision:"
        )

        print(
            f"  accepted="
            f"{bad_decision.accepted}"
        )

        print(
            f"  supported_by_evidence="
            f"{bad_decision.supported_by_evidence}"
        )

        print(
            f"  reason: "
            f"{bad_decision.reason}"
        )

        if bad_decision.accepted:
            raise ValueError(
                "Verifier incorrectly accepted "
                "the Rowan Vale claim."
            )

        if bad_promoted:
            raise ValueError(
                "Unsupported candidate was "
                "promoted to shared knowledge."
            )

        if bad_state.verified_facts:
            raise ValueError(
                "Rejected candidate entered "
                "verified_facts."
            )

        if bad_state.get_gap(
            "G1"
        ).resolved:
            raise ValueError(
                "Rejected candidate incorrectly "
                "resolved G1."
            )

        print(
            "[OK] Unsupported candidate rejected"
        )

        print(
            "[OK] Rejected candidate did NOT "
            "enter shared knowledge"
        )

        report.update(
            {
                "passed": True,
                "supported_case": {
                    "query":
                        retrieval.query,
                    "candidate_facts": [
                        {
                            "candidate_id":
                                candidate.candidate_id,
                            "statement":
                                candidate.statement,
                        }
                        for candidate
                        in candidates
                    ],
                    "decisions": [
                        decision_to_dict(
                            decision
                        )
                        for decision
                        in decisions
                    ],
                    "promoted_facts": [
                        {
                            "fact_id":
                                fact.fact_id,
                            "statement":
                                fact.statement,
                            "gap_id":
                                fact.gap_id,
                        }
                        for fact
                        in promoted
                    ],
                    "actionable_after":
                        actionable,
                },
                "unsupported_case": {
                    "candidate":
                        bad_candidate.statement,
                    "decision":
                        decision_to_dict(
                            bad_decision
                        ),
                    "promoted_count":
                        len(
                            bad_promoted
                        ),
                },
                "state":
                    state.to_dict(),
            }
        )

    except (
        OllamaError,
        QueryPlanningError,
        RetrievalStepError,
        EvidenceFilterError,
        FactExtractionError,
        VerificationError,
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
        print(
            "PHASE 7F PASSED"
        )

        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())