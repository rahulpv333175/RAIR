import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent

tracked_files = [
    "src/llm/prompts.py",
    "src/rair/query_planner.py",
    "src/rair/controller.py",
    "src/rair/synthesizer.py",
    "config/rair_scale_manifest.json",
    "config/rair_scale_settings.json"
]

file_hashes = {}
for rel in tracked_files:
    p = ROOT / rel
    file_hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()

scale_dir = ROOT / "results" / "rair_scale"
scale_dir.mkdir(parents=True, exist_ok=True)

freeze_meta = {
    "release": "RAIR_Scale_Benchmark",
    "timestamp_utc": "2026-11-03T05:15:00Z",
    "target_model": "qwen3.5:4b",
    "budget": {"max_retrieval_calls": 4, "max_llm_calls": 18},
    "file_hashes": file_hashes,
    "manifest_sha256": file_hashes["config/rair_scale_manifest.json"],
    "num_questions": 50,
    "num_pairs": 100,
    "num_runs": 200,
    "upgrades": [
        "Synthesizer Polar Rule: strictly output yes/no on polar questions",
        "Synthesizer Minimal Span Rule: extract entity/work name without conversational wrapping",
        "Synthesizer Proper Designation Rule: retain full route/award designations (e.g. European route E 22)",
        "Decomposer Dual-Entity Rule: create gaps for both candidates in comparison questions",
        "Synthesizer Fallible Gap Premise: answer from verified facts even if descriptive premise is unresolved",
        "Query Planner Negative Constraint: pass forbidden previous queries to avoid repeated_query stalls",
        "Controller Budget-Aware Early Exit: safely break loop when <4 non-final calls remain to preserve synthesis call"
    ]
}

freeze_path = scale_dir / "rair_scale_freeze.json"
freeze_path.write_text(json.dumps(freeze_meta, indent=2), encoding="utf-8")
print(f"Saved scale freeze metadata to {freeze_path}")

snapshot_zip = scale_dir / "rair_scale_source_snapshot.zip"
with zipfile.ZipFile(snapshot_zip, "w", zipfile.ZIP_DEFLATED) as zf:
    for rel in tracked_files:
        zf.write(ROOT / rel, arcname=rel)
print(f"Saved scale source snapshot to {snapshot_zip}")

