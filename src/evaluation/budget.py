"""Common per-question limits enforced before model calls and BM25 searches."""

from dataclasses import asdict, dataclass


class BudgetExhausted(RuntimeError):
    def __init__(self, resource: str) -> None:
        self.resource = resource
        super().__init__(f"Common {resource} budget exhausted.")


@dataclass
class RunBudget:
    max_retrieval_calls: int
    max_llm_calls: int
    retrieval_calls: int = 0
    llm_calls: int = 0
    final_calls: int = 0
    exhausted_resource: str | None = None

    def __post_init__(self) -> None:
        if type(self.max_retrieval_calls) is not int or self.max_retrieval_calls < 1:
            raise ValueError("Common retrieval budget must be a positive integer.")
        if type(self.max_llm_calls) is not int or self.max_llm_calls < 2:
            raise ValueError("Common LLM budget must allow at least two calls, including final synthesis.")

    def _exhausted(self, resource: str) -> None:
        self.exhausted_resource = resource
        raise BudgetExhausted(resource)

    def check_retrieval(self) -> None:
        if self.retrieval_calls >= self.max_retrieval_calls:
            self._exhausted("retrieval_calls")

    def consume_retrieval(self) -> None:
        self.check_retrieval()
        self.retrieval_calls += 1

    def consume_llm(self, *, final_answer: bool) -> None:
        ceiling = self.max_llm_calls if final_answer else self.max_llm_calls - 1
        if self.final_calls or self.llm_calls >= ceiling:
            self._exhausted("llm_calls")
        self.llm_calls += 1
        self.final_calls += int(final_answer)

    def to_dict(self) -> dict:
        return asdict(self)
