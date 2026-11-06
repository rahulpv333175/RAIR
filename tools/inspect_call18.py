import json

with open('results/rair_v2/phase3_confirmatory_benchmark.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        row = json.loads(line)
        if row.get('record_type') == 'result' and row.get('question_id') == '5adf4ba65542992d7e9f931c' and row.get('seed') == 43 and row.get('system') == 'RAIR':
            res = row['result']
            c = res['llm_calls'][17]
            print("=== REQUEST MESSAGES ===")
            for msg in c['request'].get('messages', []):
                print(f"[{msg['role']}]\n{msg['content']}")
            print("=== RAW RESPONSE ===")
            print(c['raw'].get('message', {}).get('content', ''))
