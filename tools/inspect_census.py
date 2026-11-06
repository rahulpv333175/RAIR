import csv
from collections import defaultdict

pairs = defaultdict(dict)
with open('deliverables/rair_v2/RAIR_v2_Outcome_Census.csv', 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        key = (row['question_id'], row['seed'])
        pairs[key][row['system']] = row

print(f"Total pairs: {len(pairs)}")
kair_wins = []
rair_wins = []
ties = []

for key, p in pairs.items():
    r = p['RAIR']
    k = p['KAIR']
    r_em = float(r['EM'])
    k_em = float(k['EM'])
    if k_em > r_em:
        kair_wins.append((key, r, k))
    elif r_em > k_em:
        rair_wins.append((key, r, k))
    else:
        ties.append((key, r, k))

print(f"RAIR wins: {len(rair_wins)}, KAIR wins: {len(kair_wins)}, Ties: {len(ties)}")
print("\n--- KAIR WINS (where RAIR lost) ---")
for (qid, seed), r, k in kair_wins:
    print(f"Q: {qid} (seed {seed}) | RAIR stop: {r['stop']}, ans: '{r['answer']}' | KAIR stop: {k['stop']}, ans: '{k['answer']}' | RAIR llm: {r['llm_calls']}, retr: {r['retrieval_calls']}")

print("\n--- RAIR TIES WITH 0 EM ---")
for (qid, seed), r, k in ties:
    if float(r['EM']) == 0:
        print(f"Q: {qid} (seed {seed}) | RAIR stop: {r['stop']}, ans: '{r['answer']}' | KAIR stop: {k['stop']}, ans: '{k['answer']}'")
