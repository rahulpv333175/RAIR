import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm.ollama_client import OllamaClient
from src.llm.prompts import RAIR_DECOMPOSER_SCHEMA, RAIR_DECOMPOSER_SYSTEM_PROMPT
from src.settings import load_settings

settings = load_settings()
client = OllamaClient(settings)

PROMPT_CANDIDATE = RAIR_DECOMPOSER_SYSTEM_PROMPT.strip() + """
- For comparison or selection questions between two named entities ("Between X and Y, who/which is Z?"),
  create distinct gaps to investigate BOTH entities (e.g. G1 for X, G2 for Y) so neither candidate is ignored.
"""

q = "In between Burton C. Bell and Billy Idol who is known professionally as Billy Idol?"
up = f"Question:\n{q}\n\nDecompose into minimal information gaps."

resp = client.chat(PROMPT_CANDIDATE, up, schema=RAIR_DECOMPOSER_SCHEMA, temperature=0.0)
print(resp.content)

