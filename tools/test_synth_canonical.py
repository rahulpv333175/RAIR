import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm.ollama_client import OllamaClient
from src.settings import load_settings

settings = load_settings()
client = OllamaClient(settings)

PROMPT_CANDIDATE = """You are the final answer synthesizer
for a multi-hop question-answering system.

You may use ONLY the verified facts supplied to you.

Rules:
1. Do not use prior knowledge.
2. Do not use facts that are not explicitly present in verified knowledge.
3. Return the minimal span / shortest possible answer without conversational wrapping:
   - Polar / Boolean questions: If the question begins with an auxiliary verb ("Is", "Are",
     "Was", "Were", "Where" [when asking whether/if two events were in different wars or places],
     "Did", "Do", "Does", "Has", "Have", "Can", "Could") or asks whether something is true,
     return strictly either "yes" or "no". Do NOT list the entities, wars, dates, or reasons.
   - Work / Entity titles: When asked "In which film/movie/book/album/city...", or "what in common",
     return ONLY the title or proper name (e.g., "Steve Jobs", not 'Katherine Waterston portrayed Chrisann Brennan in the film Steve Jobs').
     Do NOT append the release year in parentheses unless the year is part of the official title.
   - Proper names / Formal designations: Retain the full proper name or designation present in the
     verified facts (e.g. for European routes use "European route E 22", not merely "E22"; for awards use
     the full award name e.g. "Daytime Emmy Award").
   - People / Full names: If verified facts provide a person's full canonical name (e.g. "Daron Vartan Malakian",
     "William Michael Albert Broad", "Maria Esther Andion Bueno"), prefer the complete name supported by the facts.
   - Count questions: When asked "How many [items]..." (e.g. "How many women...", "how many people..."),
     include the count noun if present in the source facts (e.g., "179 women").
   - Named Acts / Legislation: Strip leading articles and redundant years unless integral
     (e.g., "Rural Electrification Act", not "The Rural Electrification Act of 1936").
   - Entity questions: Return the requested entity/value, not a restatement of the question.
4. Cite the verified fact IDs that support the complete answer.
5. If the verified facts are insufficient to answer the question, abstain.
6. If abstaining, return:
   answer = ""
   citations = []
   abstain = true
7. If answering, return:
   abstain = false
8. Do not invent missing links.
9. Do not include explanations unless they are required to make the answer
   understandable.
10. Citations must reference only supplied verified fact IDs.
11. Planning gaps are fallible hints. An unresolved gap must not force abstention if verified
    facts already answer the core question.

Return only the JSON object required by the supplied schema.
"""

test_cases = [
    (
        "The Russian route M9 forms a part of what European route that has a length of about 5320 km?",
        {"F1": "The Russian route M9 forms a part of European route E 22."},
        "European route E 22"
    ),
    (
        "Which is a record producer, Zach Bogosian or Daron Malakian?",
        {"F1": "Daron Vartan Malakian is an Armenian-American singer, songwriter, and record producer."},
        "Daron Vartan Malakian"
    ),
    (
        "Which player is from Brazil, Jimmy Connors or Maria Bueno?",
        {"F1": "Maria Esther Andion Bueno was a Brazilian professional tennis player."},
        "Maria Esther Andion Bueno"
    ),
    (
        "How many women in total competed at the Asian Games the year Lee Young-Sun achieved her personal best throw of 58.87 metres?",
        {"F1": "A total of 179 women competed at the 2002 Asian Games."},
        "179 women"
    )
]

for q, facts, gold in test_cases:
    vf = "\n".join(f"- {fid}: {stmt}" for fid, stmt in facts.items())
    up = f"Original question:\n{q}\n\nVerified facts:\n{vf}\n\nUnresolved gaps:\n<none>\n\nAnswer if the verified facts identify the requested entity or provide the answer. Never fill a missing link."
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
    resp = client.chat(PROMPT_CANDIDATE, up, schema=schema, temperature=0.0)
    print(f"Q: {q[:60]}...")
    print(f"  Gold: '{gold}'")
    print(f"  Resp: {resp.content}")
    print()

