import json
from pathlib import Path
from collections import Counter

raw_path = Path("data/raw/hotpot_dev_distractor_v1.json")
with open(raw_path, "r", encoding="utf-8") as f:
    gold_by_id = {q["_id"]: q for q in json.load(f)}

path = Path("results/rair_scale/rair_scale_benchmark.jsonl")
misses = []
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("record_type") == "result" and r.get("system") == "RAIR":
            em = r["evaluation"]["exact_match"]
            if em < 1.0:
                qid = r["question_id"]
                seed = r["seed"]
                ans = r["result"]["prediction"]["answer"]
                gold = gold_by_id.get(qid, {}).get("answer")
                stop = r["result"]["stop_reason"]
                f1 = r["evaluation"]["answer_f1"]
                rec = r["evaluation"]["retrieval_recall"]
                misses.append({
                    "qid": qid,
                    "seed": seed,
                    "question": r["result"]["question"],
                    "ans": ans,
                    "gold": gold,
                    "stop": stop,
                    "f1": f1,
                    "rec": rec,
                    "facts": [f["statement"] for f in r["result"]["state"]["verified_facts"]]
                })

print(f"Total RAIR non-exact runs in scale: {len(misses)}/100")
print("Stop reasons:", Counter(m["stop"] for m in misses))

# Categorize:
abstained = [m for m in misses if not m["ans"]]
answered_partial = [m for m in misses if m["ans"] and m["f1"] > 0]
answered_zero_f1 = [m for m in misses if m["ans"] and m["f1"] == 0]

print(f"  Abstained: {len(abstained)}")
print(f"  Answered partial (F1 > 0): {len(answered_partial)}")
print(f"  Answered wrong (F1 == 0): {len(answered_zero_f1)}")

print("\n--- SAMPLE ANSWERED PARTIAL (F1 > 0) ---")
for m in answered_partial[:8]:
    print(f"[{m['qid'][:8]}] Pred: '{m['ans']}' | Gold: '{m['gold']}' | F1: {m['f1']:.2f} | Q: {m['question'][:70]}")

print("\n--- SAMPLE ANSWERED WRONG (F1 == 0) WITH HIGH RETRIEVAL RECALL ---")
high_rec = [m for m in answered_zero_f1 if m["rec"] == 1.0]
for m in high_rec[:8]:
    print(f"[{m['qid'][:8]}] Pred: '{m['ans']}' | Gold: '{m['gold']}' | Q: {m['question'][:70]}")
    print(f"   Facts: {m['facts'][:2]}")

