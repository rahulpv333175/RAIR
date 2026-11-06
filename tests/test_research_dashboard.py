"""Research views read frozen evidence and never invoke either inference engine."""
import copy
import json
import os
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from statistics import fmean
from unittest.mock import patch

from dashboard.research import ResearchArchive
from src.datasets.hotpotqa import parse_hotpotqa_record
from src.evaluation.paired import fingerprint
from src.settings import load_settings
import test_dashboard


def fixture(root):
    (root/'results').mkdir();(root/'data/raw').mkdir(parents=True);(root/'data/processed').mkdir()
    examples=[];rows=[];schedule=[];questions=[]
    patterns=[(True,True),(True,False),(False,True),(False,False)]
    for i,(left,right) in enumerate(patterns):
        qid=f'q{i}';seed=42+i//2
        raw={'_id':qid,'question':f'Which city is linked to book {i}? <source>', 'answer':'Nerava',
             'context':[['Book',['Mira wrote this book.']],['Mira',['Mira was born in Nerava.']]],
             'supporting_facts':[['Book',0],['Mira',0]],'type':'bridge','level':'hard'}
        examples.append(raw);task=parse_hotpotqa_record(raw).task
        questions.append({'question_id':qid,'input_sha256':fingerprint(asdict(task))})
        for s,correct in [('RAIR',left),('KAIR',right),('RAIR_REFERENCE',False)]:
            entry={'question_id':qid,'seed':seed,'system':s};schedule.append(entry)
            status='abstained' if i==2 and s=='RAIR' else 'error' if i==3 and s=='KAIR' else 'answered'
            metrics={key:float(correct) for key in ('exact_match','answer_f1','citation_precision','citation_recall','citation_f1')}
            metrics.update(retrieval_precision=.5,retrieval_recall=.5,retrieval_f1=.5)
            result={'question_id':qid,'question':raw['question'],'status':status,'stop_reason':'diagnostic',
                    'prediction':{'answer':'Nerava' if correct else 'wrong' if status=='answered' else '', 'abstain':status!='answered','citations':[]},
                    'sources':[],'error':None,'usage':{'llm_calls':5,'retrieval_calls':1,'prompt_tokens':100,'completion_tokens':20,'elapsed_seconds':1.0,'token_counts_complete':True}}
            if s!='KAIR':
                result.update(state={'gaps':[{'gap_id':'G1','description':'Find city','depends_on':[],'resolved':correct}],
                                     'verified_facts':[],'query_history':[]},rounds=[{'decisions':[{'accepted':correct}]}])
            else:
                result.update(selected_agent_id='A1',agents=[{'agent_id':'A1','required':[] if correct else ['Find city']}],
                              iterations=[{'steps':[{'candidates':[{}],'fact_check':{'accepted_candidate_ids':['C1'] if correct else []}}]}],agent_errors=[])
            rows.append({'record_type':'result',**entry,'input_sha256':fingerprint(asdict(task)),'result':result,'evaluation':metrics})
    settings=load_settings();settings['evaluation']['seeds']=[42,43]
    manifest={'settings':settings,'schedule':schedule,'questions':questions}
    env={'server':{'version':'test'},'model':{'digest':'test-digest'}}
    metadata={'record_type':'metadata','manifest':manifest,'manifest_sha256':fingerprint(manifest),'environment':env,'created_at_utc':'2026-10-18T00:00:00Z'}
    systems={}
    for s in ('RAIR','KAIR','RAIR_REFERENCE'):
        group=[r for r in rows if r['system']==s]
        systems[s]={'num_runs':4,'metrics':{key:fmean(r['evaluation'][key] for r in group) for key in group[0]['evaluation']}}
    summary={'systems':systems,'uncertainty':{'KAIR_minus_RAIR':{}},'RAIR_minus_REFERENCE':{'metrics':{}}}
    (root/'data/raw/hotpot_dev_distractor_v1.json').write_text(json.dumps(examples))
    (root/'results/step5_fresh_benchmark.summary.json').write_text(json.dumps(summary))
    records=[metadata,*rows,{'record_type':'verification','consistent':True,'environment':env},{'record_type':'summary','summary':summary}]
    (root/'results/step5_fresh_benchmark.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    return records


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.records=fixture(self.root);self.archive=ResearchArchive(self.root)

    def test_outcome_groups_and_diagnostic_counts_match_recorded_rows(self):
        data=self.archive.describe()
        self.assertEqual(data['groups'],dict(both_correct=1,rair_only=1,kair_only=1,both_failed=1))
        self.assertEqual(data['pairs'],4);self.assertEqual(data['runs'],12)
        self.assertEqual(data['failure_counts']['RAIR']['abstained'],1)
        self.assertEqual(data['failure_counts']['KAIR']['error'],1)
        self.assertEqual(data['failure_counts']['RAIR']['incomplete_retrieval'],4)

    def test_filters_pagination_and_case_identity_are_preserved(self):
        self.assertEqual(self.archive.list_cases(group='rair_only')['cases'][0]['question_id'],'q1')
        self.assertEqual(self.archive.list_cases(seed=43)['total'],2)
        self.assertEqual(self.archive.list_cases(issue='abstained')['total'],1)
        self.assertEqual(self.archive.list_cases(search='book 2')['cases'][0]['question_id'],'q2')
        self.assertEqual(self.archive.list_cases(limit=2,offset=2)['cases'][0]['question_id'],'q2')
        self.assertEqual(self.archive.list_cases(search='not present')['total'],0)
        case=self.archive.case('q0',42)
        self.assertEqual(case['gold_answer'],'Nerava');self.assertTrue(case['historical'])
        self.assertEqual(case['task']['documents'][0]['sentences'],('Mira wrote this book.',))
        self.assertEqual(case['results']['RAIR'],self.records[1]['result'])

    def test_bad_queries_never_resolve_arbitrary_files(self):
        for kwargs in ({'group':'unknown'},{'issue':'unknown'},{'offset':-1},{'limit':51},{'seed':41},{'search':'x'*501}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.archive.list_cases(**kwargs)
        for qid in ('../../config/settings.yaml','not-present'):
            with self.assertRaises(KeyError):self.archive.case(qid,42)

    def test_cache_uses_offsets_and_refuses_changed_archive(self):
        self.archive.describe()
        with patch.object(Path,'read_text',side_effect=AssertionError('Do not reparse full files.')):
            self.assertEqual(self.archive.list_cases()['total'],4)
            self.assertEqual(self.archive.case('q0',42)['gold_answer'],'Nerava')
        path=self.root/'results/step5_fresh_benchmark.jsonl';stat=path.stat()
        os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns+10_000_000))
        with self.assertRaisesRegex(ValueError,'changed'):self.archive.describe()

    def test_partial_or_modified_metrics_fail_closed(self):
        path=self.root/'results/step5_fresh_benchmark.summary.json'
        summary=json.loads(path.read_text());summary['systems']['RAIR']['metrics']['exact_match']=1
        path.write_text(json.dumps(summary))
        with self.assertRaisesRegex(ValueError,'inconsistent'):self.archive.describe()

    def test_duplicate_missing_results_and_wrong_source_pool_fail_closed(self):
        path=self.root/'results/step5_fresh_benchmark.jsonl'
        duplicate=[*self.records[:-1],self.records[1],self.records[-1]]
        path.write_text(''.join(json.dumps(r)+'\n' for r in duplicate))
        with self.assertRaisesRegex(ValueError,'duplicate'):self.archive.describe()
        path.write_text(''.join(json.dumps(r)+'\n' for r in self.records if r is not self.records[1]))
        with self.assertRaisesRegex(ValueError,'every planned'):ResearchArchive(self.root).describe()
        path.write_text(''.join(json.dumps(r)+'\n' for r in self.records))
        data=self.root/'data/raw/hotpot_dev_distractor_v1.json';examples=json.loads(data.read_text());examples[0]['context'][0][1][0]='changed';data.write_text(json.dumps(examples))
        with self.assertRaisesRegex(ValueError,'source pool'):ResearchArchive(self.root).describe()

    def test_annotations_are_optional_and_bound_to_exact_journal(self):
        notes={'journal_sha256':'wrong','selection':'purposeful sample','cases':[{'question_id':'q0','seed':42,'assessment':'review'}]}
        path=self.root/'data/processed/step8_failure_notes.json';path.write_text(json.dumps(notes))
        self.assertEqual(self.archive.describe()['review_notes'],[])
        notes['journal_sha256']=self.archive.describe()['journal_sha256'];path.write_text(json.dumps(notes))
        archive=ResearchArchive(self.root)
        self.assertEqual(archive.case('q0',42)['review_notes'],notes['cases'])


class ResearchHTTPTests(test_dashboard.HTTPTests):
    def setUp(self):
        super().setUp();temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);fixture(self.root);self.app.research=ResearchArchive(self.root)

    def test_archive_routes_do_not_start_model_or_mutate_live_inputs(self):
        before=copy.deepcopy(self.app.examples)
        with patch('dashboard.server.OllamaClient',side_effect=AssertionError('No model inference while browsing.')):
            for path in ('/research.js','/api/research','/api/research/cases?group=rair_only','/api/research/case?question_id=q0&seed=42'):
                self.assertEqual(self.request('GET',path)[0],200)
        self.assertEqual(self.app.examples,before);self.assertIsNone(self.app.active);self.assertEqual(self.app.jobs,{})
        status,headers,body=self.request('GET','/api/research/case?question_id=q0&seed=42&download=1')
        self.assertEqual(status,200)
        self.assertIn('attachment;',headers['Content-Disposition'])
        self.assertEqual(json.loads(body)['question_id'],'q0')

    def test_invalid_research_queries_and_absent_archive_are_explicit(self):
        for query in ('group=bad','seed=nan','limit=100','offset=-1','group=all&group=both_failed','file=../../config/settings.yaml'):
            self.assertEqual(self.request('GET','/api/research/cases?'+query)[0],400)
        self.assertEqual(self.request('GET','/api/research/case?question_id=q0')[0],400)
        self.assertEqual(self.request('GET','/api/research/case?question_id=q0&seed=42&download=bad')[0],400)
        self.assertEqual(self.request('GET','/api/research/case?question_id=../../settings.yaml&seed=42')[0],404)
        self.assertEqual(self.request('GET','/api/research',headers={'Origin':'https://evil.example'})[0],403)
        self.app.research=ResearchArchive(self.root/'missing')
        self.assertEqual(self.request('GET','/api/research')[0],503)
        self.assertEqual(self.request('GET','/api/bootstrap')[0],200)


if __name__=='__main__':unittest.main()
