"""Phase 7C live integration: RAIR Query Planner -> BM25."""

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
)
from src.rair.retrieval_step import (
    RAIRRetrievalStep,
    RetrievalStepError,
)
from src.rair.state import (
    Evidence,
    Gap,
    RAIRState,
    VerifiedFact,
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
            document_id="toy-retrieval:D1",
            question_id="toy-retrieval",
            title="The Glass Orchard",
            sentences=(
                "The Glass Orchard was written by Mira Solen.",
            ),
        ),
        Document(
            document_id="toy-retrieval:D2",
            question_id="toy-retrieval",
            title="Mira Solen",
            sentences=(
                "Mira Solen was born in the city of Nerava.",
            ),
        ),
        Document(
            document_id="toy-retrieval:D3",
            question_id="toy-retrieval",
            title="River Ecology",
            sentences=(
                "River ecosystems contain many aquatic species.",
            ),
        ),
        Document(
            document_id="toy-retrieval:D4",
            question_id="toy-retrieval",
            title="Orchards",
            sentences=(
                "An orchard is land planted with fruit trees.",
            ),
        ),
    )

    return DocumentStore(
        "toy-retrieval",
        documents,
    )


def make_state(
    max_rounds: int,
) -> RAIRState:
    state = RAIRState(
        question_id="toy-retrieval",
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


def install_author_fact(
    state: RAIRState,
) -> None:
    evidence = Evidence(
        document_id="toy-retrieval:D1",
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
        / "phase7c_retrieval_step_check.json"
    )

    report: dict[str, Any] = {
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "passed": False,
        "rounds": [],
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

        state = make_state(
            int(
                settings["rair"]["max_rounds"]
            )
        )

        store = make_store()

        # ==========================================
        # ROUND 1
        # ==========================================

        print(
            "\n[ROUND 1] Author gap"
        )

        result_1 = retrieval_step.run(
            state,
            store,
        )

        print(
            f"[OK] Gap: {result_1.gap.gap_id}"
        )

        print(
            f"[OK] Query: {result_1.query}"
        )

        if not result_1.results:
            raise ValueError(
                "Round 1 retrieved no documents."
            )

        print(
            "[OK] Retrieved:"
        )

        for item in result_1.results:
            print(
                f"  #{item.rank} "
                f"{item.document.title} "
                f"(score={item.score:.4f})"
            )

        if (
            result_1.results[0]
            .document.document_id
            != "toy-retrieval:D1"
        ):
            raise ValueError(
                "Expected The Glass Orchard "
                "document to rank first."
            )

        report["rounds"].append(
            {
                "round":
                    result_1.round_number,
                "gap_id":
                    result_1.gap.gap_id,
                "query":
                    result_1.query,
                "retrieved":
                    [
                        {
                            "rank":
                                item.rank,
                            "document_id":
                                item.document.document_id,
                            "title":
                                item.document.title,
                            "score":
                                item.score,
                        }
                        for item
                        in result_1.results
                    ],
            }
        )

        # We manually install the verified fact here.
        #
        # Evidence Filter, Fact Extractor and Verifier
        # do not exist yet, so this simulates their
        # future accepted output.
        install_author_fact(
            state
        )

        print(
            "[SIMULATED] Verified author fact "
            "installed: Mira Solen"
        )

        # ==========================================
        # ROUND 2
        # ==========================================

        print(
            "\n[ROUND 2] Birth-city gap"
        )

        result_2 = retrieval_step.run(
            state,
            store,
        )

        print(
            f"[OK] Gap: {result_2.gap.gap_id}"
        )

        print(
            f"[OK] Query: {result_2.query}"
        )

        if "mira" not in result_2.query.lower():
            raise ValueError(
                "Round 2 query did not use "
                "verified bridge entity Mira Solen."
            )

        if not result_2.results:
            raise ValueError(
                "Round 2 retrieved no documents."
            )

        print(
            "[OK] Retrieved:"
        )

        for item in result_2.results:
            print(
                f"  #{item.rank} "
                f"{item.document.title} "
                f"(score={item.score:.4f})"
            )

        if (
            result_2.results[0]
            .document.document_id
            != "toy-retrieval:D2"
        ):
            raise ValueError(
                "Expected Mira Solen document "
                "to rank first in round 2."
            )

        report["rounds"].append(
            {
                "round":
                    result_2.round_number,
                "gap_id":
                    result_2.gap.gap_id,
                "query":
                    result_2.query,
                "retrieved":
                    [
                        {
                            "rank":
                                item.rank,
                            "document_id":
                                item.document.document_id,
                            "title":
                                item.document.title,
                            "score":
                                item.score,
                        }
                        for item
                        in result_2.results
                    ],
            }
        )

        if len(
            state.query_history
        ) != 2:
            raise ValueError(
                "Expected two recorded query attempts."
            )

        print(
            "\n[OK] Query history contains "
            "2 retrieval attempts"
        )

        print(
            "[OK] Planner used verified knowledge "
            "between retrieval rounds"
        )

        report["state"] = (
            state.to_dict()
        )

        report["passed"] = True

    except (
        OllamaError,
        QueryPlanningError,
        RetrievalStepError,
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
            "PHASE 7C PASSED"
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())