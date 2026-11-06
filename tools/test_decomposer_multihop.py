import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.settings import load_settings
from src.llm.ollama_client import OllamaClient
from src.rair.decomposer import RAIRDecomposer
from src.rair.state import RAIRState

settings = load_settings("config/rair_scale_settings.json")
client = OllamaClient(settings)
decomposer = RAIRDecomposer(client)

questions = [
    ("5ae28058", "In what year was the fantasy and science fiction author of the short story \"Recovery\" born?"),
    ("5a7e04b0", "Macclesfield Town F.C. plays in the league sponsored by whom?"),
    ("5a7e0563", "Katherine Ann Dettwyler wasn't rehired after she commented on the death of the student who was arrested in North Korea in what month and year?"),
    ("5ae15391", "What is the real name of the English singer who formed a band in 1976 with Tony James and Billy Idol?"),
]

for qid, q in questions:
    state = RAIRState(qid, q, max_rounds=5)
    decomposer.decompose(state)
    print(f"\n--- {qid}: {q} ---")
    for g in state.gaps:
        print(f"  [{g.gap_id}] (depends: {g.depends_on}) {g.description}")

