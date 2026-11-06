import hashlib
import json
from pathlib import Path
import random
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 1. Collect all historically touched IDs
used_qids = set()
for config_file in (ROOT / "config").glob("*.json"):
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "questions" in data:
            for item in data["questions"]:
                if isinstance(item, str):
                    used_qids.add(item)
                elif isinstance(item, dict):
                    used_qids.add(item.get("question_id") or item.get("_id"))
    except Exception:
        pass

for res_file in (ROOT / "results").glob("**/*.jsonl"):
    try:
        with open(res_file, "r", encoding="utf-8") as f:
            for line in f:
                if "question_id" in line:
                    row = json.loads(line)
                    if row.get("question_id"):
                        used_qids.add(row["question_id"])
    except Exception:
        pass

print(f"Total historically excluded question IDs: {len(used_qids)}")

# Load HotpotQA raw data
raw_path = ROOT / "data" / "raw" / "hotpot_dev_distractor_v1.json"
dev_data = json.loads(raw_path.read_text(encoding="utf-8"))

eligible = [q for q in dev_data if q["_id"] not in used_qids]
print(f"Eligible untouched questions: {len(eligible)}")

# Deterministic sample of 25 questions
rng = random.Random(20261102)
sampled = rng.sample(eligible, 25)
sampled_qids = [q["_id"] for q in sampled]
print(f"Sampled 25 untouched questions for RAIR v3: {sampled_qids[:3]}...")

# Verify zero overlap
assert len(set(sampled_qids) & used_qids) == 0, "FATAL: Overlap with historical questions!"

# 2. Build manifest: 25 questions x 2 seeds (42, 43) = 50 pairs (100 runs)
seeds = [42, 43]
pairs = []
pair_idx = 1
for q in sampled:
    qid = q["_id"]
    for seed in seeds:
        # Alternate position in pair to eliminate order effects
        if pair_idx % 2 == 1:
            first, second = "RAIR", "KAIR"
        else:
            first, second = "KAIR", "RAIR"
        pairs.append({
            "pair_index": pair_idx,
            "question_id": qid,
            "seed": seed,
            "first_system": first,
            "second_system": second,
            "question": q["question"],
            "gold_answer": q["answer"]
        })
        pair_idx += 1

manifest = {
    "benchmark_name": "rair_v3_paired_benchmark",
    "created_at_utc": "2026-11-02T22:45:00Z",
    "dataset": "data/raw/hotpot_dev_distractor_v1.json",
    "model": "qwen3.5:4b",
    "budget": {
        "max_retrieval_calls": 4,
        "max_llm_calls": 18
    },
    "num_questions": len(sampled),
    "seeds": seeds,
    "total_pairs": len(pairs),
    "total_runs": len(pairs) * 2,
    "questions": sampled_qids,
    "pairs": pairs
}

manifest_path = ROOT / "config" / "rair_v3_manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"Saved manifest to {manifest_path} ({len(pairs)} pairs / {len(pairs)*2} runs)")

# 3. Create settings file
with open(ROOT / "config" / "rair_v2_phase2_settings.json", "r", encoding="utf-8") as f:
    settings = json.load(f)

settings_path = ROOT / "config" / "rair_v3_settings.json"
settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
print(f"Saved settings to {settings_path}")

# 4. Create freeze metadata and snapshot
v3_dir = ROOT / "results" / "rair_v3"
v3_dir.mkdir(parents=True, exist_ok=True)

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

freeze_meta = {
    "release": "RAIR_v3",
    "timestamp_utc": "2026-11-02T22:45:00Z",
    "target_model": "qwen3.5:4b",
    "budget": {"max_retrieval_calls": 4, "max_llm_calls": 18},
    "file_hashes": file_hashes,
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

# Zip source snapshot
snapshot_zip = v3_dir / "rair_v3_source_snapshot.zip"
with zipfile.ZipFile(snapshot_zip, "w", zipfile.ZIP_DEFLATED) as zf:
    for rel in tracked_files:
        zf.write(ROOT / rel, arcname=rel)
print(f"Saved source snapshot to {snapshot_zip}")

