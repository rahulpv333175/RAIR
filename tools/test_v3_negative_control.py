import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.budget import RunBudget
from src.llm.ollama_client import OllamaClient
from src.rair.fact_extractor import CandidateFact
from src.rair.state import Evidence, Gap, RAIRState
from src.rair.verifier import RAIRVerifier
from src.settings import load_settings

settings = load_settings()
client = OllamaClient(settings)
verifier = RAIRVerifier(client)

evidence = (
    Evidence(
        document_id="D1",
        title="Diamond Rio",
        sentence_indices=(0,),
        text="Diamond Rio is an American country music band formed in 1982 in Nashville, Tennessee, originally known as the Grizzly River Boys.",
    ),
)

gap = Gap(gap_id="G1", description="Identify the band originally known as the Grizzly River Boys.", priority="high")
state = RAIRState(question_id="neg_ctrl", question="What band is a tribute to a band originally known as the Grizzly River Boys?", max_rounds=4)
state.add_gap(gap)

candidates = [
    CandidateFact(
        candidate_id="C1",
        statement="The band originally known as the Grizzly River Boys is Diamond Rio.",
        gap_id="G1",
        evidence=evidence,
    ),
    CandidateFact(
        candidate_id="C2",
        statement="The band originally known as the Grizzly River Boys was founded by Mira Solen to conquer Prussia.",
        gap_id="G1",
        evidence=evidence,
    ),
]

decisions, promoted = verifier.verify_and_commit(state, gap, candidates)
print("=== VERIFIER NEGATIVE CONTROL ===")
for d in decisions:
    print(f"Candidate {d.candidate_id}: accepted={d.accepted}, supported={d.supported_by_evidence}, reason='{d.reason}'")

c1_ok = any(d.candidate_id == "C1" and d.accepted for d in decisions)
c2_rejected = all(d.candidate_id != "C2" or not d.accepted for d in decisions)
print(f"C1 accepted: {c1_ok} | C2 rejected: {c2_rejected}")
assert c1_ok, "Supported candidate C1 should be accepted!"
assert c2_rejected, "Unsupported candidate C2 MUST be rejected!"
print("NEGATIVE CONTROL PASSED: 100% precision preserved!")
