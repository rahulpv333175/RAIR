"""Read-only, indexed access to the frozen experiment; no inference calls."""

import hashlib
import json
import math
import threading
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from statistics import fmean

from src.datasets.hotpotqa import parse_hotpotqa_record
from src.evaluation.paired import fingerprint
from src.settings import PROJECT_ROOT

GROUPS = ('both_correct', 'rair_only', 'kair_only', 'both_failed')
ISSUES = ('abstained', 'error', 'incomplete_retrieval', 'unresolved_requirements',
          'rejected_candidates', 'zero_overlap_answer', 'partial_overlap_answer')


def diagnostics(result, evaluation):
    if 'state' in result:
        unresolved = sum(not g['resolved'] for g in result['state']['gaps'])
        rejected = sum(not d['accepted'] for r in result['rounds'] for d in r.get('decisions', []))
    else:
        selected = next((a for a in result['agents'] if a['agent_id'] == result['selected_agent_id']), None)
        unresolved = len(selected['required']) if selected else 0
        rejected = sum(len(step.get('candidates', [])) - len(step['fact_check']['accepted_candidate_ids'])
                       for it in result['iterations'] for step in it['steps'] if 'fact_check' in step)
    flags = {key: False for key in ISSUES}
    flags.update(abstained=result['status'] == 'abstained', error=result['status'] == 'error',
                 incomplete_retrieval=evaluation['retrieval_recall'] is not None and evaluation['retrieval_recall'] < 1,
                 unresolved_requirements=unresolved > 0, rejected_candidates=rejected > 0,
                 zero_overlap_answer=result['status'] == 'answered' and evaluation['answer_f1'] == 0,
                 partial_overlap_answer=result['status'] == 'answered' and 0 < evaluation['answer_f1'] < 1)
    return {'unresolved_count': unresolved, 'rejected_count': rejected, 'flags': flags}


class ResearchArchive:
    def __init__(self, root=PROJECT_ROOT):
        self.root = Path(root)
        self.paths = [self.root / 'results/step5_fresh_benchmark.summary.json',
                      self.root / 'results/step5_fresh_benchmark.jsonl',
                      self.root / 'data/raw/hotpot_dev_distractor_v1.json']
        self.lock = threading.RLock()
        self.loaded = False

    def _signature(self):
        return tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in self.paths)

    def _ensure(self):
        with self.lock:
            signature = self._signature()
            if self.loaded:
                if signature != self.signature:
                    raise ValueError('Recorded experiment files changed; restart to inspect a consistent archive.')
                return
            summary = json.loads(self.paths[0].read_text(encoding='utf8'))
            digest = hashlib.sha256()
            offsets, pairs, checks = {}, {}, {s: [] for s in summary['systems']}
            metadata, closing, verification = None, None, None
            with self.paths[1].open('rb') as handle:
                while True:
                    offset = handle.tell()
                    line = handle.readline()
                    if not line:
                        break
                    digest.update(line)
                    row = json.loads(line)
                    kind = row['record_type']
                    if kind == 'metadata':
                        if metadata is not None:
                            raise ValueError('Duplicate experiment metadata.')
                        metadata = row
                    elif kind == 'verification':
                        verification = row
                    elif kind == 'summary':
                        closing = row['summary']
                    elif kind == 'result':
                        s, qid, seed = row['system'], row['question_id'], row['seed']
                        key = (qid, seed, s)
                        if key in offsets or s not in checks:
                            raise ValueError('Unexpected or duplicate benchmark result.')
                        offsets[key] = offset
                        checks[s].append(row['evaluation'])
                        if s not in ('RAIR', 'KAIR'):
                            continue
                        result, evaluation = row['result'], row['evaluation']
                        pair = pairs.setdefault((qid, seed), {'question_id': qid, 'seed': seed,
                                                'question': result['question'], 'systems': {}})
                        if pair['question'] != result['question']:
                            raise ValueError('Paired benchmark inputs differ.')
                        pair['systems'][s] = {'status': result['status'], 'answer': result['prediction']['answer'],
                                              'evaluation': evaluation, 'usage': result['usage'],
                                              **diagnostics(result, evaluation)}
            if (not metadata or not verification or not verification['consistent'] or closing != summary
                    or verification['environment'] != metadata['environment']):
                raise ValueError('The benchmark journal and summary are incomplete or inconsistent.')
            manifest = metadata['manifest']
            if metadata['manifest_sha256'] != fingerprint(manifest):
                raise ValueError('The recorded manifest fingerprint does not match.')
            expected = {(r['question_id'], r['seed'], r['system']) for r in manifest['schedule']}
            if set(offsets) != expected:
                raise ValueError('The archive does not contain every planned result exactly once.')
            for s, values in checks.items():
                if len(values) != summary['systems'][s]['num_runs']:
                    raise ValueError('Recorded run counts disagree with the summary.')
                for metric, score in summary['systems'][s]['metrics'].items():
                    valid = [r[metric] for r in values if r[metric] is not None]
                    if valid and not math.isclose(fmean(valid), score, abs_tol=1e-12):
                        raise ValueError('Recorded metric values disagree with the summary.')
            ids = {key[0] for key in pairs}
            records = json.loads(self.paths[2].read_text(encoding='utf8'))
            examples = {r['_id']: parse_hotpotqa_record(r) for r in records if r['_id'] in ids}
            del records
            for q in manifest['questions']:
                if q['question_id'] not in examples or fingerprint(asdict(examples[q['question_id']].task)) != q['input_sha256']:
                    raise ValueError('The source pool differs from the frozen experiment.')
            groups = Counter({g: 0 for g in GROUPS})
            failures = {s: Counter({flag: 0 for flag in ISSUES}) for s in ('RAIR', 'KAIR')}
            for pair in pairs.values():
                if set(pair['systems']) != {'RAIR', 'KAIR'}:
                    raise ValueError('An incomplete RAIR/KAIR pair was found.')
                left, right = [pair['systems'][s]['evaluation']['exact_match'] == 1 for s in ('RAIR', 'KAIR')]
                pair['group'] = 'both_correct' if left and right else 'rair_only' if left else 'kair_only' if right else 'both_failed'
                pair['question_type'] = examples[pair['question_id']].gold.question_type
                groups[pair['group']] += 1
                for s in failures:
                    failures[s].update({flag: int(value) for flag, value in pair['systems'][s]['flags'].items()})
            notes = {'selection': 'No manual review annotations supplied.', 'cases': []}
            notes_path = self.root / 'data/processed/step8_failure_notes.json'
            if notes_path.exists():
                candidate = json.loads(notes_path.read_text(encoding='utf8'))
                if candidate['journal_sha256'] == digest.hexdigest():
                    notes = candidate
            if signature != self._signature():
                raise ValueError('The experiment changed while it was being read.')
            self.offsets, self.pairs, self.examples = offsets, pairs, examples
            self.metadata, self.summary, self.notes = metadata, summary, notes
            self.overview = {'available': True, 'systems': summary['systems'], 'groups': dict(groups),
                             'failure_counts': failures, 'questions': len(ids), 'pairs': len(pairs),
                             'seeds': manifest['settings']['evaluation']['seeds'], 'runs': len(offsets),
                             'core': summary['RAIR_minus_REFERENCE']['metrics'],
                             'comparison': summary['uncertainty']['KAIR_minus_RAIR'],
                             'uncertainty': summary['uncertainty'], 'settings': manifest['settings'],
                             'environment': metadata['environment'], 'created_at_utc': metadata['created_at_utc'],
                             'journal_sha256': digest.hexdigest(), 'manifest_sha256': metadata['manifest_sha256'],
                             'review_notes': notes['cases'], 'review_selection': notes['selection']}
            self.signature, self.loaded = signature, True

    def describe(self):
        self._ensure()
        return self.overview

    def list_cases(self, *, group='all', search='', issue='all', seed='', offset=0, limit=20):
        self._ensure()
        if (group not in (*GROUPS, 'all') or issue not in (*ISSUES, 'all') or len(search) > 500
                or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 50
                or (seed != '' and seed not in self.overview['seeds'])):
            raise ValueError('Invalid research filter or pagination value.')
        values = [p for p in self.pairs.values() if (group == 'all' or p['group'] == group)
                  and (not search or search.casefold() in (p['question'] + ' ' + p['question_id']).casefold())
                  and (seed == '' or p['seed'] == seed)
                  and (issue == 'all' or any(s['flags'][issue] for s in p['systems'].values()))]
        return {'total': len(values), 'offset': offset, 'limit': limit, 'cases': values[offset:offset+limit]}

    def case(self, question_id, seed):
        self._ensure()
        if (question_id, seed) not in self.pairs:
            raise KeyError('No recorded case for that question and seed.')
        results = {}
        with self.paths[1].open('rb') as handle:
            for s in ('RAIR', 'KAIR'):
                handle.seek(self.offsets[question_id, seed, s])
                row = json.loads(handle.readline())
                if (row['question_id'], row['seed'], row['system']) != (question_id, seed, s):
                    raise ValueError('Recorded case index no longer matches the journal.')
                results[s] = row['result']
        example = self.examples[question_id]
        return {**self.pairs[question_id, seed], 'results': results, 'task': asdict(example.task),
                'gold_answer': example.gold.answer, 'gold_supporting_facts': example.gold.supporting_facts,
                'review_notes': [n for n in self.notes['cases'] if n['question_id'] == question_id and n['seed'] == seed],
                'historical': True}
