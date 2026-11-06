import json

path = "results/rair_v3/rair_v3_benchmark.jsonl"
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        row = json.loads(line)
        if row.get("question_id") == "5ae153915542990adbacf752" and row.get("system") == "RAIR":
            print("Seed:", row.get("seed"))
            print("Stop:", row["result"]["stop_reason"])
            print("Answer:", row["result"]["prediction"]["answer"])
            print("Verified facts:")
            for fact in row["result"]["state"]["verified_facts"]:
                print("  ", fact["statement"])
            print("Gaps:")
            for g in row["result"]["state"]["gaps"]:
                print("  ", g["gap_id"], g["description"], "resolved=", g["resolved"])
            print("Rounds:")
            for r in row["result"]["rounds"]:
                print("  R", r["round_number"], r["gap_id"], "q=", r["query"])

