"""Phase 8: live end-to-end checks with complete and missing source evidence."""

import argparse
import copy
import json
import sys
from datetime import datetime, timezone

from src.datasets.hotpotqa import QuestionInput
from src.experiments.run_rair import project_path
from src.llm.ollama_client import OllamaClient, OllamaError
from src.rair.controller import RAIRController
from src.retrieval.document_store import Document
from src.settings import PROJECT_ROOT, load_settings


def make_task(*, missing_birthplace: bool = False) -> QuestionInput:
    question_id = "pipeline-missing" if missing_birthplace else "pipeline-complete"
    return QuestionInput(
        question_id,
        "In which city was the author of The Glass Orchard born?",
        (
            Document(f"{question_id}:D1", question_id, "The Glass Orchard", (
                "The Glass Orchard was written by Mira Solen.",
                "The novel was published in 1998.",
            )),
            Document(f"{question_id}:D2", question_id, "Mira Solen", (
                "Mira Solen writes novels." if missing_birthplace
                else "Mira Solen was born in the city of Nerava.",
            )),
            Document(f"{question_id}:D3", question_id, "Orchards", (
                "An orchard is land planted with fruit trees.",
            )),
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    timestamp = datetime.now(timezone.utc)
    output = project_path(args.output) if args.output else PROJECT_ROOT / "results" / (
        f"phase8_rair_pipeline_{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    )
    report = {"created_at_utc": timestamp.isoformat(), "passed": False, "cases": []}
    try:
        settings = load_settings()
        client = OllamaClient(settings)
        report.update(settings=settings, environment=client.check_ready())
        output.parent.mkdir(parents=True, exist_ok=True)
        # Reserve a new file before inference so an existing report is never lost.
        with output.open("x", encoding="utf-8") as handle:
            for missing in (False, True):
                config = copy.deepcopy(settings)
                if missing:
                    config["rair"]["max_rounds"] = 2
                print(f"[CASE] {'Missing birthplace' if missing else 'Complete evidence'}", flush=True)
                result = RAIRController(config, client).run(make_task(missing_birthplace=missing))
                passed = result.error is None and (
                    result.prediction.abstain if missing else (
                        not result.prediction.abstain
                        and result.prediction.answer.lower() == "nerava"
                        and {source["title"] for source in result.sources}
                        == {"The Glass Orchard", "Mira Solen"}
                    )
                )
                report["cases"].append({
                    "missing_birthplace": missing, "max_rounds": config["rair"]["max_rounds"],
                    "passed": passed, **result.to_dict(),
                })
                print(f"  passed={passed}, status={result.status}, "
                      f"answer={result.prediction.answer!r}, rounds={result.state.current_round}", flush=True)
                report["passed"] = len(report["cases"]) == 2 and all(
                    case["passed"] for case in report["cases"]
                )
                handle.seek(0)
                json.dump(report, handle, indent=2, ensure_ascii=False)
                handle.truncate()
                handle.flush()
        print(f"[SAVED] {output}")
        print("PHASE 8 PASSED" if report["passed"] else "PHASE 8 FAILED")
        return 0 if report["passed"] else 1
    except (OllamaError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
