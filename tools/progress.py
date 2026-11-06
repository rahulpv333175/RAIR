import json
from pathlib import Path

def main():
    p = Path("results/rair_v2/phase3_confirmatory_benchmark.jsonl")
    if not p.exists():
        print("File does not exist yet.")
        return
    lines = p.read_text(encoding="utf-8").strip().split("\n")
    runs = []
    for l in lines:
        if not l.strip():
            continue
        obj = json.loads(l)
        if obj.get("record_type") == "result":
            runs.append(obj)

    rair = [r for r in runs if r.get("system") == "RAIR"]
    kair = [r for r in runs if r.get("system") == "KAIR"]

    rem = sum(r["evaluation"]["exact_match"] for r in rair)
    kem = sum(r["evaluation"]["exact_match"] for r in kair)
    rf1 = sum(r["evaluation"]["answer_f1"] for r in rair)
    kf1 = sum(r["evaluation"]["answer_f1"] for r in kair)

    n_r = max(1, len(rair))
    n_k = max(1, len(kair))

    print(f"Total evaluated runs: {len(runs)}/100 (RAIR={len(rair)}, KAIR={len(kair)})")
    print(f"RAIR: EM={rem}/{len(rair)} ({rem/n_r:.1%}), F1={rf1/n_r:.1%}")
    print(f"KAIR: EM={kem}/{len(kair)} ({kem/n_k:.1%}), F1={kf1/n_k:.1%}")

if __name__ == "__main__":
    main()

