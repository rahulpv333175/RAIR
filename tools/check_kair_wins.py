import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    p2 = [json.loads(l) for l in (ROOT / "results/rair_v2/phase2_benchmark.jsonl").read_text(encoding="utf-8").split("\n") if l.startswith('{"record_type": "result"')]
    p3 = [json.loads(l) for l in (ROOT / "results/rair_v2/phase3_confirmatory_benchmark.jsonl").read_text(encoding="utf-8").split("\n") if l.startswith('{"record_type": "result"')]
    runs = p2 + p3
    pairs = {}
    for r in runs:
        pairs.setdefault((r["question_id"], r["seed"]), {})[r["system"]] = r

    kair_wins = []
    for (qid, seed), sys_map in pairs.items():
        rem = sys_map["RAIR"]["evaluation"]["exact_match"]
        kem = sys_map["KAIR"]["evaluation"]["exact_match"]
        if kem > rem:
            kair_wins.append((
                qid, seed,
                sys_map["RAIR"]["result"]["status"],
                sys_map["RAIR"]["result"]["stop_reason"],
                sys_map["RAIR"]["result"]["prediction"]["answer"],
                sys_map["KAIR"]["result"]["prediction"]["answer"]
            ))

    print(f"Total KAIR wins across all 70 pairs: {len(kair_wins)}")
    for w in kair_wins:
        print(f"  QID: {w[0]} (Seed {w[1]}) | RAIR status: {w[2]} | stop: {w[3]}")
        print(f"    RAIR ans: {repr(w[4])} | KAIR ans: {repr(w[5])}")

if __name__ == "__main__":
    main()

