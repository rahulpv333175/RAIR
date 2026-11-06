"""Progress is observational; scripted transport keeps these tests model-free."""
import copy
import json
import threading
import unittest
from unittest.mock import Mock, patch

import test_dashboard
from src.kair.controller import KAIRController
from src.rair.controller import RAIRController
from src.settings import load_settings
from src.experiments.check_rair_pipeline import make_task


class ObserverTests(unittest.TestCase):
    def test_observers_do_not_change_requests_answers_or_state(self):
        for controller, client_type, script in (
            (RAIRController, test_dashboard.RAIRClient, test_dashboard.full_script()),
            (KAIRController, test_dashboard.KAIRClient, test_dashboard.complete_cycle()+[test_dashboard.answer()]),
        ):
            settings=load_settings()
            baseline_client=client_type(settings,copy.deepcopy(script))
            baseline=controller(settings,baseline_client).run(make_task()).to_dict()
            events=[]
            def observe(stage, details):
                events.append((stage,copy.deepcopy(details)))
                details.clear()  # Delivery must not hand mutable engine state to observers.
            observed_client=client_type(settings,copy.deepcopy(script))
            observed=controller(settings,observed_client,on_progress=observe).run(make_task()).to_dict()
            self.assertEqual(baseline_client.requests,observed_client.requests)
            for key in baseline.keys()-{'usage','llm_calls'}:
                self.assertEqual(baseline[key],observed[key],(controller.__name__,key))
            self.assertTrue(events)
            self.assertIn('retrieve',[s for s,_ in events])
            self.assertIn('verify' if controller is RAIRController else 'selection',[s for s,_ in events])

    def test_delivery_failure_does_not_stop_either_engine(self):
        for controller,client_type,script in (
            (RAIRController,test_dashboard.RAIRClient,test_dashboard.full_script()),
            (KAIRController,test_dashboard.KAIRClient,test_dashboard.complete_cycle()+[test_dashboard.answer()]),
        ):
            observer=Mock(side_effect=RuntimeError('UI disconnected'))
            settings=load_settings();client=client_type(settings,script)
            with self.assertLogs('src.progress',level='WARNING'):
                result=controller(settings,client,on_progress=observer).run(make_task())
            self.assertEqual(result.prediction.answer,'Nerava')
            self.assertEqual(result.status,'answered')
            self.assertTrue(observer.called)


class ProgressServiceTests(unittest.TestCase):
    setUp=test_dashboard.ServiceTests.setUp
    execute=test_dashboard.ServiceTests.execute

    def test_delta_replay_is_detached_and_idle_response_excludes_full_traces(self):
        full,_=self.execute()
        run_id=full['id'];first=self.app.snapshot(run_id,light=True)
        self.assertGreater(first['cursor'],0)
        self.assertEqual([e['sequence'] for e in first['events']],list(range(1,first['cursor']+1)))
        self.assertEqual({e['system'] for e in first['events']},{'RAIR','KAIR'})
        for key in ('results','task','environment','source_sha256'):
            self.assertNotIn(key,first)
        split=first['cursor']//2
        replay=self.app.snapshot(run_id,light=True,after=split)
        self.assertEqual(replay['events'],first['events'][split:])
        first['events'][0]['details'].clear()
        self.assertTrue(self.app.snapshot(run_id,light=True)['events'][0]['details'])
        idle=self.app.snapshot(run_id,light=True,after=first['cursor'])
        self.assertEqual(idle['events'],[])
        self.assertLess(len(json.dumps(idle)),len(json.dumps(full))//10)
        result=self.app.result(run_id,'RAIR');result['prediction']['answer']='changed'
        self.assertEqual(self.app.result(run_id,'RAIR')['prediction']['answer'],'Nerava')
        for after in (-1,True,first['cursor']+1):
            with self.assertRaises(ValueError):self.app.snapshot(run_id,light=True,after=after)

    def test_stage_visible_before_engine_finishes_and_gold_is_withheld(self):
        published=threading.Event();release=threading.Event();original=self.app._publish
        ready=test_dashboard.OllamaClient(self.settings)
        ready.check_ready=Mock(return_value=test_dashboard.ENVIRONMENT)
        ready._request=Mock(return_value={'done':True,'done_reason':'stop','message':{'content':'{"ready":true}'},
                                          'prompt_eval_count':10,'eval_count':4})
        clients=[ready,test_dashboard.RAIRClient(self.settings,test_dashboard.full_script()),
                 test_dashboard.KAIRClient(self.settings,test_dashboard.complete_cycle()+[test_dashboard.answer()])]
        def pause(run_id,system,stage,details):
            original(run_id,system,stage,details)
            if system=='RAIR' and stage=='decompose':
                published.set();release.wait(timeout=5)
        with patch('dashboard.server.OllamaClient',side_effect=clients),patch.object(self.app,'_publish',side_effect=pause):
            run_id=self.app.start({'example_id':'demo-complete'})
            try:
                self.assertTrue(published.wait(timeout=3))
                live=self.app.snapshot(run_id,light=True)
                self.assertEqual(live['status'],'running')
                self.assertEqual(live['events'][0]['stage'],'decompose')
                self.assertEqual(live['result_statuses'],{})
                self.assertNotIn('gold_answer',live);self.assertNotIn('evaluation',live)
            finally:
                release.set();self.app.thread.join(timeout=5)
            self.assertFalse(self.app.thread.is_alive())
        self.assertEqual(self.app.snapshot(run_id)['status'],'completed')


class ProgressHTTPTests(unittest.TestCase):
    setUp=test_dashboard.HTTPTests.setUp
    stop=test_dashboard.HTTPTests.stop
    request=test_dashboard.HTTPTests.request

    def test_progress_and_single_result_routes_keep_full_download_compatible(self):
        status,_,bootstrap=self.request('GET','/api/bootstrap')
        self.assertEqual(status,200)
        self.assertIn('live_progress_v1',json.loads(bootstrap)['api_features'])
        with patch.object(self.app,'snapshot',return_value={'id':'saved','events':[],'cursor':3}) as snapshot:
            status,_,body=self.request('GET','/api/runs/saved/progress?after=3')
            self.assertEqual(status,200);self.assertEqual(json.loads(body)['events'],[])
            snapshot.assert_called_once_with('saved',light=True,after=3)
        with patch.object(self.app,'result',return_value={'status':'answered'}) as result:
            self.assertEqual(self.request('GET','/api/runs/saved/results/RAIR')[0],200)
            result.assert_called_once_with('saved','RAIR')
        with patch.object(self.app,'snapshot',return_value={'id':'saved','results':{}}) as snapshot:
            status,headers,_=self.request('GET','/api/runs/saved/download')
            self.assertEqual(status,200);self.assertIn('attachment',headers['Content-Disposition'])
            snapshot.assert_called_once_with('saved')

    def test_invalid_cursors_unknown_results_and_cross_origin_are_rejected(self):
        for query in ('after=bad','after=','after=1&after=2','file=secrets'):
            self.assertEqual(self.request('GET','/api/runs/missing/progress?'+query)[0],400)
        self.assertEqual(self.request('GET','/api/runs/missing/progress')[0],404)
        self.assertEqual(self.request('GET','/api/runs/missing/results/RAIR')[0],404)
        self.assertEqual(self.request('GET','/api/runs/missing/results/unknown')[0],404)
        self.assertEqual(self.request('GET','/api/runs/missing/progress',headers={'Origin':'https://evil.example'})[0],403)


if __name__=='__main__':
    unittest.main()
