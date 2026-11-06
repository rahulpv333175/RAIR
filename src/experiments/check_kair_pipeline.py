"""Step 2: live competitive KAIR smoke checks without seeded agent knowledge."""

import argparse
import copy
import json
import sys
from datetime import datetime, timezone

from src.experiments.check_rair_pipeline import make_task
from src.experiments.run_rair import project_path
from src.kair.controller import KAIRController
from src.llm.ollama_client import OllamaClient, OllamaError
from src.settings import PROJECT_ROOT, load_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    timestamp = datetime.now(timezone.utc)
    output = project_path(args.output) if args.output else PROJECT_ROOT / "results" / (
        f"step2_kair_pipeline_{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    )
    report = {"created_at_utc": timestamp.isoformat(), "passed": False, "cases": []}
    try:
        settings = load_settings()
        client = OllamaClient(settings)
        report.update(settings=settings, environment=client.check_ready())
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            for missing in (False, True):
                config = copy.deepcopy(settings)
                if missing:
                    config["kair"]["max_iterations"] = 1
                controller = KAIRController(config, client)
                print(f"[CASE] {'Missing birthplace' if missing else 'Complete evidence'}", flush=True)
                result = controller.run(make_task(missing_birthplace=missing))
                passed = result.error is None and not result.agent_errors and (
                    result.prediction.abstain if missing else (
                        not result.prediction.abstain and result.prediction.answer.lower() == "nerava"
                        and {source["title"] for source in result.sources}
                        == {"The Glass Orchard", "Mira Solen"}
                    )
                )
                report["cases"].append({"missing_birthplace": missing, "policy": controller.policy,
                                        "passed": passed, **result.to_dict()})
                report["passed"] = len(report["cases"]) == 2 and all(
                    case["passed"] for case in report["cases"]
                )
                handle.seek(0)
                json.dump(report, handle, indent=2, ensure_ascii=False)
                handle.truncate()
                handle.flush()
                print(f"  passed={passed}, status={result.status}, answer={result.prediction.answer!r}, "
                      f"selected={result.selected_agent_id}, retrievals={result.usage['retrieval_calls']}", flush=True)
        print(f"[SAVED] {output}")
        print("STEP 2 KAIR SMOKE PASSED" if report["passed"] else "STEP 2 KAIR SMOKE FAILED")
        return 0 if report["passed"] else 1
    except (OllamaError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
