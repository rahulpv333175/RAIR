import json
from pathlib import Path

path = Path("results/rair_scale/rair_scale_benchmark.jsonl")
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("record_type") == "result" and r.get("system") == "RAIR":
            if r["question_id"].startswith("5a7e04b0") and r["seed"] == 42:
                res = r["result"]
                print("KEYS:", list(res.keys()))
                for k in ["question", "status", "stop_reason", "prediction", "state", "history"]:
                    if k in res:
                        print(f"--- {k} ---")
                        print(json.dumps(res[k], indent=2))
                break
