"""Prepare a frozen paired manifest, then run/resume RAIR and KAIR evaluation."""

import argparse
import copy
import json
import platform
import sys
from dataclasses import asdict
from datetime import datetime, timezone

from src.evaluation.budget import RunBudget
from src.evaluation.paired import (
    CONTROLLERS, aggregate, audit_result, fingerprint, load_manifest_examples,
    prepare_manifest, render_report, score_result,
)
from src.llm.ollama_client import OllamaClient, OllamaError
from src.settings import PROJECT_ROOT, load_settings, project_path


def identity(environment: dict) -> tuple:
    return environment["model"]["digest"], environment["server"]["version"]


def read_journal(path, manifest: dict) -> tuple[dict, list[dict], dict | None]:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    if not lines:
        raise ValueError("Cannot resume an empty journal.")
    if not content.endswith("\n"):
        raise ValueError("Journal has an incomplete final line; preserve it and start a new output.")
    try:
        entries = [json.loads(line) for line in lines]
    except json.JSONDecodeError as exc:
        raise ValueError("Journal contains an incomplete/corrupted line; preserve it and start a new output.") from exc
    metadata = entries[0]
    if (metadata.get("record_type") != "metadata" or metadata["manifest_sha256"] != fingerprint(manifest)
            or fingerprint(metadata["manifest"]) != fingerprint(manifest)):
        raise ValueError("Resume manifest does not match the original journal.")
    results = [entry for entry in entries if entry["record_type"] == "result"]
    keys = [(r["question_id"], r["seed"], r["system"]) for r in results]
    planned = [(e["question_id"], e["seed"], e["system"]) for e in manifest["schedule"]]
    if keys != planned[:len(keys)]:
        raise ValueError("Journal results are duplicated, reordered or outside the frozen schedule.")
    summaries = [entry["summary"] for entry in entries if entry["record_type"] == "summary"]
    if (sum(e["record_type"] == "metadata" for e in entries) != 1 or len(summaries) > 1
            or any(e["record_type"] not in {"metadata", "result", "warmup", "verification", "summary"}
                                 for e in entries)):
        raise ValueError("Unexpected or duplicated journal records.")
    if any(e["record_type"] == "verification" and not e["consistent"] for e in entries):
        raise ValueError("Journal was invalidated by a changed model/runtime; start a new run.")
    if summaries and (entries[-2]["record_type"] != "verification"
                      or identity(entries[-2]["environment"]) != identity(metadata["environment"])):
        raise ValueError("Completed journal has no matching final model/runtime verification.")
    if summaries and (entries[-1]["record_type"] != "summary" or summaries[0] != aggregate(manifest, results)):
        raise ValueError("Completed journal summary is inconsistent.")
    return metadata, results, summaries[0] if summaries else None


def save_reports(path, manifest: dict, summary: dict) -> None:
    path.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    path.with_suffix(".md").write_text(render_report(manifest, summary), encoding="utf-8")


def run(manifest: dict, path, *, resume: bool = False) -> dict:
    examples = load_manifest_examples(manifest)
    settings = manifest["settings"]
    config = settings["evaluation"]
    if resume:
        metadata, records, completed = read_journal(path, manifest)
        for row, entry in zip(records, manifest["schedule"]):
            task = examples[row["question_id"]].task
            if (any(row.get(key) != value for key, value in entry.items())
                    or row["input_sha256"] != fingerprint(asdict(task))):
                raise ValueError("Stored inputs or execution order differ from the common protocol.")
            stored_budget = RunBudget(**row["result"]["budget"])
            if (stored_budget.max_retrieval_calls != config["max_retrieval_calls"]
                    or stored_budget.max_llm_calls != config["max_llm_calls"]):
                raise ValueError("Stored budgets differ from the common protocol.")
            audit_result(row["result"], task, stored_budget, settings, row["seed"], row["system"])
            if row["evaluation"] != score_result(row["result"], examples[row["question_id"]]):
                raise ValueError("Stored scores differ from common post-inference scoring.")
        if completed is not None:
            save_reports(path, manifest, completed)
            return completed
    else:
        if any(candidate.exists() for candidate in (path, path.with_suffix(".summary.json"), path.with_suffix(".md"))):
            raise FileExistsError("Use a new output filename, or --resume for the original journal.")
        records = []
        metadata = None
    ready_client = OllamaClient(settings)
    ready = ready_client.check_ready()
    if not ready["model"].get("digest") or not ready["server"].get("version"):
        raise ValueError("Model digest and Ollama version are required for this protocol.")
    if metadata is not None and identity(metadata["environment"]) != identity(ready):
        raise ValueError("Model digest or Ollama version changed since this journal began.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a" if resume else "x", encoding="utf-8") as handle:
        def save(record):
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()

        if not resume:
            save({"record_type": "metadata", "created_at_utc": datetime.now(timezone.utc).isoformat(),
                  "manifest_sha256": fingerprint(manifest), "manifest": manifest,
                  "environment": ready, "python": platform.python_version(), "platform": platform.platform()})
        # Question-free warm-up is outside every scored arm and its budget/timing.
        warmup = ready_client.chat(
            'Return only the JSON object {"ready": true}.', "Initialize the model for a local evaluation.",
            schema={"type": "object", "properties": {"ready": {"type": "boolean"}},
                    "required": ["ready"], "additionalProperties": False},
            temperature=0.0, num_predict=16,
        )
        if warmup.json_object() != {"ready": True}:
            raise OllamaError("Question-free model warm-up failed its response check.")
        save({"record_type": "warmup", "response": asdict(warmup)})
        for index, entry in enumerate(manifest["schedule"][len(records):], start=len(records) + 1):
            effective = copy.deepcopy(settings)
            effective["project"]["seed"] = entry["seed"]
            client = OllamaClient(effective)
            client.generation_temperature = config["temperature"]
            budget = RunBudget(config["max_retrieval_calls"], config["max_llm_calls"])
            client.budget = budget
            controller = CONTROLLERS[entry["system"]](effective, client)
            example = examples[entry["question_id"]]
            print(f"[{index}/{len(manifest['schedule'])}] {entry['system']} seed={entry['seed']} "
                  f"{entry['question_id']}", flush=True)
            result = controller.run(example.task).to_dict()
            audit_result(result, example.task, budget, effective, entry["seed"], entry["system"])
            row = {"record_type": "result", **entry,
                   "input_sha256": fingerprint(asdict(example.task)),
                   "result": result, "evaluation": score_result(result, example)}
            save(row)
            records.append(row)
            print(f"  {result['status']}: {result['prediction']['answer']!r}; "
                  f"EM={row['evaluation']['exact_match']:.0f}; "
                  f"calls={budget.llm_calls}, retrievals={budget.retrieval_calls}, "
                  f"stop={result['stop_reason']}", flush=True)
        final_ready = ready_client.check_ready()
        consistent = identity(ready) == identity(final_ready)
        save({"record_type": "verification", "consistent": consistent, "environment": final_ready})
        if not consistent:
            raise ValueError("Model/runtime identity changed; this run cannot be reported as a controlled comparison.")
        summary = aggregate(manifest, records)
        save({"record_type": "summary", "summary": summary})
    save_reports(path, manifest, summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Freeze questions, seeds, settings, code and common budgets.")
    prepare.add_argument("--config", default="config/settings.yaml")
    prepare.add_argument("--output", required=True)
    execute = sub.add_parser("run", help="Run or resume the frozen paired schedule.")
    execute.add_argument("--manifest", required=True)
    execute.add_argument("--output", help="New JSONL journal, or the original journal with --resume.")
    execute.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            manifest = prepare_manifest(load_settings(args.config))
            path = project_path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as handle:
                json.dump(manifest, handle, indent=2, ensure_ascii=False)
            print(f"[FROZEN] {path}; {len(manifest['questions'])} questions, {len(manifest['schedule'])} system runs")
            return 0
        if args.resume and not args.output:
            parser.error("--resume requires the original --output journal.")
        manifest = json.loads(project_path(args.manifest).read_text(encoding="utf-8"))
        path = project_path(args.output) if args.output else PROJECT_ROOT / "results" / (
            f"paired_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.jsonl"
        )
        summary = run(manifest, path, resume=args.resume)
        print(json.dumps({"num_pairs": summary["num_pairs"], "systems": summary["systems"]}, indent=2))
        print(f"[SAVED] {path}\n[REPORT] {path.with_suffix('.md')}")
        return int(any(values["error"] for values in summary["systems"].values()))
    except KeyboardInterrupt:
        print("[INTERRUPTED] Completed arms are preserved; resume the original manifest/output journal.", file=sys.stderr)
        return 130
    except (OllamaError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
