import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def load_journal_results(path):
    results = []
    if not path.exists():
        return results
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                if obj.get("record_type") == "result":
                    results.append(obj)
            except Exception:
                continue
    return results

files = [
    ("Phase 2", ROOT / "results/rair_v2/phase2_benchmark.jsonl"),
    ("Phase 3", ROOT / "results/rair_v2/phase3_confirmatory_benchmark.jsonl"),
    ("RAIR v3", ROOT / "results/rair_v3/rair_v3_benchmark.jsonl"),
    ("Scale (100 pairs)", ROOT / "results/rair_scale/rair_scale_benchmark.jsonl"),
    ("Test (100 pairs)", ROOT / "results/rair_test/rair_test_benchmark.jsonl"),
]

all_rair = []
all_kair = []

print(f"{'Cohort':<18} | {'Pairs':<6} | {'RAIR EM':<8} | {'KAIR EM':<8} | {'RAIR Rec':<9} | {'KAIR Rec':<9}")
print("-" * 75)

for name, path in files:
    runs = load_journal_results(path)
    r_runs = [r for r in runs if r.get("system") == "RAIR"]
    k_runs = [r for r in runs if r.get("system") == "KAIR"]
    all_rair.extend(r_runs)
    all_kair.extend(k_runs)
    
    r_em = sum(r["evaluation"]["exact_match"] for r in r_runs) / len(r_runs) if r_runs else 0
    k_em = sum(r["evaluation"]["exact_match"] for r in k_runs) / len(k_runs) if k_runs else 0
    r_rec = sum(r["evaluation"]["retrieval_recall"] for r in r_runs) / len(r_runs) if r_runs else 0
    k_rec = sum(r["evaluation"]["retrieval_recall"] for r in k_runs) / len(k_runs) if k_runs else 0
    pairs = min(len(r_runs), len(k_runs))
    print(f"{name:<18} | {pairs:<6} | {r_em*100:>6.1f}%  | {k_em*100:>6.1f}%  | {r_rec*100:>7.1f}%  | {k_rec*100:>7.1f}%")

print("=" * 75)
p_r_em = sum(r["evaluation"]["exact_match"] for r in all_rair) / len(all_rair) if all_rair else 0
p_k_em = sum(r["evaluation"]["exact_match"] for r in all_kair) / len(all_kair) if all_kair else 0
p_r_rec = sum(r["evaluation"]["retrieval_recall"] for r in all_rair) / len(all_rair) if all_rair else 0
p_k_rec = sum(r["evaluation"]["retrieval_recall"] for r in all_kair) / len(all_kair) if all_kair else 0
p_r_f1 = sum(r["evaluation"]["answer_f1"] for r in all_rair) / len(all_rair) if all_rair else 0
p_k_f1 = sum(r["evaluation"]["answer_f1"] for r in all_kair) / len(all_kair) if all_kair else 0
p_pairs = min(len(all_rair), len(all_kair))

print(f"{'GRAND POOLED':<18} | {p_pairs:<6} | {p_r_em*100:>6.1f}%  | {p_k_em*100:>6.1f}%  | {p_r_rec*100:>7.1f}%  | {p_k_rec*100:>7.1f}%")
print(f"Total Runs: {len(all_rair) + len(all_kair)} ({p_pairs} matched pairs)")
print(f"Grand Pooled Retrieval Recall Lead for RAIR: {(p_r_rec - p_k_rec)*100:+.2f} pp")
print(f"Grand Pooled Answer F1: RAIR {p_r_f1*100:.1f}% vs KAIR {p_k_f1*100:.1f}% (Delta: {(p_r_f1 - p_k_f1)*100:+.2f} pp)")
print(f"Grand Pooled Exact Match: RAIR {p_r_em*100:.1f}% vs KAIR {p_k_em*100:.1f}% (Delta: {(p_r_em - p_k_em)*100:+.2f} pp)")

