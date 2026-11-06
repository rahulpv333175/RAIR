"""Component removal, provenance, fair scheduling and common accounting."""
import copy
import unittest
from collections import Counter

from src.evaluation.budget import RunBudget
from src.evaluation.paired import ABLATIONS, audit_result, schedule, system_names, prepare_manifest
from src.evaluation.uncertainty import paired_bootstrap
from src.experiments.check_rair_pipeline import make_task
from src.rair.ablations import NoVerificationRAIRController, NoDecompositionRAIRController, UncheckedAdmission
from src.rair.fact_extractor import CandidateFact
from src.rair.state import RAIRState, Gap, Evidence
from src.settings import load_settings
from test_rair_controller import ScriptedClient, full_script, round_script
from src.llm.prompts import RAIR_VERIFIER_SCHEMA, RAIR_SYNTHESIZER_SCHEMA


class AblationTests(unittest.TestCase):
    def run_arm(self, controller, script, system, calls=18):
        settings=load_settings();client=ScriptedClient(settings,script)
        client.budget=RunBudget(4,calls);client.generation_temperature=.7
        result=controller(settings,client).run(make_task()).to_dict()
        audit_result(result,make_task(),client.budget,settings,42,system)
        self.assertEqual(client.script,[])
        self.assertIn('intervention',result)
        return result

    def test_no_verification_removes_only_gate_calls_and_records_no_fake_decisions(self):
        script=[r for r in full_script() if r[0]!=RAIR_VERIFIER_SCHEMA]
        result=self.run_arm(NoVerificationRAIRController,script,ABLATIONS[0])
        self.assertEqual(result['prediction']['answer'],'Nerava')
        self.assertEqual(result['usage']['llm_calls'],8)
        self.assertTrue(all(not r['decisions'] for r in result['rounds']))
        self.assertEqual(len(result['state']['verified_facts']),2)
        self.assertIn('unchecked',result['intervention'])

    def test_unchecked_admission_preserves_source_and_admits_without_semantic_check(self):
        state=RAIRState('q','Question?',4);gap=Gap('G1','Find a name');state.add_gap(gap)
        evidence=Evidence('D1','Source',(0,),'The source says Alice.')
        candidate=CandidateFact('C1','The answer is Bob.','G1',(evidence,))
        decisions,facts=UncheckedAdmission().verify_and_commit(state,gap,(candidate,))
        self.assertEqual(decisions,());self.assertEqual(facts[0].evidence,(evidence,))
        self.assertEqual(facts[0].statement,'The answer is Bob.');self.assertTrue(gap.resolved)

    def test_empty_unchecked_admission_does_not_resolve_and_wrong_gap_is_rejected(self):
        state=RAIRState('q','Question?',4);gap=Gap('G1','Find');state.add_gap(gap)
        self.assertEqual(UncheckedAdmission().verify_and_commit(state,gap,()),((),()))
        self.assertFalse(gap.resolved)
        candidate=CandidateFact('C1','Claim','G2',(Evidence('D','Title',(0,),'Text'),))
        with self.assertRaises(ValueError):UncheckedAdmission().verify_and_commit(state,gap,(candidate,))

    def test_no_decomposition_installs_whole_question_and_retains_verifier(self):
        script=round_script('pipeline-complete:D2','Mira Solen birthplace',
                            'Mira Solen was born in the city of Nerava.')
        script += [(RAIR_SYNTHESIZER_SCHEMA,{'answer':'Nerava','citations':['F1'],'abstain':False})]
        result=self.run_arm(NoDecompositionRAIRController,script,ABLATIONS[1])
        self.assertEqual(result['usage']['llm_calls'],5)
        self.assertEqual(result['state']['gaps'][0]['description'],make_task().question)
        self.assertEqual(result['state']['gaps'][0]['depends_on'],())
        self.assertEqual(len(result['rounds'][0]['decisions']),1)
        self.assertFalse(any(c['stage']=='decompose' for c in result['llm_calls']))

    def test_no_gate_still_reserves_common_final_call(self):
        script=full_script()[:1]+[(RAIR_SYNTHESIZER_SCHEMA,{'answer':'','citations':[],'abstain':True})]
        result=self.run_arm(NoVerificationRAIRController,script,ABLATIONS[0],calls=2)
        self.assertEqual(result['status'],'abstained')
        self.assertEqual(result['budget']['final_calls'],1)

    def test_four_arm_schedule_is_balanced_and_preserves_old_protocol(self):
        questions=[{'question_id':str(i)} for i in range(20)]
        entries=schedule(questions,[42,43],ablations=True)
        self.assertEqual(len(entries),160)
        counts=Counter((e['system'],e['position_in_block']) for e in entries)
        self.assertEqual(set(counts.values()),{10})
        self.assertEqual(system_names({'ablations':True}),['RAIR','KAIR',*ABLATIONS])
        self.assertEqual([e['system'] for e in schedule(questions[:1],[42])],['RAIR','KAIR'])
        settings=copy.deepcopy(load_settings());settings['evaluation']['ablations']='yes'
        with self.assertRaises(ValueError):prepare_manifest(settings)

    def test_adjusted_intervals_are_labeled_and_keep_seeds_clustered(self):
        manifest={'questions':[{'question_id':str(i)} for i in range(3)],
                  'settings':{'evaluation':{'seeds':[42,43],'bootstrap_resamples':1000,'bootstrap_seed':4}}}
        rows=[{'question_id':str(i),'seed':seed,'system':system,
               'evaluation':{'exact_match':float(system=='KAIR'),'answer_f1':float(system=='KAIR')}}
              for i in range(3) for seed in (42,43) for system in ('RAIR','KAIR')]
        adjusted=paired_bootstrap(manifest,rows,confidence_level=.975)
        self.assertEqual(adjusted['confidence_level'],.975)
        self.assertEqual(adjusted['KAIR_minus_RAIR']['exact_match']['ci97_5'],[1.,1.])
        self.assertIn('ci95',paired_bootstrap(manifest,rows)['KAIR_minus_RAIR']['exact_match'])


if __name__=='__main__':unittest.main()
