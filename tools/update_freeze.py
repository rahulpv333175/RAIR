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
    "config/rair_v3_manifest.json",
    "config/rair_v3_settings.json"
]

file_hashes = {}
for rel in tracked_files:
    p = ROOT / rel
    file_hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()

v3_dir = ROOT / "results" / "rair_v3"
v3_dir.mkdir(parents=True, exist_ok=True)

freeze_meta = {
    "release": "RAIR_v3",
    "timestamp_utc": "2026-11-02T22:45:00Z",
    "target_model": "qwen3.5:4b",
    "budget": {"max_retrieval_calls": 4, "max_llm_calls": 18},
    "file_hashes": file_hashes,
    "manifest_sha256": file_hashes["config/rair_v3_manifest.json"],
    "upgrades": [
        "Synthesizer Polar Rule: strictly output yes/no on polar questions",
        "Synthesizer Minimal Span Rule: extract entity/work name without conversational wrapping",
        "Synthesizer Fallible Gap Premise: answer from verified facts even if descriptive premise is unresolved",
        "Query Planner Negative Constraint: pass forbidden previous queries to avoid repeated_query stalls",
        "Controller Budget-Aware Early Exit: safely break loop when <4 non-final calls remain to preserve synthesis call"
    ]
}

freeze_path = v3_dir / "rair_v3_freeze.json"
freeze_path.write_text(json.dumps(freeze_meta, indent=2), encoding="utf-8")
print(f"Saved freeze metadata to {freeze_path}")

snapshot_zip = v3_dir / "rair_v3_source_snapshot.zip"
with zipfile.ZipFile(snapshot_zip, "w", zipfile.ZIP_DEFLATED) as zf:
    for rel in tracked_files:
        zf.write(ROOT / rel, arcname=rel)
print(f"Saved source snapshot to {snapshot_zip}")

