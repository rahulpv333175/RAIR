"""Validate local HotpotQA pools and save a small, gold-free input preview."""

import hashlib
import json
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src.datasets.hotpotqa import HotpotExample, load_hotpotqa
from src.retrieval.document_store import DocumentStore
from src.settings import PROJECT_ROOT, load_settings


def audit_support_references(example: HotpotExample) -> list[dict]:
    """Diagnostics only: never correct labels, select evidence, or drop questions."""
    issues = []
    for title, index in example.gold.supporting_facts:
        matches = [doc for doc in example.task.documents if doc.title == title]
        reason = None
        if len(matches) != 1:
            reason = f"Expected one matching title; found {len(matches)}."
        elif not 0 <= index < len(matches[0].sentences):
            reason = "Sentence index is outside the original paragraph."
        elif not matches[0].sentence(index).strip():
            reason = "Supporting sentence is empty or whitespace-only."
        if reason:
            issues.append({"question_id": example.task.question_id,
                           "title": title, "sentence_id": index, "reason": reason})
    return issues


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    report_path = PROJECT_ROOT / "results" / "phase3_dataset_check.json"
    report = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "passed": False}
    try:
        settings = load_settings()
        dataset = settings["dataset"]
        if (dataset["name"], dataset["split"], dataset["setting"]) != (
            "hotpotqa", "dev", "distractor"
        ):
            raise ValueError("This check expects HotpotQA dev/distractor settings.")
        if settings["retrieval"]["corpus_scope"] != "per_question":
            raise ValueError("Use per_question document pools.")

        source = PROJECT_ROOT / dataset["path"]
        print(f"[RUN] Loading {source}", flush=True)
        examples = load_hotpotqa(source)
        with source.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()

        pool_sizes = Counter()
        issues = []
        for example in examples:
            store = DocumentStore(example.task.question_id, example.task.documents)
            pool_sizes[len(store)] += 1
            issues.extend(audit_support_references(example))

        preview_path = (PROJECT_ROOT / settings["paths"]["processed_data"]
                        / "hotpot_dev_smoke_inputs.json")
        preview = {"purpose": "First 3 records for debugging only; not a benchmark sample.",
                   "examples": [asdict(example.task) for example in examples[:3]]}
        write_json(preview_path, preview)
        report.update({
            "passed": True,
            "source_path": str(source),
            "source_sha256": digest,
            "dataset": dataset,
            "num_examples": len(examples),
            "num_documents": sum(size * count for size, count in pool_sizes.items()),
            "pool_size_distribution": dict(sorted(pool_sizes.items())),
            "smoke_question_ids": [example.task.question_id for example in examples[:3]],
            "annotation_issues": issues,
            "normalization": "Raw titles/sentences retained; search whitespace normalized.",
            "pool_order": "Original context order; no gold-based filtering or ordering.",
        })
        print(f"[OK] Loaded {len(examples)} questions")
        print(f"[OK] Validated {report['num_documents']} documents in separate pools")
        print(f"[INFO] Pool sizes (documents: questions): {dict(sorted(pool_sizes.items()))}")
        print(f"[INFO] Source SHA-256: {digest}")
        label = "WARN" if issues else "OK"
        print(f"[{label}] Supporting-fact reference issues: {len(issues)}")
        print("[OK] Gold labels are separate from question/document inputs")
        print(f"[SAVED] {preview_path}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report["passed"] = False
        report["error"] = str(exc)
        print(f"[FAIL] {exc}", file=sys.stderr)

    try:
        write_json(report_path, report)
    except OSError as exc:
        print(f"[FAIL] Could not save report: {exc}", file=sys.stderr)
        return 1
    print(f"[SAVED] {report_path}")
    if report["passed"]:
        print("PHASE 3 PASSED")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())