import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.evaluation.paired import prepare_manifest

# Exclude all prior questions:
# 1. exclusions from scale settings
# 2. questions from scale manifest
with open(ROOT / "config" / "rair_scale_settings.json", "r", encoding="utf-8") as f:
    scale_settings = json.load(f)

with open(ROOT / "config" / "rair_scale_manifest.json", "r", encoding="utf-8") as f:
    scale_manifest = json.load(f)

scale_qids = [q["question_id"] for q in scale_manifest["questions"]]
all_exclusions = sorted(list(set(scale_settings["evaluation"]["exclude_question_ids"]) | set(scale_qids)))
print(f"Total exclusions for Fresh Test Benchmark: {len(all_exclusions)} questions.")

test_settings = copy.deepcopy(scale_settings)
test_settings["project"]["name"] = "RAIR Extended Test Benchmark (200 Runs)"
test_settings["evaluation"]["name"] = "RAIR Test Set Evaluation vs Unchanged KAIR"
test_settings["evaluation"]["purpose"] = (
    "Final held-out test evaluation of RAIR v4 against unchanged competitive KAIR across "
    "50 strictly fresh, untouched HotpotQA test questions and 2 seeds (100 matched pairs / 200 runs) "
    "under strict protocol parity (RunBudget(4, 18), BM25 top-3 pools, identical environment)."
)
test_settings["evaluation"]["sample_size"] = 50
test_settings["evaluation"]["sample_seed"] = 20261106
test_settings["evaluation"]["seeds"] = [42, 43]
test_settings["evaluation"]["exclude_question_ids"] = all_exclusions
test_settings["evaluation"]["bootstrap_seed"] = 20261106

test_settings_path = ROOT / "config" / "rair_test_settings.json"
with open(test_settings_path, "w", encoding="utf-8") as f:
    json.dump(test_settings, f, indent=2, ensure_ascii=False)
print(f"Wrote test settings to {test_settings_path}")

manifest = prepare_manifest(test_settings)
test_manifest_path = ROOT / "config" / "rair_test_manifest.json"
with open(test_manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
print(f"Wrote test manifest to {test_manifest_path}")

num_q = len(manifest["questions"])
num_runs = len(manifest["schedule"])
print(f"Manifest Verification:")
print(f"  Questions: {num_q}")
print(f"  Runs: {num_runs}")
assert num_q == 50, f"Expected 50 questions, got {num_q}"
assert num_runs == 200, f"Expected 200 runs, got {num_runs}"

# Verify zero overlap with prior exclusions
new_qids = {q["question_id"] for q in manifest["questions"]}
overlap = new_qids & set(all_exclusions)
assert len(overlap) == 0, f"Overlap detected: {overlap}"
print("VERIFICATION SUCCESS: Zero overlap with all 455 prior evaluation questions!")

