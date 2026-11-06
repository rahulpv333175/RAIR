"""Phase 7G live RAIR synthesizer check."""

import json
import sys
from datetime import datetime, timezone
from typing import Any

from src.llm.ollama_client import (
    OllamaClient,
    OllamaError,
)
from src.rair.state import (
    Evidence,
    Gap,
    RAIRState,
    VerifiedFact,
)
from src.rair.synthesizer import (
    RAIRSynthesizer,
    SynthesisError,
)
from src.settings import (
    PROJECT_ROOT,
    load_settings,
)


def make_state(
    max_rounds: int,
) -> RAIRState:
    state = RAIRState(
        question_id="toy-synth",
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
        document_id="toy-synth:D1",
        title="The Glass Orchard",
        sentence_indices=(0,),
        text=(
            "The Glass Orchard was "
            "written by Mira Solen."
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
            evidence=(
                evidence,
            ),
        )
    )

    state.resolve_gap(
        "G1"
    )


def add_birthplace_fact(
    state: RAIRState,
) -> None:
    evidence = Evidence(
        document_id="toy-synth:D2",
        title="Mira Solen",
        sentence_indices=(0,),
        text=(
            "Mira Solen was born "
            "in the city of Nerava."
        ),
    )

    state.add_verified_fact(
        VerifiedFact(
            fact_id="F2",
            statement=(
                "Mira Solen was born "
                "in Nerava."
            ),
            gap_id="G2",
            evidence=(
                evidence,
            ),
        )
    )

    state.resolve_gap(
        "G2"
    )


def main() -> int:
    report_path = (
        PROJECT_ROOT
        / "results"
        / "phase7g_synthesizer_check.json"
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

        synthesizer = RAIRSynthesizer(
            client
        )

        max_rounds = int(
            settings["rair"]["max_rounds"]
        )

        # ==========================================
        # CASE 1
        # Complete verified knowledge.
        # ==========================================

        print(
            "\n[CASE 1] Complete verified knowledge"
        )

        complete_state = make_state(
            max_rounds
        )

        add_author_fact(
            complete_state
        )

        add_birthplace_fact(
            complete_state
        )

        if not complete_state.is_complete():
            raise ValueError(
                "Complete test state is "
                "not marked complete."
            )

        result = synthesizer.synthesize(
            complete_state
        )

        print(
            f"[OK] Answer: {result.answer}"
        )

        print(
            "[OK] Citations: "
            + ", ".join(
                result.citations
            )
        )

        print(
            f"[OK] Abstain: {result.abstain}"
        )

        if result.abstain:
            raise ValueError(
                "Synthesizer abstained despite "
                "complete verified knowledge."
            )

        if (
            result.answer.lower()
            != "nerava"
        ):
            raise ValueError(
                "Expected answer Nerava, got "
                f"{result.answer!r}."
            )

        if "F2" not in result.citations:
            raise ValueError(
                "Final answer did not cite "
                "the birthplace fact F2."
            )

        print(
            "[OK] Complete evidence produced "
            "the expected answer"
        )

        # ==========================================
        # CASE 2
        # Incomplete verified knowledge.
        # ==========================================

        print(
            "\n[CASE 2] Incomplete verified knowledge"
        )

        incomplete_state = make_state(
            max_rounds
        )

        add_author_fact(
            incomplete_state
        )

        if incomplete_state.is_complete():
            raise ValueError(
                "Incomplete state was "
                "incorrectly marked complete."
            )

        incomplete_result = (
            synthesizer.synthesize(
                incomplete_state
            )
        )

        print(
            f"[OK] Answer: "
            f"{incomplete_result.answer!r}"
        )

        print(
            f"[OK] Citations: "
            f"{list(incomplete_result.citations)}"
        )

        print(
            f"[OK] Abstain: "
            f"{incomplete_result.abstain}"
        )

        if not incomplete_result.abstain:
            raise ValueError(
                "Synthesizer answered despite "
                "insufficient verified knowledge."
            )

        if incomplete_result.answer:
            raise ValueError(
                "Abstention returned a nonempty answer."
            )

        if incomplete_result.citations:
            raise ValueError(
                "Abstention returned citations."
            )

        print(
            "[OK] Incomplete knowledge caused abstention"
        )

        report.update(
            {
                "passed": True,
                "complete_case": {
                    "answer":
                        result.answer,
                    "citations":
                        list(
                            result.citations
                        ),
                    "abstain":
                        result.abstain,
                },
                "incomplete_case": {
                    "answer":
                        incomplete_result.answer,
                    "citations":
                        list(
                            incomplete_result.citations
                        ),
                    "abstain":
                        incomplete_result.abstain,
                },
            }
        )

    except (
        OllamaError,
        SynthesisError,
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
            "PHASE 7G PASSED"
        )

        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())