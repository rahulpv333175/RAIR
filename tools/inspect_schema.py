import json

with open('results/rair_v2/phase2_benchmark_v2.jsonl', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        row = json.loads(line)
        print(f"Row {i} keys:", list(row.keys()))
        if 'rair' in row:
            print("rair keys:", list(row['rair'].keys()))
            if 'metrics' in row['rair']:
                print("rair metrics:", row['rair']['metrics'])
        elif 'metrics' in row:
            print("row metrics:", row['metrics'])
        if i >= 2:
            break

