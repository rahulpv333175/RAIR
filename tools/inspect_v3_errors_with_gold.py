import json

raw_path = "data/raw/hotpot_dev_distractor_v1.json"
with open(raw_path, "r", encoding="utf-8") as f:
    raw_data = json.load(f)
gold_by_id = {q["_id"]: q for q in raw_data}

path = "results/rair_v3/rair_v3_benchmark.jsonl"
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        row = json.loads(line)
        if row.get("record_type") == "result" and row.get("system") == "RAIR":
            em = row.get("evaluation", {}).get("exact_match", 0)
            if em < 1.0:
                qid = row["question_id"]
                seed = row["seed"]
                pred = row["result"]["prediction"]["answer"]
                stop = row["result"]["stop_reason"]
                q_obj = gold_by_id.get(qid, {})
                gold_ans = q_obj.get("answer", "")
                q_text = q_obj.get("question", "")
                f1 = row.get("evaluation", {}).get("answer_f1", 0)
                print(f"[{qid[:10]}] seed={seed} F1={f1:.2f} stop={stop}")
                print(f"  Q:    {q_text}")
                print(f"  Pred: '{pred}'")
                print(f"  Gold: '{gold_ans}'")
                print()

