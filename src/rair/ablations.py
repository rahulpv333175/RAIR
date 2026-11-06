"""One-component removals; original provenance and final-answer policy remain."""
from dataclasses import dataclass

from src.rair.controller import RAIRController, RAIRResult
from src.rair.state import Gap, VerifiedFact
from src.rair.verifier import RAIRVerifier


class WholeQuestionGap:
    def decompose(self, state):
        if state.gaps:
            raise ValueError('Decomposition requires empty state.')
        gap = Gap('G1', state.question, priority='high')
        state.add_gap(gap)
        return [gap]


class UncheckedAdmission:
    def verify_and_commit(self, state, gap, candidates):
        # Remove the semantic gate, not provenance/type validation or safe IDs.
        if gap.resolved or gap not in state.actionable_gaps():
            raise ValueError('Unchecked admission requires an actionable gap.')
        if any(c.gap_id != gap.gap_id for c in candidates):
            raise ValueError('Candidate belongs to another gap.')
        promoted = []
        for candidate in candidates:
            fact = VerifiedFact(RAIRVerifier._next_fact_id(state), candidate.statement,
                                gap.gap_id, candidate.evidence)
            state.add_verified_fact(fact)
            promoted.append(fact)
        if promoted:
            state.resolve_gap(gap.gap_id)
        # No fabricated verifier decisions: these facts have NOT been verified.
        return (), tuple(promoted)


@dataclass
class AblationResult(RAIRResult):
    intervention: str = ''


class AblationRAIRController(RAIRController):
    def run(self, task):
        result = super().run(task)
        return AblationResult(**vars(result), intervention=self.intervention)


class NoVerificationRAIRController(AblationRAIRController):
    intervention = ('No semantic verification call. Admit every structurally valid extracted candidate; '
                    'resolve its gap when at least one candidate is admitted. Stored shared facts are unchecked. '
                    'Provenance validation and common final synthesis are retained.')

    def __init__(self, settings, client, **kwargs):
        super().__init__(settings, client, **kwargs)
        self.verifier = UncheckedAdmission()

    @property
    def policy(self):
        policy = {**super().policy, 'intervention': self.intervention}
        policy['max_llm_calls'] -= self.max_rounds
        policy['final_answer'] = 'common final policy over unchecked admitted facts; abstain if insufficient'
        return policy


class NoDecompositionRAIRController(AblationRAIRController):
    intervention = ('No generated subquestions or dependency graph. Install one gap equal to the original '
                    'question; retain query planning, filtering, extraction, verification and final synthesis.')

    def __init__(self, settings, client, **kwargs):
        super().__init__(settings, client, **kwargs)
        self.decomposer = WholeQuestionGap()

    @property
    def policy(self):
        return {**super().policy, 'max_llm_calls': 1 + 4*self.max_rounds, 'intervention': self.intervention}
