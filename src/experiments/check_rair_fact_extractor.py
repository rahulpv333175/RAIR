"""Phase 7E live RAIR fact-extraction integration check."""

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
            document_id="toy-extract:D1",
            question_id="toy-extract",
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
            document_id="toy-extract:D2",
            question_id="toy-extract",
            title="Mira Solen",
            sentences=(
                (
                    "Mira Solen was born "
                    "in the city of Nerava."
                ),
                (
                    "She later became "
                    "a novelist."
                ),
            ),
        ),
        Document(
            document_id="toy-extract:D3",
            question_id="toy-extract",
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
        "toy-extract",
        documents,
    )


def make_state(
    max_rounds: int,
) -> RAIRState:
    state = RAIRState(
        question_id="toy-extract",
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
        / "phase7e_fact_extractor_check.json"
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

        evidence_filter = (
            RAIREvidenceFilter(
                client
            )
        )

        fact_extractor = (
            RAIRFactExtractor(
                client
            )
        )

        state = make_state(
            int(
                settings["rair"][
                    "max_rounds"
                ]
            )
        )

        store = make_store()

        print(
            "\n[STEP 1] Query + retrieval"
        )

        retrieval = retrieval_step.run(
            state,
            store,
        )

        print(
            f"[OK] Gap: "
            f"{retrieval.gap.gap_id}"
        )

        print(
            f"[OK] Query: "
            f"{retrieval.query}"
        )

        print(
            "[OK] Retrieved:"
        )

        for result in retrieval.results:
            print(
                f"  #{result.rank} "
                f"{result.document.title}"
            )

        print(
            "\n[STEP 2] Evidence filtering"
        )

        evidence = evidence_filter.filter(
            state,
            retrieval.gap,
            retrieval,
        )

        if not evidence:
            raise ValueError(
                "Evidence Filter kept "
                "no evidence."
            )

        for index, item in enumerate(
            evidence,
            start=1,
        ):
            print(
                f"[OK] E{index}: "
                f"{item.document_id} "
                f"{list(item.sentence_indices)}"
            )

            print(
                f"     {item.text}"
            )

        print(
            "\n[STEP 3] Fact extraction"
        )

        candidates = fact_extractor.extract(
            state,
            retrieval.gap,
            evidence,
        )

        if not candidates:
            raise ValueError(
                "Fact Extractor produced "
                "no candidate facts."
            )

        for candidate in candidates:
            print(
                f"[OK] "
                f"{candidate.candidate_id}: "
                f"{candidate.statement}"
            )

            print(
                "     evidence documents: "
                + ", ".join(
                    item.document_id
                    for item
                    in candidate.evidence
                )
            )

        # For this synthetic test, at least one
        # candidate should identify Mira Solen.
        if not any(
            "mira solen"
            in candidate.statement.lower()
            for candidate in candidates
        ):
            raise ValueError(
                "No candidate fact identified "
                "Mira Solen."
            )

        # Critical architecture check:
        # candidate facts must NOT automatically
        # enter shared verified knowledge.
        if state.verified_facts:
            raise ValueError(
                "Candidate facts were incorrectly "
                "added to verified_facts before "
                "verification."
            )

        print(
            "\n[OK] Candidate fact extracted"
        )

        print(
            "[OK] Candidate has source evidence"
        )

        print(
            "[OK] Candidate has NOT entered "
            "verified shared knowledge"
        )

        report.update(
            {
                "passed": True,
                "gap_id":
                    retrieval.gap.gap_id,
                "query":
                    retrieval.query,
                "filtered_evidence": [
                    {
                        "document_id":
                            item.document_id,
                        "title":
                            item.title,
                        "sentence_indices":
                            list(
                                item.sentence_indices
                            ),
                        "text":
                            item.text,
                    }
                    for item
                    in evidence
                ],
                "candidate_facts": [
                    {
                        "candidate_id":
                            candidate.candidate_id,
                        "statement":
                            candidate.statement,
                        "gap_id":
                            candidate.gap_id,
                        "evidence": [
                            {
                                "document_id":
                                    item.document_id,
                                "title":
                                    item.title,
                                "sentence_indices":
                                    list(
                                        item.sentence_indices
                                    ),
                                "text":
                                    item.text,
                            }
                            for item
                            in candidate.evidence
                        ],
                    }
                    for candidate
                    in candidates
                ],
                "verified_fact_count":
                    len(
                        state.verified_facts
                    ),
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
            "PHASE 7E PASSED"
        )

        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())