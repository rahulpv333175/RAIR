import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm.ollama_client import OllamaClient
from src.llm.prompts import RAIR_SYNTHESIZER_SYSTEM_PROMPT
from src.settings import load_settings

settings = load_settings()
client = OllamaClient(settings)

test_cases = [
    (
        "Katherine Waterston and Chrisann Brennan has what in common?",
        {
            "F1": "Chrisann Brennan is an American painter and writer.",
            "F2": "Katherine Waterston portrayed Chrisann Brennan in the film 'Steve Jobs'."
        },
        {},
        "Steve Jobs"
    ),
    (
        "Augustus Jesse Bowie Jr was the innovator of the switch that was crucial to leading to the passage of which federal legislation in 1936?",
        {
            "F1": "Augustus Jesse Bowie Jr. innovated the 1000lb. 287Kv disconnecting switch.",
            "F2": "The Rural Electrification Act of 1936 was enacted on May 20, 1936.",
            "F3": "The Rural Electrification Act of 1936 provided federal loans for the installation of electrical distribution systems to serve isolated rural areas of the United States."
        },
        {},
        "Rural Electrification Act"
    ),
]

user_instruction = (
    "Answer if the verified facts identify the requested entity or provide the answer. "
    "Unresolved gaps are planning hints, not a veto: if a fact answers the question, output the answer. Never fill a missing link."
)

for q, facts, gaps, gold in test_cases:
    verified_facts = "\n".join(f"- {fid}: {stmt}" for fid, stmt in facts.items())
    unresolved_gaps = "\n".join(f"- {gid}: {desc}" for gid, desc in gaps.items()) or "<none>"
    user_p = f"Original question:\n{q}\n\nVerified facts:\n{verified_facts}\n\nUnresolved gaps:\n{unresolved_gaps}\n\n{user_instruction}"
    
    schema = {
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "answer": {"const": ""},
                    "citations": {"type": "array", "items": {"type": "string"}, "maxItems": 0},
                    "abstain": {"const": True}
                },
                "required": ["answer", "citations", "abstain"],
                "additionalProperties": False
            },
            {
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "minLength": 1},
                    "citations": {"type": "array", "items": {"type": "string", "enum": list(facts)}, "minItems": 1, "maxItems": len(facts), "uniqueItems": True},
                    "abstain": {"const": False}
                },
                "required": ["answer", "citations", "abstain"],
                "additionalProperties": False
            }
        ]
    }
    
    resp = client.chat(RAIR_SYNTHESIZER_SYSTEM_PROMPT, user_p, schema=schema, temperature=0.0)
    print(f"Q: {q[:50]}... | Gold: {gold}")
    print("Response:", resp.content)
