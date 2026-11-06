import json
from pathlib import Path
from collections import Counter

raw_path = Path("data/raw/hotpot_dev_distractor_v1.json")
with open(raw_path, "r", encoding="utf-8") as f:
    gold_by_id = {q["_id"]: q for q in json.load(f)}

path = Path("results/rair_scale/rair_scale_benchmark.jsonl")
rair_absts = []

with open(path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("record_type") == "result" and r.get("system") == "RAIR":
            if r["result"]["status"] == "abstained":
                qid = r["question_id"]
                seed = r["seed"]
                stop = r["result"]["stop_reason"]
                calls = r["result"]["usage"]["llm_calls"]
                ret = r["result"]["usage"]["retrieval_calls"]
                q = r["result"]["question"]
                gold = gold_by_id.get(qid, {}).get("answer")
                rair_absts.append({
                    "qid": qid,
                    "seed": seed,
                    "stop": stop,
                    "calls": calls,
                    "ret": ret,
                    "q": q,
                    "gold": gold,
                    "trace": r["result"].get("trace", [])
                })

print(f"Total RAIR abstentions in Scale: {len(rair_absts)}/100")
print("Stop reasons:", Counter(x["stop"] for x in rair_absts))
print("\nSample of abstentions:")
for a in rair_absts[:10]:
    print(f"[{a['qid'][:8]} s={a['seed']}] stop={a['stop']} calls={a['calls']} ret={a['ret']} | Gold: '{a['gold']}' | Q: {a['q']}")

