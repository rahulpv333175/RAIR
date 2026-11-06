import json

for path in ['results/rair_v2/phase2_benchmark_v2.jsonl', 'results/rair_v2/phase3_confirmatory_benchmark.jsonl']:
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            if row.get('record_type') == 'result' and row.get('question_id') in ['5adf4ba65542992d7e9f931c', '5ac397fe554299218029dbe2'] and row.get('system') == 'RAIR':
                print("====================================")
                print("Found in", path)
                print("QID:", row['question_id'], "Seed:", row.get('seed'))
                res = row.get('result', {})
                print("Status:", res.get('status'), "Stop:", res.get('stop_reason'))
                print("Verified facts:", len(res.get('state', {}).get('verified_facts', [])))
                for f_item in res.get('state', {}).get('verified_facts', []):
                    print("  Fact:", f_item.get('statement'))
                print("Gaps:")
                for g in res.get('state', {}).get('gaps', []):
                    print(f"  {g['gap_id']} (resolved={g['resolved']}): {g['description']}")
                print("Error:", res.get('error'))
                print("LLM calls:", len(res.get('llm_calls', [])))
                print("Rounds:", len(res.get('rounds', [])))
                for r in res.get('rounds', []):
                    print(f"  R{r['round_number']} ({r['gap_id']}): q='{r['query']}'")
