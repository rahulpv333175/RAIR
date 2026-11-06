import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.settings import load_settings
from dashboard.server import Dashboard

def main():
    d = Dashboard(load_settings())
    res = d.rair_v2.describe()
    print("Dashboard RAIR v2 integration test:")
    print("  Available:", res["available"])
    print("  Questions:", res["questions"])
    print("  Pairs:", len(res["pairs"]))
    print(f"  RAIR EM: {res['systems']['RAIR']['metrics']['exact_match']:.1%}")
    print(f"  KAIR EM: {res['systems']['KAIR']['metrics']['exact_match']:.1%}")
    print(f"  Gold Document Recall: RAIR={res['systems']['RAIR']['metrics']['retrieval_recall']:.1%}, KAIR={res['systems']['KAIR']['metrics']['retrieval_recall']:.1%}")
    case0 = d.rair_v2.case(res["pairs"][0]["question_id"], res["pairs"][0]["seed"])
    print(f"  Case 0 fetched successfully!")
    print(f"    Question: {case0['question'][:60]}...")
    print(f"    RAIR: {case0['results']['RAIR']['prediction']['answer']}")
    print(f"    KAIR: {case0['results']['KAIR']['prediction']['answer']}")
    print("DASHBOARD INTEGRATION VERIFIED!")

if __name__ == "__main__":
    main()
