import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.evaluation.paired import prepare_manifest

# Load Phase 3 settings as base
with open(ROOT / "config" / "rair_v2_phase3_settings.json", "r", encoding="utf-8") as f:
    p3_settings = json.load(f)

# Collect all exclusions:
# 1. exclusions from Phase 3 settings
# 2. questions in Phase 3 manifest
with open(ROOT / "config" / "rair_v2_phase3_manifest.json", "r", encoding="utf-8") as f:
    p3_manifest = json.load(f)

p3_qids = [q["question_id"] for q in p3_manifest["questions"]]
all_exclusions = sorted(list(set(p3_settings["evaluation"]["exclude_question_ids"]) | set(p3_qids)))
print(f"Total exclusions for RAIR v3: {len(all_exclusions)} (355 historical + 25 Phase 3 = {len(all_exclusions)})")

v3_settings = copy.deepcopy(p3_settings)
v3_settings["project"]["name"] = "RAIR v3 vs KAIR Confirmatory Benchmark"
v3_settings["evaluation"]["name"] = "RAIR v3 Confirmatory Evaluation vs Unchanged KAIR"
v3_settings["evaluation"]["purpose"] = (
    "Empirical superiority benchmark of RAIR v3 against unchanged competitive KAIR across "
    "25 strictly disjoint HotpotQA questions and 2 seeds (50 matched pairs / 100 system runs) "
    "under strict protocol parity (RunBudget(4, 18), BM25 top-3 pools, identical environment)."
)
v3_settings["evaluation"]["sample_size"] = 25
v3_settings["evaluation"]["sample_seed"] = 20261104
v3_settings["evaluation"]["seeds"] = [42, 43]
v3_settings["evaluation"]["exclude_question_ids"] = all_exclusions
v3_settings["evaluation"]["bootstrap_seed"] = 20261104

v3_settings_path = ROOT / "config" / "rair_v3_settings.json"
with open(v3_settings_path, "w", encoding="utf-8") as f:
    json.dump(v3_settings, f, indent=2, ensure_ascii=False)
print(f"Wrote v3 settings to {v3_settings_path}")

# Build manifest using prepare_manifest
manifest = prepare_manifest(v3_settings)
v3_manifest_path = ROOT / "config" / "rair_v3_manifest.json"
with open(v3_manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
print(f"Wrote v3 manifest to {v3_manifest_path}")

# Verify manifest properties
num_q = len(manifest["questions"])
num_runs = len(manifest["schedule"])
print(f"Manifest verification:")
print(f"  Questions: {num_q}")
print(f"  Total system runs: {num_runs}")
print(f"  Total matched pairs: {num_runs // 2}")
assert num_q == 25, f"Expected 25 questions, got {num_q}"
assert num_runs == 100, f"Expected 100 runs, got {num_runs}"

selected_qids = {q["question_id"] for q in manifest["questions"]}
intersection = selected_qids & set(all_exclusions)
assert not intersection, f"FATAL: Overlap with exclusions: {intersection}"
print("  Disjointness verified: 0 questions intersect with any historical benchmark!")
print("RAIR v3 manifest successfully prepared and frozen!")

