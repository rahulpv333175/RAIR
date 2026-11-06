import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    p2 = [json.loads(l) for l in (ROOT / "results/rair_v2/phase2_benchmark.jsonl").read_text(encoding="utf-8").split("\n") if l.startswith('{"record_type": "result"')]
    p3 = [json.loads(l) for l in (ROOT / "results/rair_v2/phase3_confirmatory_benchmark.jsonl").read_text(encoding="utf-8").split("\n") if l.startswith('{"record_type": "result"')]
    raw_data = json.loads((ROOT / "data/raw/hotpot_dev_distractor_v1.json").read_text(encoding="utf-8"))
    examples = {e["_id"]: e for e in raw_data}

    for label, runs in [("Phase 2", p2), ("Phase 3", p3)]:
        print(f"=== {label} RAIR non-exact answers ===")
        for r in runs:
            if r["system"] == "RAIR" and r["evaluation"]["exact_match"] == 0:
                qid = r["question_id"]
                gold = examples[qid]["answer"]
                pred = r["result"]["prediction"]["answer"]
                status = r["result"]["status"]
                stop = r["result"]["stop_reason"]
                f1 = r["evaluation"]["answer_f1"]
                print(f"  QID: {qid} (Seed {r['seed']}) | Status: {status} | Stop: {stop}")
                print(f"    Gold: '{gold}'")
                print(f"    Pred: '{pred}' (F1={f1:.2f})")

if __name__ == "__main__":
    main()

