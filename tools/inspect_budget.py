import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    p3 = [json.loads(l) for l in (ROOT / "results/rair_v2/phase3_confirmatory_benchmark.jsonl").read_text(encoding="utf-8").split("\n") if l.startswith('{"record_type": "result"')]
    for r in p3:
        if r["system"] == "RAIR" and r["result"]["stop_reason"] == "budget_exhausted":
            qid = r["question_id"]
            calls = r["result"]["usage"]["llm_calls"]
            rets = r["result"]["usage"]["retrieval_calls"]
            rounds = len(r["result"]["rounds"])
            unresolved = [g["description"] for g in r["result"]["state"]["gaps"] if not g["resolved"]]
            resolved = [g["description"] for g in r["result"]["state"]["gaps"] if g["resolved"]]
            facts = [f["statement"] for f in r["result"]["state"]["verified_facts"]]
            print(f"QID: {qid} (Seed {r['seed']}) | Calls: {calls} | Rets: {rets} | Rounds: {rounds}")
            print(f"  Facts in memory ({len(facts)}): {facts}")
            print(f"  Resolved gaps ({len(resolved)}): {resolved}")
            print(f"  Unresolved gaps ({len(unresolved)}): {unresolved}")
            print()

if __name__ == "__main__":
    main()

