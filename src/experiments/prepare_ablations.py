"""Freeze a small exploratory ablation cohort, excluding all prior scheduled questions."""
import copy
import hashlib
import json
from pathlib import Path

from src.evaluation.paired import prepare_manifest
from src.settings import PROJECT_ROOT, load_settings


def prepare():
    settings = copy.deepcopy(load_settings())
    excluded = set()
    sources = []
    # Read only exposure metadata, never use past accuracy to choose the cohort.
    paths = sorted((PROJECT_ROOT/'config').glob('*benchmark.json'))
    paths += sorted((PROJECT_ROOT/'results').rglob('*.jsonl'))
    for path in paths:
        with path.open(encoding='utf-8-sig') as handle:
            text = handle.readline() if path.suffix == '.jsonl' else handle.read()
        if not text.strip():
            continue
        record = json.loads(text)
        manifest = record.get('manifest', record)
        ids = set(manifest.get('excluded_question_ids', []))
        ids.update(q['question_id'] for q in manifest.get('questions', []))
        qid = record.get('question_id') or record.get('task', {}).get('question_id')
        if qid:
            ids.add(qid)
        excluded.update(ids)
        if ids:
            sources.append({'path': path.relative_to(PROJECT_ROOT).as_posix(),
                            'metadata_sha256': hashlib.sha256(text.encode()).hexdigest(), 'ids': sorted(ids)})
    raw = json.loads((PROJECT_ROOT/settings['dataset']['path']).read_text(encoding='utf8'))
    dataset_ids = {r['_id'] for r in raw}
    excluded.update(r['_id'] for r in raw[:20])
    settings['evaluation'] = {
        'name': 'Step 9 exploratory component ablations',
        'purpose': 'Prespecified exploratory component study on 20 previously unscheduled questions. '
                   'Primary endpoints: full RAIR minus each of two component removals in exact match. '
                   '97.5% pointwise question-cluster intervals for the two EM contrasts; other metrics secondary. '
                   'Not the final untouched confirmation benchmark.',
        'sample_size': 20, 'sample_seed': 20261030, 'seeds': [42, 43],
        'exclude_first_n': 0, 'exclude_question_ids': sorted(excluded & dataset_ids),
        'max_retrieval_calls': 4, 'max_llm_calls': 18, 'temperature': .7,
        'bootstrap_resamples': 10000, 'bootstrap_seed': 20261031, 'ablations': True,
    }
    manifest = prepare_manifest(settings)
    for name, value in [('config/step9_ablation_settings.json', settings),
                        ('config/step9_exclusions.json', {'policy': 'All prior scheduled/exposed IDs; no accuracy selection.', 'sources': sources}),
                        ('config/step9_ablations.json', manifest)]:
        with (PROJECT_ROOT/name).open('x', encoding='utf8') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
    print(f"Frozen {len(manifest['questions'])} questions, {len(manifest['schedule'])} runs; "
          f"excluded {len(settings['evaluation']['exclude_question_ids'])} prior IDs.")


if __name__ == '__main__':
    prepare()
