import json
from pathlib import Path

path = Path("results/rair_scale/rair_scale_benchmark.jsonl")
if not path.exists():
    print("Benchmark jsonl does not exist yet.")
else:
    count = 0
    rair_count = 0
    kair_count = 0
    rair_em = 0
    kair_em = 0
    rair_f1 = 0
    kair_f1 = 0
    rair_rec = 0
    kair_rec = 0
    rair_prec = 0
    kair_prec = 0
    rair_abst = 0
    kair_abst = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("record_type") == "result":
                count += 1
                sys = row.get("system")
                ev = row.get("evaluation", {})
                em = ev.get("exact_match", 0)
                f1 = ev.get("answer_f1", 0)
                rec = ev.get("retrieval_recall", 0)
                prec = ev.get("retrieval_precision", 0)
                status = row.get("result", {}).get("status")
                if sys == "RAIR":
                    rair_count += 1
                    rair_em += em
                    rair_f1 += f1
                    rair_rec += rec
                    rair_prec += prec
                    if status == "abstained":
                        rair_abst += 1
                elif sys == "KAIR":
                    kair_count += 1
                    kair_em += em
                    kair_f1 += f1
                    kair_rec += rec
                    kair_prec += prec
                    if status == "abstained":
                        kair_abst += 1

    print(f"Total runs completed: {count}/200 ({count/200*100:.1f}%)")
    if rair_count:
        print(f"RAIR ({rair_count} runs): EM={rair_em/rair_count*100:.1f}%, F1={rair_f1/rair_count*100:.1f}%, Rec={rair_rec/rair_count*100:.1f}%, Prec={rair_prec/rair_count*100:.1f}%, Abst={rair_abst}/{rair_count}")
    if kair_count:
        print(f"KAIR ({kair_count} runs): EM={kair_em/kair_count*100:.1f}%, F1={kair_f1/kair_count*100:.1f}%, Rec={kair_rec/kair_count*100:.1f}%, Prec={kair_prec/kair_count*100:.1f}%, Abst={kair_abst}/{kair_count}")

