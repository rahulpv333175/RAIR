import json
from pathlib import Path

# Collect all question IDs ever used in:
# 1. smoke tests
# 2. Step 4, Step 5, Step 9, Step 10
# 3. Phase 2 (manifests)
# 4. Phase 3 (manifests)
# 5. any other config manifests

used_qids = set()

for config_file in Path("config").glob("*.json"):
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                # check for questions list
                if "questions" in data and isinstance(data["questions"], list):
                    for item in data["questions"]:
                        if isinstance(item, str):
                            used_qids.add(item)
                        elif isinstance(item, dict) and "question_id" in item:
                            used_qids.add(item["question_id"])
                        elif isinstance(item, dict) and "_id" in item:
                            used_qids.add(item["_id"])
    except Exception as e:
        pass

# Also scan results/*.jsonl
for res_file in Path("results").glob("**/*.jsonl"):
    try:
        with open(res_file, "r", encoding="utf-8") as f:
            for line in f:
                if "question_id" in line:
                    row = json.loads(line)
                    if "question_id" in row and row["question_id"]:
                        used_qids.add(row["question_id"])
    except Exception:
        pass

print(f"Total historically touched question IDs: {len(used_qids)}")

# Check against raw dataset
with open("data/raw/hotpot_dev_distractor_v1.json", "r", encoding="utf-8") as f:
    dev_data = json.load(f)

all_dev_ids = {q["_id"] for q in dev_data}
untouched_ids = all_dev_ids - used_qids
print(f"Total dev questions: {len(all_dev_ids)}")
print(f"Untouched questions available: {len(untouched_ids)}")

