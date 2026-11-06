import json
from pathlib import Path

path = Path("results/rair_v3/rair_v3_benchmark.jsonl")
if not path.exists():
    print("Benchmark jsonl does not exist yet.")
else:
    count = 0
    rair_count = 0
    kair_count = 0
    rair_em = 0
    kair_em = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("record_type") == "result":
                count += 1
                sys = row.get("system")
                em = row.get("evaluation", {}).get("exact_match", 0)
                if sys == "RAIR":
                    rair_count += 1
                    rair_em += em
                elif sys == "KAIR":
                    kair_count += 1
                    kair_em += em
    print(f"Total runs completed: {count}/100")
    if rair_count:
        print(f"RAIR runs: {rair_count} | EM: {rair_em}/{rair_count} ({rair_em/rair_count*100:.1f}%)")
    if kair_count:
        print(f"KAIR runs: {kair_count} | EM: {kair_em}/{kair_count} ({kair_em/kair_count*100:.1f}%)")

