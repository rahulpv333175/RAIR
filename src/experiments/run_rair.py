"""Run RAIR on a bounded HotpotQA subset and checkpoint each result as JSONL."""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone

from src.datasets.hotpotqa import load_hotpotqa
from src.evaluation.metrics import answer_f1, exact_match
from src.llm.ollama_client import OllamaClient, OllamaError
from src.rair.controller import RAIRController
from src.settings import PROJECT_ROOT, load_settings, project_path


def main(argv: list[str] | None = None, *, controller_type=RAIRController,
         system: str = "RAIR") -> int:
    parser = argparse.ArgumentParser(description=f"Run {system} on a diagnostic HotpotQA subset.")
    parser.add_argument("--config", default="config/settings.yaml")
    parser.add_argument("--limit", type=int, default=3, help="Number of diagnostic questions (default: 3).")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--output", help="New JSONL file; existing files are never overwritten.")
    args = parser.parse_args(argv)
    if args.limit < 1 or args.offset < 0:
        parser.error("--limit must be positive and --offset must be non-negative.")

    timestamp = datetime.now(timezone.utc)
    output = project_path(args.output) if args.output else PROJECT_ROOT / "results" / (
        f"{system.lower()}_{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.jsonl"
    )
    try:
        settings = load_settings(args.config)
        dataset_path = project_path(settings["dataset"]["path"])
        examples = load_hotpotqa(dataset_path)
        selected = examples[args.offset:args.offset + args.limit]
        if len(selected) != args.limit:
            raise ValueError("Requested question range exceeds the dataset.")
        client = OllamaClient(settings)
        controller = controller_type(settings, client)
        ready = client.check_ready()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            def save(record: dict) -> None:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()

            save({
                "record_type": "metadata", "created_at_utc": timestamp.isoformat(),
                "system": system,
                "purpose": f"{system} integration diagnostic; not a comparative benchmark.",
                "settings": settings, "environment": ready,
                "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
                "question_ids": [example.task.question_id for example in selected],
                "selection": {"offset": args.offset, "limit": args.limit},
                "policy": controller.policy,
            })
            counts = {"answered": 0, "abstained": 0, "error": 0}
            stop_reasons: dict[str, int] = {}
            agent_error_count = questions_with_agent_errors = 0
            em_sum = f1_sum = 0.0
            for index, example in enumerate(selected, start=1):
                print(f"[{index}/{len(selected)}] {example.task.question_id}", flush=True)
                result = controller.run(example.task)
                # Gold is consulted only after inference has finished.
                em = exact_match(result.prediction.answer, example.gold.answer)
                f1 = answer_f1(result.prediction.answer, example.gold.answer)
                save({"record_type": "result", **result.to_dict(),
                      "evaluation": {"exact_match": em, "answer_f1": f1}})
                counts[result.status] += 1
                failures = len(getattr(result, "agent_errors", []))
                agent_error_count += failures
                questions_with_agent_errors += bool(failures)
                stop_reasons[result.stop_reason] = stop_reasons.get(result.stop_reason, 0) + 1
                em_sum += em
                f1_sum += f1
                print(f"  {result.status}: {result.prediction.answer!r}; "
                      f"retrievals={result.usage['retrieval_calls']}, "
                      f"LLM calls={result.usage['llm_calls']}, "
                      f"stop={result.stop_reason}, EM={em:.0f}", flush=True)
                if result.error:
                    print(f"  {result.error['stage']}: {result.error['message']}", flush=True)
            summary = {
                "record_type": "summary", "completed": True,
                "num_questions": len(selected), **counts,
                "stop_reasons": stop_reasons,
                "agent_error_count": agent_error_count,
                "questions_with_agent_errors": questions_with_agent_errors,
                "exact_match": em_sum / len(selected),
                "answer_f1": f1_sum / len(selected),
                "answer_coverage": counts["answered"] / len(selected),
            }
            save(summary)
        print(json.dumps(summary, indent=2))
        print(f"[SAVED] {output}")
        return int(counts["error"] > 0)
    except (OllamaError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(f"[INTERRUPTED] Completed records remain in {output}", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
