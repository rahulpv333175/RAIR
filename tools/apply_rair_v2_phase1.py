"""Apply reversible RAIR v2 Phase 1 prompt changes to a project checkout.

Usage (from project root): python path/to/apply_rair_v2_phase1.py
Does not touch KAIR, benchmark manifests, or recorded experiment journals.
"""
from pathlib import Path
from datetime import datetime, timezone
import difflib
import hashlib
import shutil
import sys

root = Path.cwd()
path = root / 'src' / 'llm' / 'prompts.py'
if not path.is_file():
    sys.exit(f'ERROR: cannot find {path}. Run this from E:\\Projects\\role_aware_kair')
original = path.read_text(encoding='utf-8')
text = original

extract_anchor = '''10. Return statement and evidence_ids only. Candidate IDs are assigned by software.'''
extract_new = '''10. Return statement and evidence_ids only. Candidate IDs are assigned by software.
11. Bridge entity preservation: when a source identifies an entity by a prior
    name, occupation, work, or other clue, explicitly name the identified
    entity in the supported candidate claim. For example, prefer "The band
    previously named X is Y" over "The band was previously named X".
    Never fill an entity name missing from the supplied evidence.
12. For comparisons, preserve each explicitly stated attribute or category
    as a supported candidate. Never invent a numerical count or conclude a
    comparison absent evidence for both operands.
13. Preserve relevant named relations exactly; never strengthen a weak
    association into a claim of causation, tribute, membership, or identity.'''

old_answer = '''- answer_type_ok:
  True when the claim supplies a concrete useful factual value or relationship
  needed for the original question. A partial fact need not answer the entire
  current gap. A country alone cannot resolve a gap asking for a city.
  This checks the factual value type, not a JSON format or canonical ID.
  A sentence naming a person satisfies a gap asking who that person is.
  Do not invent identifier or formatting requirements absent from the gap.
  A supported partial fact may have the correct value type without fully
  resolving the gap. Missing gap conditions affect resolves_gap, not
  automatically answer_type_ok.
'''
new_answer = '''- answer_type_ok:
  True if the claim provides a concrete factual value, attribute, entity,
  or relation useful to answering the original question, including an
  intermediate bridge fact. This is a FACT ADMISSION check, not a check
  that the current gap is completed. A supported list of animation styles
  can be admitted without giving a numeric count for a comparison.
  An explicitly identified named military force may answer a question
  worded using the broad word "army" when the evidence supports its role.
  Never reject a supported intermediate fact merely for not completing
  the final answer. A wrong entity, unsupported relation, or mismatched
  location is never treated as the completed answer.
'''

old_resolve = '''- resolves_gap:
  True only when this candidate, if accepted, provides the specific
  information requested by the current gap.
'''
new_resolve = '''- resolves_gap:
  True only when the supported candidate fully supplies the information
  requested by the current gap. An admitted partial fact may have
  answer_type_ok=true and resolves_gap=false. For comparisons, admitting
  one operand or its attributes does NOT complete the comparison. Never
  mark a gap resolved solely because the evidence is relevant.
'''

pairs = [('fact extractor anchor', extract_anchor, extract_new),
         ('verifier admission', old_answer, new_answer),
         ('verifier completion', old_resolve, new_resolve)]
for name, old, new in pairs:
    if new in text:
        print(f'ALREADY PRESENT: {name}')
        continue
    if text.count(old) != 1:
        sys.exit(f'ERROR: expected exactly one original anchor for {name}; found {text.count(old)}. No file changed.')
    text = text.replace(old, new, 1)

if text == original:
    print('No change: RAIR v2 Phase 1 prompt modifications already present.')
    sys.exit(0)
compile(text, str(path), 'exec')
backup_dir = root / 'results' / 'rair_v2' / 'backups'
backup_dir.mkdir(parents=True, exist_ok=True)
digest = hashlib.sha256(original.encode('utf-8')).hexdigest()[:12]
backup = backup_dir / f'prompts_before_phase1_{digest}.py'
if not backup.exists():
    shutil.copy2(path, backup)
path.write_text(text, encoding='utf-8', newline='')
patch_dir = root / 'results' / 'rair_v2'
patch = patch_dir / 'phase1_prompt.diff'
patch.write_text(''.join(difflib.unified_diff(original.splitlines(keepends=True),
    text.splitlines(keepends=True), fromfile='src/llm/prompts.py BEFORE',
    tofile='src/llm/prompts.py PHASE1')), encoding='utf-8')
print(f'APPLIED RAIR v2 Phase 1 to: {path}')
print(f'Backup saved: {backup}')
print(f'Review diff: {patch}')
print('Next: run syntax check, test suite, then development experiments. NO measured improvement claimed.')
