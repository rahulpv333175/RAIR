import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from src.datasets.hotpotqa import load_hotpotqa
from src.evaluation.budget import RunBudget
from src.llm.ollama_client import OllamaClient
from src.rair.controller import RAIRController

with open("config/rair_v2_phase2_settings.json", "r", encoding="utf-8") as f:
    settings = json.load(f)

dev_data = load_hotpotqa("data/raw/hotpot_dev_distractor_v1.json")
lookup = {q.task.question_id: q for q in dev_data}

target_qids = [
    "5aba85335542994dbf01992d",  # polar question: Where both ... at Gettysburg?
    "5ade15f35542997545bbbe47",  # In which film ... Steve Jobs
    "5ac3b62b554299741d48a2f6",  # What act ... Rural Electrification Act
    "5adf4ba65542992d7e9f931c",  # 30th Disney animated film ... Beauty and the Beast
]

for qid in target_qids:
    ex = lookup.get(qid)
    if not ex:
        print(f"QID {qid} not found")
        continue
    print(f"\n==========================================")
    print(f"QID: {qid}")
    print(f"Question: {ex.task.question}")
    print(f"Gold: {ex.gold.answer}")
    
    client = OllamaClient(settings)
    budget = RunBudget(max_retrieval_calls=4, max_llm_calls=18)
    client.budget = budget
    controller = RAIRController(settings, client)
    res = controller.run(ex.task)
    print(f"Status: {res.status} | Stop: {res.stop_reason}")
    print(f"Prediction: '{res.prediction.answer}' (abstain={res.prediction.abstain})")
    print(f"Calls: {len(res.llm_calls)} | Retrievals: {res.usage.get('retrieval_calls')}")
    for f in res.state.verified_facts:
        print(f"  Fact: {f.statement}")
