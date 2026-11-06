"""Read-only Stage 1 audit of the frozen Step 10 paired benchmark."""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / 'results' / 'step10_benchmark.jsonl'
OUTPUT = ROOT / 'results' / 'improvement_v2'


def main():
    rows = []
    for line in JOURNAL.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get('record_type') == 'result':
            rows.append(record)
    assert len(rows) == 400, f'Expected 400 results; found {len(rows)}'
    paired = {}
    for record in rows:
        key = (record['question_id'], record['seed'])
        pair = paired.setdefault(key, {})
        assert record['system'] not in pair, f'Duplicate arm: {key}'
        pair[record['system']] = record
    assert len(paired) == 200 and all(set(p) == {'RAIR','KAIR'} for p in paired.values())

    output_rows = []
    counters = Counter()
    review_cases = []
    for (qid, seed), pair in sorted(paired.items()):
        rr, kr = pair['RAIR'], pair['KAIR']
        r, k = rr['result'], kr['result']
        rounds = r.get('rounds') or []
        state = r.get('state') or {}
        gaps = state.get('gaps') or []
        retrieved = {
            item['document']['document_id']
            for round_ in rounds for item in round_.get('retrieved', [])
        }
        extracted = sum(len(round_.get('candidates') or []) for round_ in rounds)
        rejected = sum(
            not decision.get('accepted', False)
            for round_ in rounds for decision in round_.get('decisions') or []
        )
        selected = sum(len(round_.get('evidence') or []) for round_ in rounds)
        promoted = len(state.get('verified_facts') or [])
        rem = sum(not gap.get('resolved', False) for gap in gaps)
        rem_desc = ' | '.join(gap.get('description','') for gap in gaps if not gap.get('resolved',False))
        rcorrect = rr['evaluation']['exact_match'] == 1.0
        kcorrect = kr['evaluation']['exact_match'] == 1.0
        outcome = ('both_correct' if rcorrect and kcorrect else
                   'rair_only' if rcorrect else 'kair_only' if kcorrect else 'neither_correct')
        counters[outcome] += 1
        abstained = r['status'] == 'abstained' or bool(r.get('prediction',{}).get('abstain'))
        budget = r.get('stop_reason') == 'budget_exhausted'
        # This is document-title recall derived from the frozen post-inference evaluation.
        # It is not a semantic entailment or individual-sentence sufficiency judgment.
        full_support_titles = rr['evaluation'].get('retrieval_recall') == 1.0
        flags = []
        if abstained: flags.append('abstained')
        if budget: flags.append('budget_exhausted')
        if full_support_titles: flags.append('full_support_title_recall')
        if rejected: flags.append('one_or_more_rejected_candidates')
        if rem: flags.append('unresolved_gaps')
        if extracted == 0: flags.append('no_extracted_candidates')
        if selected == 0: flags.append('no_filtered_evidence')
        if promoted == 0: flags.append('no_promoted_facts')
        if r.get('stop_reason') == 'all_gaps_resolved' and not rcorrect:
            flags.append('resolved_plan_but_nonexact_answer')
        if abstained and full_support_titles: counters['abstain_full_support'] += 1
        if budget and full_support_titles: counters['budget_full_support'] += 1
        if rejected: counters['runs_with_rejections'] += 1
        if r.get('stop_reason') == 'all_gaps_resolved' and not rcorrect:
            counters['resolved_but_nonexact'] += 1
        for flag in flags: counters['flag:'+flag] += 1
        row = {
            'question_id': qid, 'seed': seed, 'question': r.get('question',''),
            'outcome': outcome, 'rair_answer': r.get('prediction',{}).get('answer',''),
            'kair_answer': k.get('prediction',{}).get('answer',''),
            'rair_em': int(rcorrect), 'kair_em': int(kcorrect),
            'rair_status': r.get('status',''), 'stop_reason': r.get('stop_reason',''),
            'full_support_title_recall': int(full_support_titles),
            'rounds': len(rounds), 'retrievals': r.get('usage',{}).get('retrieval_calls',0),
            'llm_calls': r.get('usage',{}).get('llm_calls',0),
            'gaps': len(gaps), 'unresolved_gaps': rem,
            'filtered_evidence_groups': selected, 'candidate_count': extracted,
            'rejected_candidates': rejected, 'promoted_facts': promoted,
            'retrieved_document_ids': ';'.join(sorted(retrieved)),
            'unresolved_descriptions': rem_desc, 'flags': ';'.join(flags),
        }
        output_rows.append(row)
        if outcome != 'both_correct' and (
            outcome in ('kair_only','rair_only') or (abstained and full_support_titles)
        ):
            review_cases.append({
                'question_id': qid, 'seed': seed, 'outcome': outcome,
                'question': row['question'], 'flags': flags,
                'rair_answer': row['rair_answer'], 'kair_answer': row['kair_answer'],
                'rounds': rounds, 'gaps': gaps,
                'verified_facts': state.get('verified_facts',[]),
            })
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / 'failure_audit.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(output_rows[0]))
        writer.writeheader(); writer.writerows(output_rows)
    summary = {'pairs': len(paired), 'run_counts': dict(counters),
               'definitions': {'full_support_title_recall':
               'Post-inference document-title retrieval recall equals 1; not proof of sentence-level support or answer sufficiency.',
               'flags': 'Nonexclusive observable events, not validated root causes.'}}
    (OUTPUT / 'failure_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    # Deterministic compact subset per outcome/flag for manual review.
    chosen=[]
    for label, predicate in [
        ('kair_only',lambda c: c['outcome']=='kair_only'),
        ('rair_only',lambda c: c['outcome']=='rair_only'),
        ('abstained_with_support',lambda c: 'abstained' in c['flags'] and 'full_support_title_recall' in c['flags']),
    ]:
        candidates=[c for c in review_cases if predicate(c)]
        chosen.extend(dict(c, review_category=label) for c in candidates[:5])
    (OUTPUT/'review_queue.json').write_text(json.dumps(chosen,indent=2,ensure_ascii=False),encoding='utf-8')
    report = ['# Step 10 RAIR Failure Audit', '', 'This audit is observational, not a causal analysis.',
              'All 200 paired runs are included. Nonexclusive flags can overlap.', '']
    for key,value in sorted(counters.items()): report.append(f'- **{key}:** {value}')
    report.extend(['','## Interpretation boundaries',
                   '- Retrieval recall is title overlap with annotated support, not semantic sufficiency.',
                   '- Rejection counts do not establish whether a rejected claim was correct.',
                   '- Exact-match failures can include aliases or other semantically acceptable variants.',
                   '- Manually inspect review_queue.json before choosing an intervention.'])
    (OUTPUT/'failure_review.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('AUDIT PASSED: 200 paired runs; 400 source records')
    for key,val in sorted(counters.items()):
        if not key.startswith('flag:'): print(f'  {key}: {val}')
    print(f'Output: {OUTPUT}')


if __name__ == '__main__':
    main()
