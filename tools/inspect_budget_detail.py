import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    p3 = [json.loads(l) for l in (ROOT / "results/rair_v2/phase3_confirmatory_benchmark.jsonl").read_text(encoding="utf-8").split("\n") if l.startswith('{"record_type": "result"')]
    for r in p3:
        if r["system"] == "RAIR" and r["result"]["stop_reason"] == "budget_exhausted":
            qid = r["question_id"]
            seed = r["seed"]
            status = r["result"]["status"]
            pred = r["result"]["prediction"]
            err = r["result"]["error"]
            print(f"QID: {qid} (Seed {seed}) | Status: {status} | Error: {err}")
            print(f"  Prediction: {pred}")

if __name__ == "__main__":
    main()

