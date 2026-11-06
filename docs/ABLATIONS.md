# Step 9: controlled component removals

## Research question

Does the full RAIR design improve answer quality compared with removing its
semantic verification gate or its generated subquestions/dependency graph?
Competitive KAIR is rerun on the same cohort as a secondary comparison.

This is a **small exploratory component study**, not the final confirmation
benchmark and not a claim that more roles necessarily improve performance.

The study is complete: 160 runs, no question-level execution errors, 239 passing
automated tests, four live browser smoke runs and a validated 15-slide deck.
Full RAIR scored 50.0% EM, KAIR and no-gate each 55.0%, and no-decomposition
47.5%. Both adjusted component intervals include zero. Read the
[measured findings](../deliverables/step9/Step9_Findings.md) and
[reviewed cases](../deliverables/step9/Step9_Failure_Review.md).

## Frozen design

- Twenty questions sampled without consulting prior accuracy, excluding 225
  dataset IDs already scheduled or exposed in preserved local records.
- Two base seeds, 42 and 43; four arms, producing 160 scheduled results.
- Same `qwen3.5:4b` model/digest, per-question document pools, BM25 top-3,
  4096 context, 512 output cap and non-final temperature 0.7.
- Each arm has the same ceilings: four retrievals and 18 model calls, including
  a reserved final-answer call. Final temperature is zero.
- Serial execution, cyclic rotation of starting arm. Each arm occupies each
  position ten times. The design is not exhaustive over all predecessor orders.
- Same final synthesis implementation and prompt. No live dashboard observers
  are enabled during benchmark execution.
- Gold is consulted only after each prediction for scoring. Every error and
  abstention remains an empty prediction in the answer-score denominator.

`config/step9_ablations.json` fixes question fingerprints, schedule, settings,
dataset hash and source hashes before inference. `config/step9_exclusions.json`
records the exclusion metadata. `results/step9_source.zip` preserves the source.
Resume requires the exact original manifest and source; it cannot silently mix
code or model/runtime versions.

## What is removed

| Arm | Intervention | Retained |
| --- | --- | --- |
| RAIR | None | Current full pipeline |
| RAIR_NO_VERIFICATION | Bypass the semantic verifier call; admit every structurally valid extracted candidate and resolve its gap after a nonempty admission | Generated gaps, BM25, filter, extractor, original-source validation, common synthesis |
| RAIR_NO_DECOMPOSITION | Install one gap equal to the original question; no generated subquestions or dependencies | Planner, retrieval, filter, extractor, semantic verifier, common synthesis |
| KAIR | Competitive baseline | Private state, independent agent seeds, selection and refined-context sharing |

The no-gate result includes an explicit intervention label and no fabricated
verifier decisions. Its admitted shared facts are **unchecked**, despite the
legacy internal field being named `verified_facts`. Source/type validation is
retained; “no verification” never means accepting invalid document/sentence IDs.

The single-gap baseline can still iterate and accumulate facts. It does not
generate an explicit multi-gap graph. A query planner can still implicitly
identify intermediate entities; the intervention tests explicit decomposition,
not the removal of all possible model reasoning about subproblems.

## Analysis fixed before execution

Primary endpoints are full RAIR minus each removal in exact match. Both use
10,000 paired question-cluster percentile resamples, with both seeds kept in
each question cluster. Pointwise 97.5% intervals provide approximately 95%
family coverage for these two prespecified EM comparisons. The sample has
20 question clusters, not 40 independent observations.

F1 and RAIR-versus-KAIR are secondary. Source-sentence overlap, retrieval
precision/recall/F1, coverage, abstentions, errors, calls, input/output tokens
and local execution time are descriptive secondary metrics. No semantic
entailment or hallucination-rate conclusion follows from citation overlap.

Removing a component also removes its calls and can alter gap resolution and
stopping. Equal ceilings do not mean equal actual computation. The contrast
estimates the declared removal intervention; it does not isolate a semantic
benefit while holding realized compute constant. Local elapsed times are not
a controlled hardware speed comparison. Small-sample bootstrap intervals can
be unstable; a zero-containing interval does not establish a directional effect.

## Results and presentation

The completed experiment generates:

- `results/step9_ablations.jsonl`: every original result, request/response trace,
  input fingerprint, score and final environment verification.
- `results/step9_ablations.summary.json` and `.md`: all metrics and contrasts.
- `results/step9_analysis.json`: observed stops/errors, outcome groups and
  deterministic illustrative pairs; illustrations are not causal explanations.
- `deliverables/step9/Step9_Findings.md` and `Step9_Outcome_Census.csv`:
  examiner-facing findings and all scheduled outcomes.
- A new presentation copy with a Step 9 appendix. The Step 7 package remains
  historical; the appendix clearly separates the cohorts.
- The dashboard's Benchmark view adds a separately labeled Step 9 section
  with measured tables/charts, adjusted intervals and all four paired outputs.
  It validates the manifest, complete journal and recomputed summary before
  showing results; incomplete or inconsistent data are not presented as findings.

## Reproduce

Preserve the frozen source and existing evidence. Do not regenerate the
manifest after viewing results. For a compatible checkout, audit/resume with:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -u -m src.experiments.compare run --manifest config/step9_ablations.json --output results/step9_ablations.jsonl --resume
```

A completed journal is audited without new inference. An interrupted journal
resumes only its unrecorded arms. Do not edit prompts/settings to complete an
unfinished schedule. Syntax, unit/integration checks, browser QA and the
completed-result audit are recorded with the Step 9 verification artifacts.

## Next step

Step 10 freezes the final chosen systems and evaluates them on a larger
untouched cohort that excludes every prior experiment, including these 20
questions. Its primary endpoint and sample size must be chosen before running.
Only after that study should the final teacher report and submission package
be consolidated. Step 9 does not run that next experiment.
