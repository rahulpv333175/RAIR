import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

benchmarks = [
    ("Step 10 Confirmation", ROOT / "results/step10_benchmark.summary.json"),
    ("RAIR v2 Phase 2", ROOT / "results/rair_v2/phase2_benchmark.summary.json"),
    ("RAIR v2 Phase 3", ROOT / "results/rair_v2/phase3_confirmatory_benchmark.summary.json"),
    ("RAIR v3 Upgrade", ROOT / "results/rair_v3/rair_v3_benchmark.summary.json"),
    ("RAIR Scale", ROOT / "results/rair_scale/rair_scale_benchmark.summary.json"),
]

print("=== PROJECT BENCHMARK SUMMARY ===")
for name, p in benchmarks:
    if not p.exists():
        print(f"[{name}]: Pending / running")
        continue
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    r = data["systems"]["RAIR"]
    k = data["systems"]["KAIR"]
    pairs = len(data.get("pairs", []))
    print(f"\n--- {name} ({pairs} pairs / {pairs*2} runs) ---")
    print(f"  Exact Match:        RAIR={r['metrics']['exact_match']*100:.1f}%  |  KAIR={k['metrics']['exact_match']*100:.1f}%  |  Delta={ (r['metrics']['exact_match'] - k['metrics']['exact_match'])*100:+.1f} pp")
    print(f"  Retrieval Recall:   RAIR={r['metrics']['retrieval_recall']*100:.1f}%  |  KAIR={k['metrics']['retrieval_recall']*100:.1f}%  |  Delta={ (r['metrics']['retrieval_recall'] - k['metrics']['retrieval_recall'])*100:+.1f} pp")
    print(f"  Answer F1:          RAIR={r['metrics']['answer_f1']*100:.1f}%  |  KAIR={k['metrics']['answer_f1']*100:.1f}%  |  Delta={ (r['metrics']['answer_f1'] - k['metrics']['answer_f1'])*100:+.1f} pp")
    print(f"  Coverage:           RAIR={r['coverage']*100:.1f}%  |  KAIR={k['coverage']*100:.1f}%  |  Delta={ (r['coverage'] - k['coverage'])*100:+.1f} pp")
    print(f"  Mean Latency:       RAIR={r['mean_usage']['elapsed_seconds']:.1f}s  |  KAIR={k['mean_usage']['elapsed_seconds']:.1f}s  |  Speedup={(1 - r['mean_usage']['elapsed_seconds']/k['mean_usage']['elapsed_seconds'])*100:.1f}%")

