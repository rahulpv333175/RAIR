import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

raw_path = ROOT / "data/raw/hotpot_dev_distractor_v1.json"
with open(raw_path, "r", encoding="utf-8") as f:
    gold_by_id = {q["_id"]: q for q in json.load(f)}

path = ROOT / "results/rair_scale/rair_scale_benchmark.jsonl"
runs_by_pair = {}

with open(path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("record_type") == "result":
            key = (r["question_id"], r["seed"])
            runs_by_pair.setdefault(key, {})[r["system"]] = r

completed_pairs = {k: v for k, v in runs_by_pair.items() if "RAIR" in v and "KAIR" in v}
print(f"Total fully completed matched pairs: {len(completed_pairs)}")

rair_wins = []
kair_wins = []
both_correct = []
both_wrong = []

for (qid, seed), pair in completed_pairs.items():
    r = pair["RAIR"]
    k = pair["KAIR"]
    r_em = r["evaluation"]["exact_match"]
    k_em = k["evaluation"]["exact_match"]
    r_f1 = r["evaluation"]["answer_f1"]
    k_f1 = k["evaluation"]["answer_f1"]
    r_ans = r["result"]["prediction"]["answer"] or f"[{r['result']['status']}]"
    k_ans = k["result"]["prediction"]["answer"] or f"[{k['result']['status']}]"
    gold = gold_by_id.get(qid, {}).get("answer", "Unknown")
    q = r["result"]["question"]
    
    item = {
        "qid": qid,
        "seed": seed,
        "question": q,
        "gold": gold,
        "r_ans": r_ans,
        "k_ans": k_ans,
        "r_em": r_em,
        "k_em": k_em,
        "r_f1": r_f1,
        "k_f1": k_f1,
        "r_rec": r["evaluation"]["retrieval_recall"],
        "k_rec": k["evaluation"]["retrieval_recall"],
        "r_stop": r["result"]["stop_reason"],
        "k_stop": k["result"]["stop_reason"],
    }
    
    if r_em > k_em:
        rair_wins.append(item)
    elif k_em > r_em:
        kair_wins.append(item)
    elif r_em == 1.0:
        both_correct.append(item)
    else:
        both_wrong.append(item)

print(f"\nHead-to-Head Tally ({len(completed_pairs)} pairs):")
print(f"  RAIR Wins:     {len(rair_wins)} ({len(rair_wins)/len(completed_pairs)*100:.1f}%)")
print(f"  KAIR Wins:     {len(kair_wins)} ({len(kair_wins)/len(completed_pairs)*100:.1f}%)")
print(f"  Both Correct:  {len(both_correct)} ({len(both_correct)/len(completed_pairs)*100:.1f}%)")
print(f"  Both Wrong:    {len(both_wrong)} ({len(both_wrong)/len(completed_pairs)*100:.1f}%)")

print("\n--- RAIR WINS SAMPLE ---")
for w in rair_wins[:5]:
    print(f"[{w['qid'][:8]} s={w['seed']}] Q: {w['question']}")
    print(f"  Gold: {w['gold']}")
    print(f"  RAIR: '{w['r_ans']}' (EM={w['r_em']})")
    print(f"  KAIR: '{w['k_ans']}' (EM={w['k_em']})")

print("\n--- KAIR WINS SAMPLE ---")
for w in kair_wins[:5]:
    print(f"[{w['qid'][:8]} s={w['seed']}] Q: {w['question']}")
    print(f"  Gold: {w['gold']}")
    print(f"  RAIR: '{w['r_ans']}' (EM={w['r_em']}, F1={w['r_f1']:.2f}, stop={w['r_stop']})")
    print(f"  KAIR: '{w['k_ans']}' (EM={w['k_em']}, F1={w['k_f1']:.2f}, stop={w['k_stop']})")

print("\n--- BOTH WRONG BUT NON-ZERO F1 / SEMANTIC SAMPLE ---")
for w in [x for x in both_wrong if x['r_f1'] > 0 or x['k_f1'] > 0][:5]:
    print(f"[{w['qid'][:8]} s={w['seed']}] Q: {w['question']}")
    print(f"  Gold: {w['gold']}")
    print(f"  RAIR: '{w['r_ans']}' (F1={w['r_f1']:.2f})")
    print(f"  KAIR: '{w['k_ans']}' (F1={w['k_f1']:.2f})")

