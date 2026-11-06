# Step 4: larger untouched benchmark

This step evaluates the unchanged Step 3 inference systems on a prospectively
selected sample of **100 previously unexecuted HotpotQA questions**, with two
base seeds per question and both systems: **400 runs / 200 matched pairs**.
The complete cohort and analysis plan were frozen before model inference.

## Hold-out and fixed controls

The exclusion audit scanned 28 prior local JSON/JSONL artifacts and combined
their dataset question IDs with the first 20 development examples. It found
**25 exposed questions**: the original 20, the four Step 3 questions, and one
additional question (`5ae61bfd5542992663a4f261`) in the early dataset check.
All 25 are excluded. Selection samples 100 IDs from the remaining **7380**,
sorted before sampling with seed **20261019**, without filtering by answer,
difficulty, support validity or previous outcome.

"Untouched" refers to the project's recorded local experiment history at
protocol freeze. This is a sample of the public development split, not the
official hidden test set or a claim that the model never saw HotpotQA during
training. Each question still uses its supplied distractor document pool.

| Control | Frozen setting |
| --- | --- |
| Model | Installed `qwen3.5:4b`; exact digest and Ollama version checked before/after |
| Base seeds | 42, 43 for each question and both systems |
| Order | One system first for seed 42, the other first for seed 43; starting order alternates by question |
| Retrieval | Same local BM25, top 3 passages, per-question pool, no web |
| Common ceilings per run | 4 retrievals, 18 LLM calls including one reserved final call |
| Context / output | 4096 / 512 tokens per model request |
| Non-final temperature | 0.7 for both systems |
| Final generation | Same synthesizer, temperature 0, base seed, verified facts only, citations or abstention |
| Competitive KAIR | Two private agents, seeds base/base+1, existing serial scheduler and early stopping |
| Warm-up | Question-free, logged outside each scored run and budget |
| Primary endpoint | Mean paired exact-match difference, KAIR minus RAIR |
| Secondary endpoint | Paired answer-F1 difference; remaining metrics descriptive |
| Uncertainty | 95% question-cluster percentile bootstrap, 10000 resamples, seed 20261020 |

The inference, retrieval, budget-guard, input-parsing and answer-scoring files
were checked byte-for-byte against Step 3's frozen hashes before the run.
Only exclusion handling and evaluation reporting/uncertainty were extended.
No prompts, final-answer normalization, model settings or controller logic were
tuned using Step 3 outcomes. Both arms are the same matched-temperature local
variants documented in [the common evaluation guide](EVALUATION.md).

Every completed run contributes, including errors and abstentions. No run is
repeated or discarded because of its score. An interrupted unfinished arm may
restart through the existing journal recovery mechanism; completed errors are
retained. Invalid gold support references affect only source/retrieval metric
denominators, with all answer scores retained. Runtime and tokens measure actual
use; equal ceilings are not equal token expenditure or asynchronous performance.

## Why uncertainty uses questions

The two seeds share the same question and evidence, so there are 100 question
units, not 200 independent questions. For each question, each system's answer
score is averaged across its two seeds. Bootstrap draws sample 100 question
indices with replacement and carry both systems' seed-averaged scores together.
The 2.5th and 97.5th percentiles give the reported intervals. Pairing preserves
question difficulty and shared seed effects instead of independently resampling
the systems or treating repeated seeds as new questions.

Exact match is the prespecified primary endpoint. F1 intervals are secondary,
pointwise descriptions without adjustment for multiple comparisons. Intervals
are approximate and apply to this sampled local protocol; they do not establish
causality for individual architectural choices or generalize to other models,
budgets, full-corpus retrieval or the original paper's asynchronous execution.

## Reproduce or resume

```powershell
# The existing frozen manifest and original journal:
.\.venv\Scripts\python.exe -X utf8 -B -u -m src.experiments.compare run --manifest config/step4_benchmark.json --output results/step4_untouched_benchmark.jsonl --resume

# Offline tests:
.\.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests

# For a future experiment, use a revised config and NEW manifest/output names.
# Exclude every evaluated question before defining a new untouched sample.
# Create config/next_benchmark.yaml as a revised COPY, preserving this protocol.
.\.venv\Scripts\python.exe -X utf8 -B -m src.experiments.compare prepare --config config/next_benchmark.yaml --output config/new_benchmark.json
```

Python UTF-8 mode keeps answers with non-Latin characters printable on Windows.
The journal retains full prompts, raw responses, source references, actual
decoding settings, call counts, tokens, timings and per-arm post-inference
scores. Source/data/settings hashes and the exact schedule prevent a resumed
run from silently mixing implementations. Earlier manifests keep their original
hashes and artifacts; code changes require a new protocol for new execution.

## Validation and outputs

All **178 automated tests pass**, including the 168 Step 3 tests and ten new
checks for explicit hold-out exclusions, invalid exclusion IDs, unchanged
sampling under gold-label mutation, analysis configuration, paired resampling,
seed clustering, deterministic confidence intervals and complete-report gating.

- [Exclusion audit and unchanged inference hashes](../config/step4_exclusions.json)
- [Frozen settings](../config/step4_benchmark.yaml)
- [Frozen manifest](../config/step4_benchmark.json)
- [Full benchmark journal](../results/step4_untouched_benchmark.jsonl)
- [Generated result report](../results/step4_untouched_benchmark.md)
- [Machine summary](../results/step4_untouched_benchmark.summary.json)
- [Independent archive validation](../results/step4_validation.json)
- [Frozen source, configuration and test snapshot](../results/step4_source_snapshot.zip)

The source snapshot contains 70 files and matches every source hash in the
manifest. Extract it into a fresh folder to restore the implementation after
later code changes. Dataset files and model weights are not bundled; their
identities are recorded in the manifest and journal. Installed Python package
versions are recorded in the validation file.
The snapshot was restored into an isolated folder and all 178 offline tests
passed there, without the downloaded dataset or model inference.

## Completed results

All **400 planned runs / 200 matched pairs** completed. All 100 question IDs and
normalized question texts are distinct and disjoint from the prior exposed
questions. The cohort contains 85 bridge questions and 15 comparison questions.
No selected gold support annotations were invalid; every metric denominator is
200 runs per system. All token counts were available. No common-budget
violations occurred. The model digest and Ollama 0.40.6 were unchanged at the
closing verification, and the digest matches the Step 3 model.

| Metric, over 200 runs per system | RAIR | KAIR |
| --- | --- | --- |
| Exact match | **23.0% (46/200)** | **36.0% (72/200)** |
| Exact-match 95% question-cluster interval | 16.5–30.0% | 27.5–44.5% |
| Answer F1 | **29.8%** | **50.5%** |
| Answer-F1 95% question-cluster interval | 23.3–36.5% | 42.8–58.2% |
| Answer coverage | 38.5% (77/200) | 73.5% (147/200) |
| Abstentions | 99 | 40 |
| Question-level errors | 24 (12.0%) | 13 (6.5%) |
| Isolated agent errors | — | 33 |
| Common-budget stops | 34 | 15 |
| Source-sentence citation F1 | 26.1% | 47.0% |
| Cumulative retrieved-document recall | 83.25% | 86.50% |
| Mean LLM calls | 10.77 | 8.50 |
| Mean retrieval calls | 2.24 | 1.89 |
| Mean prompt tokens | 7141.25 | 9152.94 |
| Mean output tokens | 779.24 | 709.575 |
| Mean serial controller seconds | 15.95 | 15.61 |

The prespecified **KAIR minus RAIR exact-match difference is +13.0 percentage
points**, with a **95% paired question-cluster interval of +5.5 to +21.0
points**. The secondary answer-F1 difference is **+20.7 points**, interval
**+12.2 to +29.3 points**. Across the 200 seed-specific pairs, KAIR alone was
exactly correct in 40, RAIR alone in 14, and 146 tied. These pairs still contain
only 100 question units for uncertainty estimation.

This benchmark provides evidence of a KAIR accuracy advantage under the frozen
local protocol. It does not support a current RAIR accuracy advantage. The
individual-system exact-match intervals overlap; the relevant comparison is
the paired difference, whose interval stays above zero. No alternative scoring
rule, best-seed selection, post-outcome exclusion or prompt revision was used.

KAIR used fewer calls and fewer output tokens but **more prompt tokens**. Mean
total recorded tokens were approximately 7920.49 for RAIR and 9862.515 for
KAIR. The observed serial times were close. These results therefore do not
establish that KAIR is cheaper overall or meaningfully faster. Cost figures
include failed runs, as do accuracy denominators.

RAIR abstained substantially more often. Its 24 question errors comprised
11 verifier failures, 10 evidence-filter failures, two extraction failures and
one final-synthesis failure. KAIR's 13 question errors comprised seven final
citation/synthesis failures and six competitions with no valid proposal. Its
33 isolated agent failures are retained separately; one generation reached the
512-token limit. Invalid structured outputs and source references were rejected
rather than repaired or retried outside the common budget.
Agent-level and question-level error counts can overlap and should not be added.

The command's exit code was 1 because completed question-level error outcomes
were present. The benchmark itself has a complete schedule, closing identity
verification and final summary. This distinction prevents failed predictions
from disappearing from the evaluation.

The archive audit independently rescored every prediction, rechecked every
actual call and budget, checked order balance and all prior artifact IDs across
their different ID lengths, and verified the source snapshot. A separate
bootstrap calculation using standard-library inclusive quantiles reproduced all
reported intervals. Completed-journal resume regenerated the reports while
network/model requests were explicitly blocked.

Step 4 establishes a larger controlled baseline, uncertainty estimates and an
auditable record of the remaining failure modes. Any work on verifier coverage,
source IDs, final citation formatting or abstention needs a separate development
step. If these benchmark outcomes guide changes, retain these IDs outside any
future untouched evaluation cohort. Step 5 subsequently completed these repairs
and a separate fresh evaluation; see [Step 5](RAIR_IMPROVEMENTS.md). The Step 4
scores and archived implementation above remain historical results.
