"""Prepare RAIR v2 Phase 3 settings and frozen paired manifest."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.experiments.compare import prepare_manifest

def main():
    p2_settings_path = ROOT / "config" / "rair_v2_phase2_settings.json"
    p2_manifest_path = ROOT / "config" / "rair_v2_phase2_manifest.json"
    p3_settings_path = ROOT / "config" / "rair_v2_phase3_settings.json"
    p3_manifest_path = ROOT / "config" / "rair_v2_phase3_manifest.json"

    with open(p2_settings_path, "r", encoding="utf-8") as f:
        p2_settings = json.load(f)
    with open(p2_manifest_path, "r", encoding="utf-8") as f:
        p2_manifest = json.load(f)

    # Gather exclusions: existing 345 exclusions + 10 Phase 2 questions
    p2_qids = [q["question_id"] for q in p2_manifest["questions"]]
    all_exclusions = sorted(list(set(p2_settings["evaluation"]["exclude_question_ids"]) | set(p2_qids)))
    print(f"Total exclusions for Phase 3: {len(all_exclusions)} (345 prior + {len(p2_qids)} Phase 2)")

    p3_settings = copy.deepcopy(p2_settings)
    p3_settings["project"]["name"] = "RAIR v2 vs KAIR Phase 3 Confirmatory Evaluation"
    p3_settings["evaluation"]["name"] = "RAIR v2 Phase 3: Confirmatory Evaluation vs Unchanged KAIR"
    p3_settings["evaluation"]["purpose"] = (
        "Confirmatory evaluation of frozen RAIR v2 against unchanged competitive KAIR across "
        "25 disjoint questions and 2 seeds (50 matched pairs / 100 system runs) under identical "
        "4/18 budget and BM25 top-3 per-question pools."
    )
    p3_settings["evaluation"]["sample_size"] = 25
    p3_settings["evaluation"]["sample_seed"] = 20261103
    p3_settings["evaluation"]["seeds"] = [42, 43]
    p3_settings["evaluation"]["exclude_question_ids"] = all_exclusions
    p3_settings["evaluation"]["bootstrap_seed"] = 20261103

    with open(p3_settings_path, "w", encoding="utf-8") as f:
        json.dump(p3_settings, f, indent=2, ensure_ascii=False)
    print(f"Wrote settings to {p3_settings_path}")

    # Build manifest
    manifest = prepare_manifest(p3_settings)
    with open(p3_manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"Wrote manifest to {p3_manifest_path}")

    # Verify manifest
    num_q = len(manifest["questions"])
    num_runs = len(manifest["schedule"])
    print(f"Manifest verification:")
    print(f"  Questions: {num_q}")
    print(f"  Total system runs: {num_runs}")
    print(f"  Total matched pairs: {num_runs // 2}")
    assert num_q == 25, f"Expected 25 questions, got {num_q}"
    assert num_runs == 100, f"Expected 100 runs, got {num_runs}"

    # Verify complete disjointness from exclusions
    selected_qids = {q["question_id"] for q in manifest["questions"]}
    intersection = selected_qids & set(all_exclusions)
    assert not intersection, f"Selected questions intersect with exclusions: {intersection}"
    print("  Disjointness verified: 0 questions intersect with historical exclusions or Phase 2.")
    print("Phase 3 setup SUCCESSFUL!")

if __name__ == "__main__":
    main()
