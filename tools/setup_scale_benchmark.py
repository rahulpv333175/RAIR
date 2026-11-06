import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.evaluation.paired import prepare_manifest

# Collect all exclusions:
# 1. exclusions from v3 settings
# 2. questions in v3 manifest
with open(ROOT / "config" / "rair_v3_settings.json", "r", encoding="utf-8") as f:
    v3_settings = json.load(f)

with open(ROOT / "config" / "rair_v3_manifest.json", "r", encoding="utf-8") as f:
    v3_manifest = json.load(f)

v3_qids = [q["question_id"] for q in v3_manifest["questions"]]
all_exclusions = sorted(list(set(v3_settings["evaluation"]["exclude_question_ids"]) | set(v3_qids)))
print(f"Total exclusions for Scale Benchmark: {len(all_exclusions)} (380 prior + 25 v3 = {len(all_exclusions)})")

scale_settings = copy.deepcopy(v3_settings)
scale_settings["project"]["name"] = "RAIR Extended Scale Benchmark (200 Runs)"
scale_settings["evaluation"]["name"] = "RAIR Extended Scale Confirmatory Evaluation vs Unchanged KAIR"
scale_settings["evaluation"]["purpose"] = (
    "High-power empirical scale evaluation of RAIR against unchanged competitive KAIR across "
    "50 strictly disjoint HotpotQA questions and 2 seeds (100 matched pairs / 200 system runs) "
    "under strict protocol parity (RunBudget(4, 18), BM25 top-3 pools, identical environment)."
)
scale_settings["evaluation"]["sample_size"] = 50
scale_settings["evaluation"]["sample_seed"] = 20261105
scale_settings["evaluation"]["seeds"] = [42, 43]
scale_settings["evaluation"]["exclude_question_ids"] = all_exclusions
scale_settings["evaluation"]["bootstrap_seed"] = 20261105

scale_settings_path = ROOT / "config" / "rair_scale_settings.json"
with open(scale_settings_path, "w", encoding="utf-8") as f:
    json.dump(scale_settings, f, indent=2, ensure_ascii=False)
print(f"Wrote scale settings to {scale_settings_path}")

# Build manifest using prepare_manifest
manifest = prepare_manifest(scale_settings)
scale_manifest_path = ROOT / "config" / "rair_scale_manifest.json"
with open(scale_manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
print(f"Wrote scale manifest to {scale_manifest_path}")

# Verify manifest properties
num_q = len(manifest["questions"])
num_runs = len(manifest["schedule"])
print(f"Manifest verification:")
print(f"  Questions: {num_q}")
print(f"  Total system runs: {num_runs}")
print(f"  Total matched pairs: {num_runs // 2}")
assert num_q == 50, f"Expected 50 questions, got {num_q}"
assert num_runs == 200, f"Expected 200 runs, got {num_runs}"

selected_qids = {q["question_id"] for q in manifest["questions"]}
intersection = selected_qids & set(all_exclusions)
assert not intersection, f"FATAL: Overlap with exclusions: {intersection}"
print("  Disjointness verified: 0 questions intersect with any historical benchmark!")
print("RAIR scale manifest successfully prepared and frozen!")

