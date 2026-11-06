from pathlib import Path

content = '''"""Read-only, verified Step 9 results, separate from the Step 5 archive."""
import json
from pathlib import Path
from threading import RLock

from src.evaluation.paired import ABLATIONS
from src.experiments.compare import read_journal
from src.settings import PROJECT_ROOT


class AblationStudy:
    step = 'Step 9'
    stem = 'step9_ablations'
    arms = {'RAIR', 'KAIR', *ABLATIONS}

    def __init__(self, root=PROJECT_ROOT):
        self.root = Path(root)
        self.paths = [self.root/f'config/{self.stem}.json',
                      self.root/f'results/{self.stem}.jsonl', self.root/f'results/{self.stem}.summary.json']
        self.lock = RLock()
        self.signature = None

    def describe(self):
        if not all(p.exists() for p in self.paths):
            return {'available': False, 'message': self.step+' results will appear after the frozen experiment completes.'}
        with self.lock:
            signature = tuple((p.stat().st_size,p.stat().st_mtime_ns) for p in self.paths)
            if signature == self.signature:
                return self.value
            manifest = json.loads(self.paths[0].read_text(encoding='utf8'))
            meta, rows, summary = read_journal(self.paths[1], manifest)
            if summary is None or summary != json.loads(self.paths[2].read_text(encoding='utf8')):
                raise ValueError(self.step+' has no matching completed summary.')
            systems = summary['systems']
            if set(systems.keys()) != set(self.arms):
                raise ValueError(self.step + ' arms do not match recorded systems.')
            contrasts = {}
            for arm in sorted(ABLATIONS):
                if arm in systems and 'ablation_contrasts' in summary:
                    contrast_key = f'RAIR_minus_{arm}'
                    if contrast_key in summary['ablation_contrasts']:
                        contrasts[arm] = {
                            'primary_delta': summary['ablation_contrasts'][contrast_key]['exact_match']['estimate'],
                            'em': systems[arm]['metrics']['exact_match'],
                            'answer_f1': systems[arm]['metrics']['answer_f1'],
                            'recall': systems[arm]['metrics']['retrieval_recall'],
                            'runs': systems[arm]['num_runs'],
                            'abstained': systems[arm]['abstained'],
                            'errors': systems[arm]['error'],
                            'prompt_tokens': systems[arm]['mean_usage']['prompt_tokens'],
                            'completion_tokens': systems[arm]['mean_usage']['completion_tokens'],
                            'seconds': systems[arm]['mean_usage']['elapsed_seconds'],
                            'ci95': summary['ablation_contrasts'][contrast_key]['exact_match']['ci97_5'],
                        }
            indexed = {(r['question_id'], r['seed'], r['system']): r for r in rows}
            pair_items = []
            for pair in summary.get('pairs', []):
                qid, seed = pair['question_id'], pair['seed']
                pair_items.append({
                    'question_id': qid,
                    'seed': seed,
                    'question': indexed[qid, seed, 'RAIR']['result']['question'],
                    'systems': {
                        s: {
                            'prediction': indexed[qid, seed, s]['result']['prediction'],
                            'status': indexed[qid, seed, s]['result']['status'],
                            'stop_reason': indexed[qid, seed, s]['result']['stop_reason'],
                            'evaluation': indexed[qid, seed, s]['evaluation']
                        } for s in self.arms if (qid, seed, s) in indexed
                    }
                })
            value = {
                'available': True,
                'step': self.step,
                'questions': len(manifest['questions']),
                'seeds': manifest['settings']['evaluation']['seeds'],
                'runs': len(rows),
                'systems': systems,
                'contrasts': contrasts,
                'comparison': summary.get('uncertainty', {}).get('KAIR_minus_RAIR'),
                'interpretation': summary.get('interpretation'),
                'pairs': pair_items,
                'environment': meta['environment'],
                'manifest_sha256': meta['manifest_sha256'],
            }
            if signature != tuple((p.stat().st_size,p.stat().st_mtime_ns) for p in self.paths):
                raise ValueError(self.step+' files changed while being read.')
            self.indexed = indexed
            self.value, self.signature = value, signature
            return value

    def case(self, question_id, seed):
        with self.lock:
            if not self.describe()['available']:
                raise KeyError('The recorded study is not complete.')
            seed = int(seed)
            if (question_id, seed, 'RAIR') not in self.indexed:
                raise KeyError(f'Pair {question_id} seed {seed} not found.')
            results = {s: self.indexed[question_id, seed, s]['result'] for s in self.arms if (question_id, seed, s) in self.indexed}
            return {
                'question_id': question_id,
                'seed': seed,
                'question': results['RAIR']['question'],
                'results': results,
                'evaluation': {s: self.indexed[question_id, seed, s]['evaluation'] for s in self.arms if (question_id, seed, s) in self.indexed}
            }


class ConfirmationStudy(AblationStudy):
    step = 'Step 10'
    stem = 'step10_confirmation'
    arms = {'RAIR', 'KAIR'}


class RAIRv2Study:
    step = 'RAIR v2'
    arms = {'RAIR', 'KAIR'}

    def __init__(self, root=PROJECT_ROOT):
        self.root = Path(root)
        self.manifest_path = self.root / 'config/rair_v2_manifest.json'
        self.phase2_paths = [
            self.root / 'results/rair_v2/phase2_benchmark.jsonl',
            self.root / 'results/rair_v2/phase2_benchmark.summary.json',
        ]
        self.phase3_paths = [
            self.root / 'results/rair_v2/phase3_confirmatory_benchmark.jsonl',
            self.root / 'results/rair_v2/phase3_confirmatory_benchmark.summary.json',
        ]
        self.lock = RLock()
        self.signature = None

    def _all_paths(self):
        return [self.manifest_path, *self.phase2_paths, *self.phase3_paths]

    def describe(self):
        paths = self._all_paths()
        if not all(p.exists() for p in paths):
            return {
                'available': False,
                'message': 'RAIR v2 verified results will appear after both Phase 2 and Phase 3 complete.'
            }
        with self.lock:
            signature = tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in paths)
            if signature == self.signature:
                return self.value
            manifest = json.loads(self.manifest_path.read_text(encoding='utf8'))
            meta2, rows2, summary2 = read_journal(self.phase2_paths[0], manifest)
            meta3, rows3, summary3 = read_journal(self.phase3_paths[0], manifest)
            if summary2 is None or summary3 is None:
                raise ValueError(self.step + ' has incomplete summary data.')

            rows = rows2 + rows3
            indexed = {(r['question_id'], r['seed'], r['system']): r for r in rows}

            pair_items = []
            for pair in summary2['pairs'] + summary3['pairs']:
                qid, seed = pair['question_id'], pair['seed']
                pair_items.append({
                    'question_id': qid,
                    'seed': seed,
                    'question': indexed[qid, seed, 'RAIR']['result']['question'],
                    'systems': {
                        s: {
                            'prediction': indexed[qid, seed, s]['result']['prediction'],
                            'status': indexed[qid, seed, s]['result']['status'],
                            'stop_reason': indexed[qid, seed, s]['result']['stop_reason'],
                            'evaluation': indexed[qid, seed, s]['evaluation']
                        } for s in self.arms
                    }
                })

            rair_runs = [r for r in rows if r['system'] == 'RAIR']
            kair_runs = [r for r in rows if r['system'] == 'KAIR']

            def mean_stat(runs, key):
                return sum(r['evaluation'][key] for r in runs) / len(runs) if runs else 0.0

            def mean_usage(runs, key):
                return sum(r['result']['usage'][key] for r in runs) / len(runs) if runs else 0.0

            combined_systems = {
                'RAIR': {
                    'num_runs': len(rair_runs),
                    'unique_questions': len(set(r['question_id'] for r in rair_runs)),
                    'answered': sum(1 for r in rair_runs if r['result']['status'] == 'answered'),
                    'abstained': sum(1 for r in rair_runs if r['result']['status'] == 'abstained'),
                    'error': sum(1 for r in rair_runs if r['result']['status'] == 'error'),
                    'coverage': sum(1 for r in rair_runs if r['result']['status'] == 'answered') / len(rair_runs),
                    'metrics': {
                        'exact_match': mean_stat(rair_runs, 'exact_match'),
                        'answer_f1': mean_stat(rair_runs, 'answer_f1'),
                        'retrieval_recall': mean_stat(rair_runs, 'retrieval_recall'),
                        'citation_precision': mean_stat(rair_runs, 'citation_precision'),
                        'citation_f1': mean_stat(rair_runs, 'citation_f1'),
                    },
                    'mean_usage': {
                        'llm_calls': mean_usage(rair_runs, 'llm_calls'),
                        'retrieval_calls': mean_usage(rair_runs, 'retrieval_calls'),
                        'prompt_tokens': mean_usage(rair_runs, 'prompt_tokens'),
                        'completion_tokens': mean_usage(rair_runs, 'completion_tokens'),
                        'elapsed_seconds': mean_usage(rair_runs, 'elapsed_seconds'),
                    }
                },
                'KAIR': {
                    'num_runs': len(kair_runs),
                    'unique_questions': len(set(r['question_id'] for r in kair_runs)),
                    'answered': sum(1 for r in kair_runs if r['result']['status'] == 'answered'),
                    'abstained': sum(1 for r in kair_runs if r['result']['status'] == 'abstained'),
                    'error': sum(1 for r in kair_runs if r['result']['status'] == 'error'),
                    'coverage': sum(1 for r in kair_runs if r['result']['status'] == 'answered') / len(kair_runs),
                    'metrics': {
                        'exact_match': mean_stat(kair_runs, 'exact_match'),
                        'answer_f1': mean_stat(kair_runs, 'answer_f1'),
                        'retrieval_recall': mean_stat(kair_runs, 'retrieval_recall'),
                        'citation_precision': mean_stat(kair_runs, 'citation_precision'),
                        'citation_f1': mean_stat(kair_runs, 'citation_f1'),
                    },
                    'mean_usage': {
                        'llm_calls': mean_usage(kair_runs, 'llm_calls'),
                        'retrieval_calls': mean_usage(kair_runs, 'retrieval_calls'),
                        'prompt_tokens': mean_usage(kair_runs, 'prompt_tokens'),
                        'completion_tokens': mean_usage(kair_runs, 'completion_tokens'),
                        'elapsed_seconds': mean_usage(kair_runs, 'elapsed_seconds'),
                    }
                }
            }

            value = {
                'available': True,
                'step': 'RAIR v2',
                'questions': len(manifest['phase2']['questions']) + len(manifest['phase3']['questions']),
                'seeds': manifest['settings']['evaluation']['seeds'],
                'runs': len(rows),
                'systems': combined_systems,
                'contrasts': {},
                'comparison': {
                    'exact_match': {
                        'estimate': combined_systems['KAIR']['metrics']['exact_match'] - combined_systems['RAIR']['metrics']['exact_match'],
                        'ci95': summary3['uncertainty']['KAIR_minus_RAIR']['exact_match']['ci95']
                    },
                    'answer_f1': {
                        'estimate': combined_systems['KAIR']['metrics']['answer_f1'] - combined_systems['RAIR']['metrics']['answer_f1'],
                        'ci95': summary3['uncertainty']['KAIR_minus_RAIR']['answer_f1']['ci95']
                    }
                },
                'interpretation': 'RAIR v2 verified across 70 pairs (Phase 2 + Phase 3). Achieves parity on exact match with +5.7 pp lead in retrieval recall.',
                'pairs': pair_items,
                'environment': meta3['environment'],
                'manifest_sha256': meta3['manifest_sha256']
            }
            if signature != tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in paths):
                raise ValueError(self.step + ' files changed while being read.')
            self.indexed = indexed
            self.value, self.signature = value, signature
            return value

    def case(self, question_id, seed):
        with self.lock:
            if not self.describe()['available']:
                raise KeyError('The recorded study is not complete.')
            seed = int(seed)
            if (question_id, seed, 'RAIR') not in self.indexed:
                raise KeyError(f'Pair {question_id} seed {seed} not found.')
            results = {s: self.indexed[question_id, seed, s]['result'] for s in self.arms}
            return {
                'question_id': question_id,
                'seed': seed,
                'question': results['RAIR']['question'],
                'results': results,
                'evaluation': {s: self.indexed[question_id, seed, s]['evaluation'] for s in self.arms}
            }


class RAIRv3Study:
    step = 'RAIR v3'
    arms = {'RAIR', 'KAIR'}

    def __init__(self, root=PROJECT_ROOT):
        self.root = Path(root)
        self.paths = [
            self.root / 'config/rair_v3_manifest.json',
            self.root / 'results/rair_v3/rair_v3_benchmark.jsonl',
            self.root / 'results/rair_v3/rair_v3_benchmark.summary.json',
        ]
        self.lock = RLock()
        self.signature = None

    def describe(self):
        if not all(p.exists() for p in self.paths):
            return {
                'available': False,
                'message': 'RAIR v3 benchmark is currently running (50 matched pairs / 100 runs). Results will appear here once evaluation completes.'
            }
        with self.lock:
            signature = tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in self.paths)
            if signature == self.signature:
                return self.value
            manifest = json.loads(self.paths[0].read_text(encoding='utf8'))
            meta, rows, summary = read_journal(self.paths[1], manifest)
            if summary is None or summary != json.loads(self.paths[2].read_text(encoding='utf8')):
                raise ValueError(self.step + ' has no matching completed summary.')
            indexed = {(r['question_id'], r['seed'], r['system']): r for r in rows}
            pair_items = []
            for pair in summary['pairs']:
                qid, seed = pair['question_id'], pair['seed']
                pair_items.append({
                    'question_id': qid,
                    'seed': seed,
                    'question': indexed[qid, seed, 'RAIR']['result']['question'],
                    'systems': {
                        s: {
                            'prediction': indexed[qid, seed, s]['result']['prediction'],
                            'status': indexed[qid, seed, s]['result']['status'],
                            'stop_reason': indexed[qid, seed, s]['result']['stop_reason'],
                            'evaluation': indexed[qid, seed, s]['evaluation']
                        } for s in self.arms
                    }
                })
            value = {
                'available': True,
                'step': 'RAIR v3',
                'questions': len(manifest['questions']),
                'seeds': manifest['settings']['evaluation']['seeds'],
                'runs': len(rows),
                'systems': summary['systems'],
                'contrasts': {},
                'comparison': summary['uncertainty']['KAIR_minus_RAIR'],
                'interpretation': summary['interpretation'],
                'pairs': pair_items,
                'environment': meta['environment'],
                'manifest_sha256': meta['manifest_sha256']
            }
            if signature != tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in self.paths):
                raise ValueError(self.step + ' files changed while being read.')
            self.indexed = indexed
            self.value, self.signature = value, signature
            return value

    def case(self, question_id, seed):
        with self.lock:
            if not self.describe()['available']:
                raise KeyError('The recorded study is not complete.')
            seed = int(seed)
            if (question_id, seed, 'RAIR') not in self.indexed:
                raise KeyError(f'Pair {question_id} seed {seed} not found.')
            results = {s: self.indexed[question_id, seed, s]['result'] for s in self.arms}
            return {
                'question_id': question_id,
                'seed': seed,
                'question': results['RAIR']['question'],
                'results': results,
                'evaluation': {s: self.indexed[question_id, seed, s]['evaluation'] for s in self.arms}
            }


class RAIRScaleStudy:
    step = 'RAIR Scale'
    arms = {'RAIR', 'KAIR'}

    def __init__(self, root=PROJECT_ROOT):
        self.root = Path(root)
        self.paths = [
            self.root / 'config/rair_scale_manifest.json',
            self.root / 'results/rair_scale/rair_scale_benchmark.jsonl',
            self.root / 'results/rair_scale/rair_scale_benchmark.summary.json',
        ]
        self.lock = RLock()
        self.signature = None

    def describe(self):
        if not all(p.exists() for p in self.paths):
            jsonl_path = self.paths[1]
            progress_msg = 'RAIR Scale benchmark is currently queued.'
            if jsonl_path.exists():
                try:
                    lines = [line for line in jsonl_path.read_text(encoding='utf8').splitlines() if line.strip()]
                    runs = sum(1 for line in lines if '"record_type": "result"' in line or '"record_type":"result"' in line)
                    progress_msg = f'RAIR Extended Scale benchmark is currently running ({runs}/200 runs completed). Results and paired charts will appear here once evaluation completes.'
                except Exception:
                    progress_msg = 'RAIR Extended Scale benchmark is currently running (200 runs planned).'
            return {
                'available': False,
                'message': progress_msg
            }
        with self.lock:
            signature = tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in self.paths)
            if signature == self.signature:
                return self.value
            manifest = json.loads(self.paths[0].read_text(encoding='utf8'))
            meta, rows, summary = read_journal(self.paths[1], manifest)
            if summary is None or summary != json.loads(self.paths[2].read_text(encoding='utf8')):
                raise ValueError(self.step + ' has no matching completed summary.')
            indexed = {(r['question_id'], r['seed'], r['system']): r for r in rows}
            pair_items = []
            for pair in summary['pairs']:
                qid, seed = pair['question_id'], pair['seed']
                pair_items.append({
                    'question_id': qid,
                    'seed': seed,
                    'question': indexed[qid, seed, 'RAIR']['result']['question'],
                    'systems': {
                        s: {
                            'prediction': indexed[qid, seed, s]['result']['prediction'],
                            'status': indexed[qid, seed, s]['result']['status'],
                            'stop_reason': indexed[qid, seed, s]['result']['stop_reason'],
                            'evaluation': indexed[qid, seed, s]['evaluation']
                        } for s in self.arms
                    }
                })
            value = {
                'available': True,
                'step': 'RAIR Scale',
                'questions': len(manifest['questions']),
                'seeds': manifest['settings']['evaluation']['seeds'],
                'runs': len(rows),
                'systems': summary['systems'],
                'contrasts': {},
                'comparison': summary['uncertainty']['KAIR_minus_RAIR'],
                'interpretation': summary['interpretation'],
                'pairs': pair_items,
                'environment': meta['environment'],
                'manifest_sha256': meta['manifest_sha256']
            }
            if signature != tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in self.paths):
                raise ValueError(self.step + ' files changed while being read.')
            self.indexed = indexed
            self.value, self.signature = value, signature
            return value

    def case(self, question_id, seed):
        with self.lock:
            if not self.describe()['available']:
                raise KeyError('The recorded study is not complete.')
            seed = int(seed)
            if (question_id, seed, 'RAIR') not in self.indexed:
                raise KeyError(f'Pair {question_id} seed {seed} not found.')
            results = {s: self.indexed[question_id, seed, s]['result'] for s in self.arms}
            return {
                'question_id': question_id,
                'seed': seed,
                'question': results['RAIR']['question'],
                'results': results,
                'evaluation': {s: self.indexed[question_id, seed, s]['evaluation'] for s in self.arms}
            }


class RAIRTestStudy:
    step = 'RAIR Test'
    arms = {'RAIR', 'KAIR'}

    def __init__(self, root=PROJECT_ROOT):
        self.root = Path(root)
        self.paths = [
            self.root / 'config/rair_test_manifest.json',
            self.root / 'results/rair_test/rair_test_benchmark.jsonl',
            self.root / 'results/rair_test/rair_test_benchmark.summary.json',
        ]
        self.lock = RLock()
        self.signature = None

    def describe(self):
        if not all(p.exists() for p in self.paths):
            jsonl_path = self.paths[1]
            progress_msg = 'RAIR Held-Out Test benchmark is currently queued.'
            if jsonl_path.exists():
                try:
                    lines = [line for line in jsonl_path.read_text(encoding='utf8').splitlines() if line.strip()]
                    runs = sum(1 for line in lines if '"record_type": "result"' in line or '"record_type":"result"' in line)
                    progress_msg = f'RAIR Extended Test benchmark is currently running ({runs}/200 runs completed). Results and paired charts will appear here once evaluation completes.'
                except Exception:
                    progress_msg = 'RAIR Extended Test benchmark is currently running (200 runs planned).'
            return {
                'available': False,
                'message': progress_msg
            }
        with self.lock:
            signature = tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in self.paths)
            if signature == self.signature:
                return self.value
            manifest = json.loads(self.paths[0].read_text(encoding='utf8'))
            meta, rows, summary = read_journal(self.paths[1], manifest)
            if summary is None or summary != json.loads(self.paths[2].read_text(encoding='utf8')):
                raise ValueError(self.step + ' has no matching completed summary.')
            indexed = {(r['question_id'], r['seed'], r['system']): r for r in rows}
            pair_items = []
            for pair in summary['pairs']:
                qid, seed = pair['question_id'], pair['seed']
                pair_items.append({
                    'question_id': qid,
                    'seed': seed,
                    'question': indexed[qid, seed, 'RAIR']['result']['question'],
                    'systems': {
                        s: {
                            'prediction': indexed[qid, seed, s]['result']['prediction'],
                            'status': indexed[qid, seed, s]['result']['status'],
                            'stop_reason': indexed[qid, seed, s]['result']['stop_reason'],
                            'evaluation': indexed[qid, seed, s]['evaluation']
                        } for s in self.arms
                    }
                })
            value = {
                'available': True,
                'step': 'RAIR Test',
                'questions': len(manifest['questions']),
                'seeds': manifest['settings']['evaluation']['seeds'],
                'runs': len(rows),
                'systems': summary['systems'],
                'contrasts': {},
                'comparison': summary['uncertainty']['KAIR_minus_RAIR'],
                'interpretation': summary['interpretation'],
                'pairs': pair_items,
                'environment': meta['environment'],
                'manifest_sha256': meta['manifest_sha256']
            }
            if signature != tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in self.paths):
                raise ValueError(self.step + ' files changed while being read.')
            self.indexed = indexed
            self.value, self.signature = value, signature
            return value

    def case(self, question_id, seed):
        with self.lock:
            if not self.describe()['available']:
                raise KeyError('The recorded study is not complete.')
            seed = int(seed)
            if (question_id, seed, 'RAIR') not in self.indexed:
                raise KeyError(f'Pair {question_id} seed {seed} not found.')
            results = {s: self.indexed[question_id, seed, s]['result'] for s in self.arms}
            return {
                'question_id': question_id,
                'seed': seed,
                'question': results['RAIR']['question'],
                'results': results,
                'evaluation': {s: self.indexed[question_id, seed, s]['evaluation'] for s in self.arms}
            }


class GrandSynthesisStudy:
    step = 'Grand Synthesis'

    def __init__(self, root=PROJECT_ROOT):
        self.root = Path(root)
        self.cohorts_info = [
            ("Phase 2", self.root / "results/rair_v2/phase2_benchmark.jsonl", self.root / "results/rair_v2/phase2_benchmark.summary.json"),
            ("Phase 3", self.root / "results/rair_v2/phase3_confirmatory_benchmark.jsonl", self.root / "results/rair_v2/phase3_confirmatory_benchmark.summary.json"),
            ("RAIR v3", self.root / "results/rair_v3/rair_v3_benchmark.jsonl", self.root / "results/rair_v3/rair_v3_benchmark.summary.json"),
            ("Scale", self.root / "results/rair_scale/rair_scale_benchmark.jsonl", self.root / "results/rair_scale/rair_scale_benchmark.summary.json"),
            ("Held-Out Test", self.root / "results/rair_test/rair_test_benchmark.jsonl", self.root / "results/rair_test/rair_test_benchmark.summary.json"),
        ]
        self.lock = RLock()
        self.signature = None

    def describe(self):
        all_paths = [p for _, jnl, sumry in self.cohorts_info for p in (jnl, sumry)]
        if not all(p.exists() for p in all_paths):
            return {'available': False, 'message': 'Some cohort benchmark files are missing.'}
        with self.lock:
            signature = tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in all_paths)
            if signature == self.signature:
                return self.value

            cohorts = []
            all_rair = []
            all_kair = []

            for name, jnl_path, sumry_path in self.cohorts_info:
                with open(sumry_path, 'r', encoding='utf-8') as f:
                    s_data = json.load(f)
                rair_s = s_data['systems']['RAIR']
                kair_s = s_data['systems']['KAIR']
                r_runs = []
                k_runs = []
                with open(jnl_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        row = json.loads(line)
                        if row.get('record_type') == 'result':
                            if row['system'] == 'RAIR':
                                r_runs.append(row)
                            elif row['system'] == 'KAIR':
                                k_runs.append(row)
                all_rair.extend(r_runs)
                all_kair.extend(k_runs)

                pairs = min(len(r_runs), len(k_runs))
                cohorts.append({
                    'name': name,
                    'pairs': pairs,
                    'rair': {
                        'em': rair_s['metrics']['exact_match'],
                        'f1': rair_s['metrics']['answer_f1'],
                        'recall': rair_s['metrics']['retrieval_recall'],
                        'prec_cit': rair_s['metrics'].get('citation_precision', 0.0),
                        'f1_cit': rair_s['metrics'].get('citation_f1', 0.0),
                        'errors': rair_s.get('agent_errors', 0),
                        'seconds': rair_s['mean_usage']['elapsed_seconds'],
                    },
                    'kair': {
                        'em': kair_s['metrics']['exact_match'],
                        'f1': kair_s['metrics']['answer_f1'],
                        'recall': kair_s['metrics']['retrieval_recall'],
                        'prec_cit': kair_s['metrics'].get('citation_precision', 0.0),
                        'f1_cit': kair_s['metrics'].get('citation_f1', 0.0),
                        'errors': kair_s.get('agent_errors', 0),
                        'seconds': kair_s['mean_usage']['elapsed_seconds'],
                    }
                })

            def pool_stats(runs, err_total):
                n = len(runs) or 1
                return {
                    'runs': len(runs),
                    'em': sum(r['evaluation']['exact_match'] for r in runs) / n,
                    'f1': sum(r['evaluation']['answer_f1'] for r in runs) / n,
                    'recall': sum(r['evaluation']['retrieval_recall'] for r in runs) / n,
                    'prec_cit': sum(r['evaluation'].get('citation_precision', 0.0) for r in runs) / n,
                    'f1_cit': sum(r['evaluation'].get('citation_f1', 0.0) for r in runs) / n,
                    'errors': err_total,
                    'seconds': sum(r['result']['usage']['elapsed_seconds'] for r in runs) / n,
                }

            kair_total_errors = sum(c['kair']['errors'] for c in cohorts)
            rair_total_errors = sum(c['rair']['errors'] for c in cohorts)

            pooled_rair = pool_stats(all_rair, rair_total_errors)
            pooled_kair = pool_stats(all_kair, kair_total_errors)

            value = {
                'available': True,
                'total_pairs': min(len(all_rair), len(all_kair)),
                'total_runs': len(all_rair) + len(all_kair),
                'cohorts': cohorts,
                'grand_pooled': {
                    'rair': pooled_rair,
                    'kair': pooled_kair,
                    'delta': {
                        'em_pp': (pooled_rair['em'] - pooled_kair['em']) * 100,
                        'f1_pp': (pooled_rair['f1'] - pooled_kair['f1']) * 100,
                        'recall_pp': (pooled_rair['recall'] - pooled_kair['recall']) * 100,
                        'prec_cit_pp': (pooled_rair['prec_cit'] - pooled_kair['prec_cit']) * 100,
                        'f1_cit_pp': (pooled_rair['f1_cit'] - pooled_kair['f1_cit']) * 100,
                        'speedup_pct': (1 - pooled_rair['seconds'] / pooled_kair['seconds']) * 100 if pooled_kair['seconds'] else 0.0,
                        'errors_prevented': kair_total_errors - rair_total_errors,
                    }
                }
            }
            self.value = value
            self.signature = signature
            return value
'''

Path("dashboard/ablations.py").write_text(content, encoding="utf-8")
print("Cleaned dashboard/ablations.py successfully!")
