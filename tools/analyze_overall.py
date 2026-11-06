"""Analyze Phase 2 and Phase 3 combined performance."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def load_results(path):
    runs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("record_type") == "result":
                runs.append(obj)
    return runs

def summarize(runs, label):
    rair = [r for r in runs if r["system"] == "RAIR"]
    kair = [r for r in runs if r["system"] == "KAIR"]
    
    rem = sum(r["evaluation"]["exact_match"] for r in rair)
    kem = sum(r["evaluation"]["exact_match"] for r in kair)
    rf1 = sum(r["evaluation"]["answer_f1"] for r in rair)
    kf1 = sum(r["evaluation"]["answer_f1"] for r in kair)
    
    r_ab = sum(1 for r in rair if r["result"]["prediction"]["abstain"])
    k_ab = sum(1 for r in kair if r["result"]["prediction"]["abstain"])

    r_rec = sum(r["evaluation"]["retrieval_recall"] for r in rair)
    k_rec = sum(r["evaluation"]["retrieval_recall"] for r in kair)

    r_tok = sum(r["result"]["usage"]["prompt_tokens"] for r in rair)
    k_tok = sum(r["result"]["usage"]["prompt_tokens"] for r in kair)

    r_lat = sum(r["result"]["usage"]["elapsed_seconds"] for r in rair)
    k_lat = sum(r["result"]["usage"]["elapsed_seconds"] for r in kair)

    nr = len(rair)
    nk = len(kair)

    r_wins = 0
    k_wins = 0
    ties = 0
    
    # Group by (question_id, seed)
    q_seed_pairs = {}
    for r in rair:
        q_seed_pairs.setdefault((r["question_id"], r["seed"]), {})["RAIR"] = r
    for k in kair:
        q_seed_pairs.setdefault((k["question_id"], k["seed"]), {})["KAIR"] = k

    for (qid, seed), pdict in q_seed_pairs.items():
        if "RAIR" in pdict and "KAIR" in pdict:
            p_rem = pdict["RAIR"]["evaluation"]["exact_match"]
            p_kem = pdict["KAIR"]["evaluation"]["exact_match"]
            if p_rem > p_kem:
                r_wins += 1
            elif p_kem > p_rem:
                k_wins += 1
            else:
                ties += 1

    print(f"=== {label} (Pairs: {nr}) ===")
    print(f"  Exact Match:    RAIR v2 = {rem}/{nr} ({rem/nr:.1%}) | KAIR = {kem}/{nk} ({kem/nk:.1%}) | Delta = {(rem-kem)/nr:+.1%}")
    print(f"  Paired Wins:    RAIR wins = {r_wins} | KAIR wins = {k_wins} | Ties = {ties}")
    print(f"  Answer F1:      RAIR v2 = {rf1/nr:.1%} | KAIR = {kf1/nk:.1%} | Delta = {(rf1-kf1)/nr:+.1%}")
    print(f"  Abstentions:    RAIR v2 = {r_ab}/{nr} ({r_ab/nr:.1%}) | KAIR = {k_ab}/{nk} ({k_ab/nk:.1%})")
    print(f"  Retrieval Rec:  RAIR v2 = {r_rec/nr:.1%} | KAIR = {k_rec/nk:.1%}")
    print(f"  Mean Tokens:    RAIR v2 = {r_tok/nr:.0f} | KAIR = {k_tok/nk:.0f}")
    print(f"  Mean Latency:   RAIR v2 = {r_lat/nr:.1f}s | KAIR = {k_lat/nk:.1f}s")
    print()

def compute_bootstrap(all_runs):
    import random

    # Group runs by question_id and seed
    runs_by_q = {}
    for r in all_runs:
        qid = r["question_id"]
        seed = r["seed"]
        sys_name = r["system"]
        runs_by_q.setdefault(qid, {}).setdefault(seed, {})[sys_name] = r

    q_deltas_em = []
    q_deltas_f1 = []
    q_rair_em = []
    q_kair_em = []
    q_rair_f1 = []
    q_kair_f1 = []

    for qid, seeds in runs_by_q.items():
        seed_diffs_em = []
        seed_diffs_f1 = []
        seed_r_em = []
        seed_k_em = []
        seed_r_f1 = []
        seed_k_f1 = []
        for seed, sys_map in seeds.items():
            if "RAIR" in sys_map and "KAIR" in sys_map:
                rem = sys_map["RAIR"]["evaluation"]["exact_match"]
                kem = sys_map["KAIR"]["evaluation"]["exact_match"]
                rf1 = sys_map["RAIR"]["evaluation"]["answer_f1"]
                kf1 = sys_map["KAIR"]["evaluation"]["answer_f1"]
                seed_diffs_em.append(rem - kem)
                seed_diffs_f1.append(rf1 - kf1)
                seed_r_em.append(rem)
                seed_k_em.append(kem)
                seed_r_f1.append(rf1)
                seed_k_f1.append(kf1)
        if seed_diffs_em:
            q_deltas_em.append(sum(seed_diffs_em) / len(seed_diffs_em))
            q_deltas_f1.append(sum(seed_diffs_f1) / len(seed_diffs_f1))
            q_rair_em.append(sum(seed_r_em) / len(seed_r_em))
            q_kair_em.append(sum(seed_k_em) / len(seed_k_em))
            q_rair_f1.append(sum(seed_r_f1) / len(seed_r_f1))
            q_kair_f1.append(sum(seed_k_f1) / len(seed_k_f1))

    n_q = len(q_deltas_em)
    rng = random.Random(20261103)
    B = 2000
    boot_diff_em = []
    boot_diff_f1 = []
    boot_r_em = []
    boot_k_em = []

    for _ in range(B):
        idx = [rng.randrange(n_q) for _ in range(n_q)]
        boot_diff_em.append(sum(q_deltas_em[i] for i in idx) / n_q)
        boot_diff_f1.append(sum(q_deltas_f1[i] for i in idx) / n_q)
        boot_r_em.append(sum(q_rair_em[i] for i in idx) / n_q)
        boot_k_em.append(sum(q_kair_em[i] for i in idx) / n_q)

    boot_diff_em.sort()
    boot_diff_f1.sort()
    boot_r_em.sort()
    boot_k_em.sort()

    ci_diff_em = (boot_diff_em[int(0.025 * B)], boot_diff_em[int(0.975 * B)])
    ci_diff_f1 = (boot_diff_f1[int(0.025 * B)], boot_diff_f1[int(0.975 * B)])
    ci_r_em = (boot_r_em[int(0.025 * B)], boot_r_em[int(0.975 * B)])
    ci_k_em = (boot_k_em[int(0.025 * B)], boot_k_em[int(0.975 * B)])

    print(f"Bootstrap Uncertainty across {n_q} Disjoint Question Clusters (2000 resamples):")
    print(f"  RAIR v2 EM: {sum(q_rair_em)/n_q:.1%} 95% CI [{ci_r_em[0]:.1%}, {ci_r_em[1]:.1%}]")
    print(f"  KAIR EM:    {sum(q_kair_em)/n_q:.1%} 95% CI [{ci_k_em[0]:.1%}, {ci_k_em[1]:.1%}]")
    print(f"  RAIR - KAIR EM Delta: {sum(q_deltas_em)/n_q:+.1%} 95% CI [{ci_diff_em[0]:+.1%}, {ci_diff_em[1]:+.1%}]")
    print(f"  RAIR - KAIR F1 Delta: {sum(q_deltas_f1)/n_q:+.1%} 95% CI [{ci_diff_f1[0]:+.1%}, {ci_diff_f1[1]:+.1%}]")

def main():
    p2 = load_results(ROOT / "results" / "rair_v2" / "phase2_benchmark.jsonl")
    p3 = load_results(ROOT / "results" / "rair_v2" / "phase3_confirmatory_benchmark.jsonl")

    summarize(p2, "PHASE 2 (10 questions, 2 seeds = 20 pairs / 40 runs)")
    summarize(p3, "PHASE 3 (25 questions, 2 seeds = 50 pairs / 100 runs)")
    summarize(p2 + p3, "COMBINED POOLED (35 questions, 2 seeds = 70 pairs / 140 runs)")
    compute_bootstrap(p2 + p3)

if __name__ == "__main__":
    main()
