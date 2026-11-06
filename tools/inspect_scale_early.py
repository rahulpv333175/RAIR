import json
from pathlib import Path

raw_path = Path("data/raw/hotpot_dev_distractor_v1.json")
raw_data = {}
if raw_path.exists():
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = {q["_id"]: q for q in json.load(f)}

path = Path("results/rair_scale/rair_scale_benchmark.jsonl")
if path.exists():
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("record_type") == "result":
            sys = r.get("system")
            em = r.get("evaluation", {}).get("exact_match")
            f1 = r.get("evaluation", {}).get("answer_f1")
            status = r.get("result", {}).get("status")
            stop = r.get("result", {}).get("stop_reason")
            ans = r.get("result", {}).get("prediction", {}).get("answer")
            qid = r.get("question_id")
            gold = raw_data.get(qid, {}).get("answer", "Unknown")
            q = r.get("result", {}).get("question")
            print(f"[{sys}] qid={qid[:8]} status={status} stop={stop} EM={em} F1={f1:.2f} | pred: '{ans}' | gold: '{gold}'")
