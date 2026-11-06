"""Phase 7D live RAIR evidence-filter integration check."""

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
from src.rair.query_planner import (
    QueryPlanningError,
    RAIRQueryPlanner,
)
from src.rair.retrieval_step import (
    RAIRRetrievalStep,
    RetrievalStepError,
)
from src.rair.state import (
    Gap,
    RAIRState,
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
            document_id="toy-filter:D1",
            question_id="toy-filter",
            title="The Glass Orchard",
            sentences=(
                "The Glass Orchard was written by Mira Solen.",
                "The novel was published in 1998.",
            ),
        ),
        Document(
            document_id="toy-filter:D2",
            question_id="toy-filter",
            title="Mira Solen",
            sentences=(
                "Mira Solen was born in the city of Nerava.",
                "She later became a novelist.",
            ),
        ),
        Document(
            document_id="toy-filter:D3",
            question_id="toy-filter",
            title="Orchards",
            sentences=(
                "An orchard is land planted with fruit trees.",
            ),
        ),
        Document(
            document_id="toy-filter:D4",
            question_id="toy-filter",
            title="Glass",
            sentences=(
                "Glass is an amorphous solid material.",
            ),
        ),
    )

    return DocumentStore(
        "toy-filter",
        documents,
    )


def make_state(
    max_rounds: int,
) -> RAIRState:
    state = RAIRState(
        question_id="toy-filter",
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


def main() -> int:
    report_path = (
        PROJECT_ROOT
        / "results"
        / "phase7d_evidence_filter_check.json"
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

        state = make_state(
            int(
                settings["rair"]["max_rounds"]
            )
        )

        store = make_store()

        # ==========================================
        # ROUND 1: Author
        # ==========================================

        print(
            "\n[ROUND 1] Author evidence"
        )

        retrieval_1 = retrieval_step.run(
            state,
            store,
        )

        print(
            f"[OK] Query: {retrieval_1.query}"
        )

        print(
            "[OK] BM25 retrieved:"
        )

        for result in retrieval_1.results:
            print(
                f"  #{result.rank} "
                f"{result.document.title}"
            )

        evidence_1 = evidence_filter.filter(
            state,
            retrieval_1.gap,
            retrieval_1,
        )

        if not evidence_1:
            raise ValueError(
                "Evidence Filter kept no "
                "author evidence."
            )

        print(
            "[OK] Evidence Filter kept:"
        )

        for evidence in evidence_1:
            print(
                f"  {evidence.document_id} "
                f"{list(evidence.sentence_indices)}"
            )

            print(
                f"     {evidence.text}"
            )

        selected_ids_1 = {
            evidence.document_id
            for evidence in evidence_1
        }

        if (
            "toy-filter:D1"
            not in selected_ids_1
        ):
            raise ValueError(
                "Evidence Filter failed to keep "
                "The Glass Orchard evidence."
            )

        if (
            "toy-filter:D3"
            in selected_ids_1
            or "toy-filter:D4"
            in selected_ids_1
        ):
            raise ValueError(
                "Evidence Filter kept an irrelevant "
                "distractor document."
            )

        # We do NOT yet have Fact Extractor/Verifier.
        # Therefore we stop after filtering instead of
        # manually pretending the evidence became knowledge.

        report.update(
            {
                "passed": True,
                "query": retrieval_1.query,
                "retrieved": [
                    {
                        "rank":
                            result.rank,
                        "document_id":
                            result.document.document_id,
                        "title":
                            result.document.title,
                        "score":
                            result.score,
                    }
                    for result
                    in retrieval_1.results
                ],
                "filtered_evidence": [
                    {
                        "document_id":
                            evidence.document_id,
                        "title":
                            evidence.title,
                        "sentence_indices":
                            list(
                                evidence.sentence_indices
                            ),
                        "text":
                            evidence.text,
                    }
                    for evidence
                    in evidence_1
                ],
                "state":
                    state.to_dict(),
            }
        )

        print(
            "\n[OK] Relevant source evidence "
            "was preserved exactly"
        )

        print(
            "[OK] Distractor evidence was rejected"
        )

    except (
        OllamaError,
        QueryPlanningError,
        RetrievalStepError,
        EvidenceFilterError,
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
            "PHASE 7D PASSED"
        )

        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())