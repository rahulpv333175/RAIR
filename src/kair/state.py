"""Private knowledge and source-exact context for a competitive KAIR agent."""

from dataclasses import dataclass, field
from typing import Any

from src.rair.state import Evidence


@dataclass(frozen=True)
class KAIRFact:
    fact_id: str
    statement: str
    evidence: tuple[Evidence, ...]


@dataclass
class KAIRState:
    agent_id: str
    seed: int
    known: list[KAIRFact] = field(default_factory=list)
    required: list[str] = field(default_factory=list)
    query_history: list[dict[str, Any]] = field(default_factory=list)
    context: tuple[Evidence, ...] = ()
    initialized: bool = False
    status: str = "active"
    next_fact_number: int = 1

    @property
    def complete(self) -> bool:
        # Algorithm 1 starts with R empty; that is not yet an agent solution.
        return self.initialized and bool(self.known) and not self.required
