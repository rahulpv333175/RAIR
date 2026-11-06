import json

with open('results/rair_v2/phase3_confirmatory_benchmark.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        row = json.loads(line)
        if row.get('record_type') == 'result' and row.get('question_id') == '5adf4ba65542992d7e9f931c' and row.get('seed') == 43 and row.get('system') == 'RAIR':
            res = row['result']
            print("Stop reason:", res['stop_reason'])
            print("Status:", res['status'])
            print("Prediction:", res['prediction'])
            print("LLM calls:", len(res['llm_calls']))
            for i, c in enumerate(res['llm_calls']):
                print(f"Call {i+1}: stage={c.get('stage')}")

