import json

path = "results/rair_v3/rair_v3_benchmark.jsonl"
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("record_type") == "result":
            sys = row.get("system")
            qid = row.get("question_id")
            seed = row.get("seed")
            pred = row.get("result", {}).get("prediction", {}).get("answer")
            stop = row.get("result", {}).get("stop_reason")
            em = row.get("evaluation", {}).get("exact_match")
            f1 = row.get("evaluation", {}).get("answer_f1")
            q = row.get("result", {}).get("question")
            print(f"[{sys}] seed={seed} EM={em} F1={f1:.2f} stop={stop} | ans: '{pred}' | Q: {q[:60]}...")

