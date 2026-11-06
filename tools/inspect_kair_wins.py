import json

paths = [
    'results/rair_v2/phase2_benchmark_v2.jsonl',
    'results/rair_v2/phase3_confirmatory_benchmark.jsonl',
]

for path in paths:
    print(f"=== {path} ===")
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            if row.get('status') == 'completed':
                q_id = row['question_id']
                rair = row['rair']
                kair = row['kair']
                if kair['metrics']['exact_match'] > rair['metrics']['exact_match']:
                    vf = len(rair.get('state', {}).get('verified_facts', []))
                    unres = len(rair.get('state', {}).get('unresolved_gaps', []))
                    print(f"Q: {q_id} | stop: {rair['stop_reason']} | status: {rair['status']} | facts: {vf} | unres: {unres} | rair: '{rair['prediction']['answer']}' | gold: '{row['gold']['answer']}' | kair: '{kair['prediction']['answer']}'")
