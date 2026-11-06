"""Regression proof for constrained role contracts and bounded recovery."""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.evaluation.budget import RunBudget
from src.evaluation.paired import schedule, aggregate, METRICS
from src.experiments.check_rair_pipeline import make_task
from src.llm.ollama_client import OllamaClient
from src.rair.evidence_filter import RAIREvidenceFilter, EvidenceFilterError
from src.rair.fact_extractor import RAIRFactExtractor, FactExtractionError, CandidateFact
from src.rair.query_planner import select_next_gap, QueryPlanningError
from src.rair.reference import ReferenceRAIRController
from src.rair.retrieval_step import RetrievalStepResult
from src.rair.state import RAIRState, Gap, Evidence, QueryAttempt
from src.rair.synthesizer import RAIRSynthesizer, SynthesisError
from src.rair.verifier import RAIRVerifier, VerificationError
from src.retrieval.bm25 import RetrievalResult
from src.settings import load_settings
from test_rair_controller import ScriptedClient, round_script
from src.rair.controller import RAIRController
from src.llm import prompts


class WireClient:
    def __init__(self, output):
        self.output = output

    def chat(self, system, user, **kwargs):
        self.schema, self.user = kwargs['schema'], user
        return SimpleNamespace(json_object=lambda: copy.deepcopy(self.output))


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.task = make_task()
        self.gap = Gap('G1', 'Find the author.', 'high')
        self.state = RAIRState(self.task.question_id, self.task.question, 4, gaps=[self.gap])
        doc = self.task.documents[0]
        self.evidence = Evidence(doc.document_id, doc.title, (0,), doc.sentences[0])
        self.candidates = tuple(CandidateFact(f'C{i}', f'Claim {i}', 'G1', (self.evidence,)) for i in (1, 2))

    def retrieval(self):
        return RetrievalStepResult(1, self.gap, 'author', tuple(
            RetrievalResult(i, doc, 1.0) for i, doc in enumerate(self.task.documents[:2], 1)))

    def test_aliases_reconstruct_original_sources_in_canonical_order(self):
        client = WireClient({'selections': ['E3', 'E1', 'E1']})
        evidence = RAIREvidenceFilter(client).filter(self.state, self.gap, self.retrieval())
        self.assertEqual([e.document_id for e in evidence], [d.document_id for d in self.task.documents[:2]])
        self.assertEqual([e.text for e in evidence], [d.sentences[0] for d in self.task.documents[:2]])
        self.assertEqual(client.schema['properties']['selections']['items']['enum'], ['E1', 'E2', 'E3'])

    def test_unknown_source_alias_still_fails_closed(self):
        for invalid in ('E999', self.task.documents[0].document_id, 1):
            with self.subTest(invalid=invalid), self.assertRaises(EvidenceFilterError):
                RAIREvidenceFilter(WireClient({'selections': [invalid]})).filter(self.state, self.gap, self.retrieval())

    def test_extractor_ids_assigned_by_software_and_sources_constrained(self):
        client = WireClient({'candidates': [{'statement': 'Mira Solen wrote the novel.', 'evidence_ids': ['E1']}]})
        result = RAIRFactExtractor(client).extract(self.state, self.gap, (self.evidence,))
        self.assertEqual(result[0].candidate_id, 'C1')
        self.assertEqual(result[0].evidence, (self.evidence,))
        properties = client.schema['properties']['candidates']['items']['properties']
        self.assertNotIn('candidate_id', properties)
        self.assertEqual(properties['evidence_ids']['items']['enum'], ['E1'])
        client.output['candidates'][0]['evidence_ids'] = ['F1']
        with self.assertRaises(FactExtractionError):
            RAIRFactExtractor(client).extract(self.state, self.gap, (self.evidence,))

    def decisions(self):
        return {'decisions': {c.candidate_id: {'supported_by_evidence': True, 'relevant_to_gap': True,
            'answer_type_ok': True, 'contains_unresolved_placeholder': False, 'resolves_gap': True,
            'reason': 'Direct source support.'} for c in self.candidates}}

    def test_rejected_resolution_cannot_promote_or_discard_other_supported_claim(self):
        payload = self.decisions()
        payload['decisions']['C1']['supported_by_evidence'] = False
        client = WireClient(payload)
        decisions = RAIRVerifier(client).verify(self.state, self.gap, self.candidates)
        self.assertFalse(decisions[0].accepted)
        self.assertFalse(decisions[0].resolves_gap)
        self.assertTrue(decisions[1].accepted)
        self.assertTrue(decisions[1].resolves_gap)
        self.assertEqual(client.schema['properties']['decisions']['required'], ['C1', 'C2'])

    def test_missing_extra_or_nonboolean_verification_still_fails_closed(self):
        for modification in ('missing', 'extra', 'bad_bool'):
            payload = self.decisions()
            if modification == 'missing':
                del payload['decisions']['C2']
            elif modification == 'extra':
                payload['decisions']['C3'] = payload['decisions']['C1']
            else:
                payload['decisions']['C1']['supported_by_evidence'] = 'true'
            with self.subTest(modification=modification), self.assertRaises(VerificationError):
                RAIRVerifier.parse_response(payload, candidates=self.candidates)

    def test_untried_actionable_gap_precedes_repeated_gap_and_stalls_are_excluded(self):
        second = Gap('G2', 'Another independent need.', 'low')
        blocked = Gap('G3', 'Dependent need.', 'high', ('G1',))
        self.state.gaps += [second, blocked]
        self.state.record_query(QueryAttempt(1, 'G1', 'author', (), False, 'No evidence.'))
        self.assertEqual(select_next_gap(self.state), second)
        self.assertEqual(select_next_gap(self.state, {'G2'}), self.gap)
        with self.assertRaises(QueryPlanningError):
            select_next_gap(self.state, {'G1', 'G2'})

    def test_shared_final_schema_only_allows_available_citations(self):
        client = WireClient({'answer': 'Mira Solen', 'citations': ['F7'], 'abstain': False})
        synthesizer = RAIRSynthesizer(client)
        self.assertEqual(synthesizer.synthesize_knowledge('Who?', {'F7': 'The author is Mira Solen.'}, {}).answer, 'Mira Solen')
        answered = client.schema['oneOf'][1]['properties']
        self.assertEqual(answered['citations']['items']['enum'], ['F7'])
        self.assertFalse(answered['abstain']['const'])
        client.output['citations'] = ['F1']
        with self.assertRaises(SynthesisError):
            synthesizer.synthesize_knowledge('Who?', {'F7': 'The author is Mira Solen.'}, {})

    def test_no_facts_constrains_model_to_valid_abstention(self):
        client = WireClient({'answer': '', 'citations': [], 'abstain': True})
        result = RAIRSynthesizer(client).synthesize_knowledge('Who?', {}, {'G1': 'Missing author.'})
        self.assertTrue(result.abstain)
        self.assertEqual(client.schema['properties']['answer'], {'const': ''})
        self.assertEqual(client.schema['properties']['citations']['maxItems'], 0)

    def test_controller_continues_another_gap_after_duplicate_fallback_is_used(self):
        gaps = {'gaps': [{'gap_id': f'G{i}', 'description': description, 'priority': 'high', 'depends_on': []}
                         for i, description in ((1, 'Find author.'), (2, 'Find birthplace.'))]}
        script = [(prompts.RAIR_DECOMPOSER_SCHEMA, gaps)]
        for query in ('Glass Orchard author', self.task.question):
            script += [(prompts.RAIR_QUERY_PLANNER_SCHEMA, {'query': query}),
                       (prompts.RAIR_EVIDENCE_FILTER_SCHEMA, {'selections': []})]
        script += [(prompts.RAIR_QUERY_PLANNER_SCHEMA, {'query': 'Glass Orchard author'}),
                   (prompts.RAIR_QUERY_PLANNER_SCHEMA, {'query': 'Mira Solen birthplace'}),
                   (prompts.RAIR_EVIDENCE_FILTER_SCHEMA, {'selections': []}),
                   (prompts.RAIR_SYNTHESIZER_SCHEMA, {'answer': '', 'citations': [], 'abstain': True})]
        settings = load_settings()
        settings['rair']['max_rounds'] = 3
        client = ScriptedClient(settings, script)
        client.budget = RunBudget(3, 18)
        result = RAIRController(settings, client).run(self.task)
        self.assertIsNone(result.error)
        self.assertEqual([r['gap_id'] for r in result.rounds], ['G1', 'G2', 'G2'])
        self.assertEqual([r['gap_id'] for r in result.planner_stalls], ['G1'])
        self.assertEqual(client.budget.retrieval_calls, 3)
        self.assertEqual(client.script, [])

    def test_standalone_call_ceiling_includes_stalled_gap_planners(self):
        gaps = {'gaps': [{'gap_id': f'G{i}', 'description': 'Identify useful author information.',
                         'priority': 'high', 'depends_on': []} for i in range(1, 7)]}
        claim = 'The Glass Orchard was written by Mira Solen.'
        script = [(prompts.RAIR_DECOMPOSER_SCHEMA, gaps)] + round_script(
            'pipeline-complete:D1', self.task.question, claim, resolves=False)
        script += [(prompts.RAIR_QUERY_PLANNER_SCHEMA, {'query': self.task.question}) for _ in range(5)]
        for i in range(4):
            script += round_script('pipeline-complete:D1', f'Glass Orchard author detail {i}', claim, resolves=False)
        script += [(prompts.RAIR_SYNTHESIZER_SCHEMA, {'answer': '', 'citations': [], 'abstain': True})]
        settings = load_settings()
        settings['rair']['max_rounds'] = 5
        client = ScriptedClient(settings, script)
        self.assertIsNone(client.budget)
        controller = RAIRController(settings, client)
        result = controller.run(self.task)
        self.assertIsNone(result.error)
        self.assertEqual(len(result.planner_stalls), 5)
        self.assertEqual(result.usage['retrieval_calls'], 5)
        self.assertEqual(result.usage['llm_calls'], 27)
        self.assertEqual(controller.policy['max_llm_calls'], result.usage['llm_calls'])
        self.assertEqual(client.script, [])


class ReferenceTests(unittest.TestCase):
    def test_same_question_control_summary_requires_every_arm(self):
        questions = [{'question_id': str(i)} for i in range(3)]
        config = {'seeds': [42, 43], 'reference_rair': {}, 'bootstrap_seed': 17, 'bootstrap_resamples': 1000}
        manifest = {'questions': questions, 'settings': {'evaluation': config},
                    'schedule': schedule(questions, config['seeds'], reference=True)}
        rows = [{**entry, 'evaluation': {**dict.fromkeys(METRICS, int(entry['system'] == 'RAIR')),
                                       'annotation_issues': []},
                 'result': {'status': 'answered', 'stop_reason': 'complete',
                            'prediction': {'answer': 'yes', 'citations': [], 'abstain': False},
                            'usage': {'token_counts_complete': True, **dict.fromkeys(
                                ('llm_calls', 'retrieval_calls', 'prompt_tokens', 'completion_tokens', 'elapsed_seconds'), 1)}}}
                for entry in manifest['schedule']]
        summary = aggregate(manifest, rows)
        self.assertEqual(summary['RAIR_minus_REFERENCE']['metrics']['exact_match'], {'estimate': 1.0, 'ci95': [1.0, 1.0]})
        self.assertEqual(summary['uncertainty']['primary_endpoint'], 'RAIR_minus_REFERENCE.exact_match')
        self.assertEqual(summary['KAIR_minus_RAIR']['exact_match'], -1.0)
        with self.assertRaisesRegex(ValueError, 'every planned'):
            aggregate(manifest, rows[:-1])

    def test_three_arm_schedule_balances_order_and_retains_primary_pairs(self):
        entries = schedule([{'question_id': str(i)} for i in range(6)], [42, 43], reference=True)
        self.assertEqual(len(entries), 36)
        for i in range(6):
            block = [e for e in entries if e['question_id'] == str(i)]
            self.assertEqual([e['system'] for e in block[:3]], [e['system'] for e in block[3:]][::-1])
            for system in ('RAIR', 'KAIR'):
                self.assertEqual({e['position_in_pair'] for e in block if e['system'] == system}, {0, 1})

    def test_reference_hashes_and_budget_transfer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'src').mkdir()
            (root / 'src/__init__.py').write_text('')
            (root / 'requirements.txt').write_text('')
            archive = root / 'archive.zip'
            archive.write_bytes(b'frozen test archive')
            settings = load_settings()
            settings['evaluation']['reference_rair'] = {
                'root': str(root), 'archive': str(archive), 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'source_sha256': {name: hashlib.sha256(b'').hexdigest() for name in ('src/__init__.py', 'requirements.txt')}}
            client = OllamaClient(settings)
            client.budget = RunBudget(4, 18)
            reference = ReferenceRAIRController(settings, client)
            output = {'budget': RunBudget(4, 18, retrieval_calls=2, llm_calls=10, final_calls=1).to_dict(), 'llm_calls': []}
            with patch('src.rair.reference.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(output))):
                result = reference.run(make_task()).to_dict()
            self.assertEqual(client.budget.llm_calls, 10)
            self.assertEqual(client.budget.retrieval_calls, 2)
            self.assertIn('shared_final_sha256', result['reference'])
            (root / 'src/__init__.py').write_text('# altered')
            with self.assertRaisesRegex(ValueError, 'frozen Step 4'):
                ReferenceRAIRController(settings, client)


if __name__ == '__main__':
    unittest.main()
