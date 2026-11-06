"""Four-arm summaries and their independent read-only dashboard view."""
import json
import unittest
from unittest.mock import patch

import test_step4_benchmark
import test_dashboard
from dashboard.ablations import AblationStudy, ConfirmationStudy, RAIRv2Study, RAIRv3Study, RAIRScaleStudy, RAIRTestStudy
from src.evaluation.paired import METRICS, aggregate, fingerprint, prepare_manifest, render_report


class StudyTests(unittest.TestCase):
    setUp=test_step4_benchmark.HeldOutTests.setUp

    def make_study(self):
        self.settings['evaluation']['ablations']=True
        manifest=prepare_manifest(self.settings)
        rows=[]
        for entry in manifest['schedule']:
            correct=entry['system']=='RAIR'
            rows.append({'record_type':'result',**entry,'result':{
                'question':'A question?', 'status':'answered','stop_reason':'all_gaps_resolved',
                'prediction':{'answer':'yes' if correct else 'no','abstain':False,'citations':[]},
                'usage':{'llm_calls':4,'retrieval_calls':1,'prompt_tokens':100,'completion_tokens':20,
                         'elapsed_seconds':1.,'token_counts_complete':True}},
                'evaluation':{**{m:float(correct) for m in METRICS},'annotation_issues':[]}})
        summary=aggregate(manifest,rows)
        return manifest,rows,summary

    def test_four_arm_aggregation_and_adjusted_contrasts(self):
        manifest,rows,summary=self.make_study()
        self.assertEqual(len(summary['systems']),4)
        self.assertEqual(len(rows),16)
        self.assertEqual(len(summary['ablation_contrasts']),2)
        for values in summary['ablation_contrasts'].values():
            self.assertEqual(values['exact_match']['estimate'],1.)
            self.assertEqual(values['exact_match']['ci97_5'],[1.,1.])
        report=render_report(manifest,summary)
        self.assertIn('No decomposition',report)
        self.assertIn('97.5%',report)
        self.assertIn('component-removal EM contrasts',report)

    def test_dashboard_reads_all_four_arms_and_rejects_tampered_summary(self):
        manifest,rows,summary=self.make_study()
        root=self.path.parent; (root/'config').mkdir();(root/'results').mkdir()
        study=AblationStudy(root)
        self.assertFalse(study.describe()['available'])
        (root/'config/step9_ablations.json').write_text(json.dumps(manifest),encoding='utf8')
        env={'server':{'version':'test'},'model':{'digest':'test','name':'test'}}
        journal=[{'record_type':'metadata','manifest':manifest,'manifest_sha256':fingerprint(manifest),'environment':env},
                 *rows,{'record_type':'verification','consistent':True,'environment':env},
                 {'record_type':'summary','summary':summary}]
        (root/'results/step9_ablations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in journal),encoding='utf8')
        summary_path=root/'results/step9_ablations.summary.json';summary_path.write_text(json.dumps(summary),encoding='utf8')
        data=study.describe()
        self.assertEqual(data['runs'],16);self.assertEqual(len(data['pairs']),4)
        self.assertEqual(len(data['pairs'][0]['systems']),4)
        self.assertIs(study.describe(),data)
        summary['systems']['RAIR']['metrics']['exact_match']=.3
        summary_path.write_text(json.dumps(summary),encoding='utf8')
        with self.assertRaises(ValueError):study.describe()

    def test_confirmation_is_separate_and_rejects_wrong_arms(self):
        manifest,rows,_=self.make_study()
        del manifest['settings']['evaluation']['ablations']
        manifest['schedule']=[e for e in manifest['schedule'] if e['system'] in ('RAIR','KAIR')]
        rows=[r for r in rows if r['system'] in ('RAIR','KAIR')]
        summary=aggregate(manifest,rows)
        root=self.path.parent;(root/'config').mkdir();(root/'results').mkdir()
        study=ConfirmationStudy(root)
        self.assertFalse(study.describe()['available'])
        study.paths[0].write_text(json.dumps(manifest),encoding='utf8')
        env={'server':{'version':'test'},'model':{'digest':'test','name':'test'}}
        journal=[{'record_type':'metadata','manifest':manifest,'manifest_sha256':fingerprint(manifest),'environment':env},
                 *rows,{'record_type':'verification','consistent':True,'environment':env},
                 {'record_type':'summary','summary':summary}]
        study.paths[1].write_text(''.join(json.dumps(r)+'\n' for r in journal),encoding='utf8')
        study.paths[2].write_text(json.dumps(summary),encoding='utf8')
        data=study.describe()
        self.assertEqual(data['runs'],8)
        self.assertEqual(set(data['systems']),{'RAIR','KAIR'})
        self.assertEqual(data['contrasts'],{})
        case=study.case(data['pairs'][0]['question_id'],data['pairs'][0]['seed'])
        self.assertEqual(set(case['results']),{'RAIR','KAIR'})
        self.assertEqual(case['question'],'A question?')
        with self.assertRaises(KeyError):study.case('missing',42)
        self.assertFalse(AblationStudy(root).describe()['available'])
        study.arms={'RAIR'};study.signature=None
        with self.assertRaises(ValueError):study.describe()


class StudyHTTPTests(unittest.TestCase):
    setUp=test_dashboard.HTTPTests.setUp
    stop=test_dashboard.HTTPTests.stop
    request=test_dashboard.HTTPTests.request

    def test_read_only_route_and_archive_failure(self):
        with patch.object(self.app.ablations,'describe',return_value={'available':False,'message':'pending'}):
            self.assertEqual(self.request('GET','/api/ablations')[0],200)
            self.assertEqual(self.request('GET','/api/ablations',headers={'Origin':'https://evil.example'})[0],403)
        with patch.object(self.app.ablations,'describe',side_effect=ValueError('inconsistent')):
            self.assertEqual(self.request('GET','/api/ablations')[0],503)
        self.assertIsNone(self.app.active)

    def test_confirmation_route_and_origin_guard(self):
        with patch.object(self.app.confirmation,'describe',return_value={'available':False,'message':'pending'}):
            self.assertEqual(self.request('GET','/api/confirmation')[0],200)
            self.assertEqual(self.request('GET','/api/confirmation',headers={'Origin':'https://evil.example'})[0],403)
        with patch.object(self.app.confirmation,'describe',side_effect=ValueError('inconsistent')):
            self.assertEqual(self.request('GET','/api/confirmation')[0],503)
        self.assertIsNone(self.app.active)

    def test_confirmation_case_routes_validate_queries_and_failures(self):
        with patch.object(self.app.confirmation,'case',return_value={'results':{'RAIR':{},'KAIR':{}}}):
            self.assertEqual(self.request('GET','/api/confirmation/case?question_id=q&seed=42')[0],200)
            for query in ('','?question_id=q','?question_id=q&seed=x','?question_id=q&seed=42&seed=43','?question_id=q&seed=42&extra=1'):
                self.assertEqual(self.request('GET','/api/confirmation/case'+query)[0],400)
            self.assertEqual(self.request('GET','/api/confirmation/case?question_id=q&seed=42',headers={'Origin':'https://evil.example'})[0],403)
        with patch.object(self.app.confirmation,'case',side_effect=KeyError('missing')):
            self.assertEqual(self.request('GET','/api/confirmation/case?question_id=q&seed=42')[0],404)
        with patch.object(self.app.confirmation,'case',side_effect=ValueError('corrupt')):
            self.assertEqual(self.request('GET','/api/confirmation/case?question_id=q&seed=42')[0],503)
        self.assertIsNone(self.app.active)

    def test_rair_v2_route_and_case(self):
        with patch.object(self.app.rair_v2,'describe',return_value={'available':True,'runs':140}):
            self.assertEqual(self.request('GET','/api/rair_v2')[0],200)
            self.assertEqual(self.request('GET','/api/rair_v2',headers={'Origin':'https://evil.example'})[0],403)
        with patch.object(self.app.rair_v2,'describe',side_effect=ValueError('corrupt')):
            self.assertEqual(self.request('GET','/api/rair_v2')[0],503)
        with patch.object(self.app.rair_v2,'case',return_value={'results':{'RAIR':{},'KAIR':{}}}):
            self.assertEqual(self.request('GET','/api/rair_v2/case?question_id=q&seed=42')[0],200)
            for query in ('','?question_id=q','?question_id=q&seed=x','?question_id=q&seed=42&extra=1'):
                self.assertEqual(self.request('GET','/api/rair_v2/case'+query)[0],400)
            self.assertEqual(self.request('GET','/api/rair_v2/case?question_id=q&seed=42',headers={'Origin':'https://evil.example'})[0],403)
        with patch.object(self.app.rair_v2,'case',side_effect=KeyError('missing')):
            self.assertEqual(self.request('GET','/api/rair_v2/case?question_id=q&seed=42')[0],404)
        self.assertIsNone(self.app.active)

    def test_rair_v3_route_and_case(self):
        with patch.object(self.app.rair_v3,'describe',return_value={'available':True,'runs':100}):
            self.assertEqual(self.request('GET','/api/rair_v3')[0],200)
            self.assertEqual(self.request('GET','/api/rair_v3',headers={'Origin':'https://evil.example'})[0],403)
        with patch.object(self.app.rair_v3,'describe',side_effect=ValueError('corrupt')):
            self.assertEqual(self.request('GET','/api/rair_v3')[0],503)
        with patch.object(self.app.rair_v3,'case',return_value={'results':{'RAIR':{},'KAIR':{}}}):
            self.assertEqual(self.request('GET','/api/rair_v3/case?question_id=q&seed=42')[0],200)
            for query in ('','?question_id=q','?question_id=q&seed=x','?question_id=q&seed=42&extra=1'):
                self.assertEqual(self.request('GET','/api/rair_v3/case'+query)[0],400)
            self.assertEqual(self.request('GET','/api/rair_v3/case?question_id=q&seed=42',headers={'Origin':'https://evil.example'})[0],403)
        with patch.object(self.app.rair_v3,'case',side_effect=KeyError('missing')):
            self.assertEqual(self.request('GET','/api/rair_v3/case?question_id=q&seed=42')[0],404)
        self.assertIsNone(self.app.active)

    def test_rair_scale_route_and_case(self):
        with patch.object(self.app.rair_scale,'describe',return_value={'available':True,'runs':200}):
            self.assertEqual(self.request('GET','/api/rair_scale')[0],200)
            self.assertEqual(self.request('GET','/api/rair_scale',headers={'Origin':'https://evil.example'})[0],403)
        with patch.object(self.app.rair_scale,'describe',side_effect=ValueError('corrupt')):
            self.assertEqual(self.request('GET','/api/rair_scale')[0],503)
        with patch.object(self.app.rair_scale,'case',return_value={'results':{'RAIR':{},'KAIR':{}}}):
            self.assertEqual(self.request('GET','/api/rair_scale/case?question_id=q&seed=42')[0],200)
            for query in ('','?question_id=q','?question_id=q&seed=x','?question_id=q&seed=42&extra=1'):
                self.assertEqual(self.request('GET','/api/rair_scale/case'+query)[0],400)
            self.assertEqual(self.request('GET','/api/rair_scale/case?question_id=q&seed=42',headers={'Origin':'https://evil.example'})[0],403)
        with patch.object(self.app.rair_scale,'case',side_effect=KeyError('missing')):
            self.assertEqual(self.request('GET','/api/rair_scale/case?question_id=q&seed=42')[0],404)
        self.assertIsNone(self.app.active)

    def test_rair_test_route_and_case(self):
        with patch.object(self.app.rair_test,'describe',return_value={'available':True,'runs':200}):
            self.assertEqual(self.request('GET','/api/rair_test')[0],200)
            self.assertEqual(self.request('GET','/api/rair_test',headers={'Origin':'https://evil.example'})[0],403)
        with patch.object(self.app.rair_test,'describe',side_effect=ValueError('corrupt')):
            self.assertEqual(self.request('GET','/api/rair_test')[0],503)
        with patch.object(self.app.rair_test,'case',return_value={'results':{'RAIR':{},'KAIR':{}}}):
            self.assertEqual(self.request('GET','/api/rair_test/case?question_id=q&seed=42')[0],200)
            for query in ('','?question_id=q','?question_id=q&seed=x','?question_id=q&seed=42&extra=1'):
                self.assertEqual(self.request('GET','/api/rair_test/case'+query)[0],400)
            self.assertEqual(self.request('GET','/api/rair_test/case?question_id=q&seed=42',headers={'Origin':'https://evil.example'})[0],403)
        with patch.object(self.app.rair_test,'case',side_effect=KeyError('missing')):
            self.assertEqual(self.request('GET','/api/rair_test/case?question_id=q&seed=42')[0],404)
        self.assertIsNone(self.app.active)


if __name__=='__main__':unittest.main()
