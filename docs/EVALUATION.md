# Common RAIR / KAIR evaluation

Step 3 adds one paired runner around the existing controllers. It freezes the
protocol before inference, enforces the same resource limits, scores both
systems with the same functions, and preserves every completed arm in a journal.
It uses the existing local model, dataset loader, BM25 implementation, final
answer synthesizer, and answer metrics. No dependencies were added.

## Frozen pilot protocol

| Control | Setting |
| --- | --- |
| Dataset | HotpotQA dev, distractor; each question's supplied document pool |
| Sample | 4 questions, sampled without gold-based filtering, sample seed 20261018 |
| Development exclusion | First 20 dataset questions, covering the earlier diagnostics |
| Base seeds | 42 and 43 for every question and both systems |
| Schedule | 8 matched pairs / 16 system runs; alternate which system runs first |
| Model | Installed `qwen3.5:4b`; record and check exact model digest and Ollama version |
| Retrieval | Shared BM25, top 3 passages, no web retrieval |
| Common budget per run | At most 4 actual retrievals and 18 LLM calls, including final synthesis |
| Generation limits | 4096-token context, 512-token output allowance per call, thinking disabled |
| Non-final temperature | 0.7 for both systems |
| Final answer | Shared verified-fact synthesizer, temperature 0, base seed, citations or abstention |
| KAIR agent seeds | Base seed and base seed + 1; private agent memories remain separate |
| Execution | One local model request at a time, question-free warm-up outside scored runs |

The comparison explicitly matches non-final temperature. Standalone RAIR role
calls normally use temperature 0; standalone KAIR uses 0.7. This pilot therefore
evaluates a matched-temperature RAIR variant alongside competitive local KAIR.
It does not silently change the standalone diagnostic policy. KAIR's independent
agent seeds are preserved because sampled competition is part of that method.

Standalone maximum budgets remain RAIR 5 retrievals / 22 LLM calls and KAIR
8 retrievals / 33 LLM calls. Those earlier diagnostic outputs cannot be compared
as though they used this common protocol.

The guard reserves one LLM call for final synthesis. On a common limit, retrieval
stops normally and the controller synthesizes from committed verified facts,
or abstains. A blocked call never reaches Ollama or BM25 and never appears as a
paid attempt. Transport and output-validation failures remain explicit errors;
actual attempted calls, including failures, count against the budget. KAIR shares
one budget across all its agents. It cannot multiply the common allowance by
adding agents. Final generation can still fail and is recorded as an error.

Equal ceilings do not imply equal actual token use or compute. Different prompt
sizes, decomposition costs, early completion, and abstention affect actual use.
The reports retain LLM/retrieval counts, prompt/output tokens, missing-token
flags, and serial wall time. Warm-up is logged separately. Local timing remains
dependent on machine load and does not reproduce asynchronous KAIR.

## Run and resume

From the project root in PowerShell:

```powershell
# Freeze a NEW protocol before looking at its outcomes.
.\.venv\Scripts\python.exe -B -m src.experiments.compare prepare --output config/new_pilot.json

# Execute every arm in the frozen schedule, with a NEW journal filename.
.\.venv\Scripts\python.exe -B -u -m src.experiments.compare run --manifest config/new_pilot.json --output results/new_pilot.jsonl

# After an interruption, resume the original manifest and journal.
.\.venv\Scripts\python.exe -B -u -m src.experiments.compare run --manifest config/new_pilot.json --output results/new_pilot.jsonl --resume

# Offline regression and protocol tests; no model requests.
.\.venv\Scripts\python.exe -B -m unittest discover -s tests
```

Preparation uses `evaluation` in `config/settings.yaml`, checks that neither
controller has a lower native ceiling than the requested common limits, and
samples from sorted eligible question IDs using the recorded sample seed. It
freezes all source-code hashes, requirements, dataset hash, settings, selected
question/document hashes, development exclusions, seeds and execution schedule.
Changing these inputs requires a new manifest. Keep the committed pilot manifest
as the historical protocol; preparing again will not overwrite it.

Inference receives only `QuestionInput`: question text, question ID and source
documents. Gold answers and supporting facts stay in the evaluation layer and
are read for scoring after the controller returns. Tests mutate the gold labels
and verify that selection and every inference request remain unchanged.

The journal stores metadata, warm-up, one full result per completed arm, final
model/runtime verification, and the aggregate summary. Each completed arm is
flushed immediately. Resume checks the manifest, schedule prefix, saved inputs,
actual decoding settings, budgets, scores, model digest and server version.
It skips completed errors as well as completed successes. An arm interrupted
before its result was written starts again. Corrupted/incomplete lines are
rejected; retain that journal and use a new output for a fresh complete run.

Only a complete, verified schedule produces final `.summary.json` and `.md`
reports. Completed resume regenerates those reports without model calls.
The command returns 1 if any planned arm has a question-level execution error,
0 for a completed error-free run (including ordinary abstentions), and 130 for
an interrupted process. Existing journals are preserved unless explicitly
resuming the same file.

## Shared metrics

- **Answer exact match and token F1:** existing HotpotQA-style normalization.
  Every planned arm contributes; errors and abstentions are empty predictions.
- **Coverage:** fraction of arms with an answered prediction, separate from
  correctness. A wrong answer still contributes to coverage.
- **Citation precision, recall and F1:** set overlap between emitted original
  source sentence references and annotated supporting sentences. Document ID,
  title, sentence index and exact original text are checked; invalid sources
  receive no credit. Repeated valid sources receive no extra credit.
- **Cumulative retrieval precision, recall and F1:** union of document titles
  returned by every paid retrieval, including losing KAIR agents. This measures
  evidence reached during search, not just evidence retained by the winner.
- **Reliability and cost:** question errors, isolated KAIR agent errors,
  common-budget stops, missing token counts, call counts, tokens and runtime.
- **Paired differences:** KAIR minus RAIR answer scores for each question/base
  seed, plus exact-match win/tie counts. Repeated seeds are not independent
  questions; no significance test or superiority claim is made for this pilot.

Malformed/missing gold supporting references are flagged. Such questions stay
in answer metrics but are excluded from source/retrieval metric denominators.
Each metric's denominator is stored, so annotation problems cannot silently
inflate or suppress answer accuracy. Citation overlap is not semantic
entailment; model fact checking cannot guarantee factual truth.

## Step 3 validation

All **168 automated tests pass**, including the previous 150 and 18 new budget,
paired-scoring, gold-isolation, manifest and recovery tests. The integration
tests execute the real RAIR and KAIR controllers and replace only Ollama's HTTP
transport. They cover reserved final calls, both budget types, safe partial-state
finalization, actual decoding controls, output preservation, changed source/data
or runtime rejection, failed-arm retention, and completed-run report recovery.

The live pilot completed all **16 planned arms / 8 pairs** with zero question
errors, zero KAIR agent errors, zero common-budget violations, and complete token
counts. All selected gold references were valid. The same model digest and
Ollama **0.40.6** were verified at the beginning and end. Earlier standalone
diagnostics used their own recorded environment; they are not pooled into this
comparison.

| Metric, over 8 runs per system | RAIR | KAIR |
| --- | --- | --- |
| Exact match | 25.0% (2/8) | 50.0% (4/8) |
| Answer F1 | 30.6% | 61.3% |
| Answer coverage | 50.0% (4/8) | 87.5% (7/8) |
| Source-sentence citation F1 | 37.0% | 63.3% |
| Cumulative retrieval document recall | 87.5% | 87.5% |
| Mean LLM calls | 13.25 | 6.50 |
| Mean retrieval calls | 2.75 | 1.375 |
| Mean prompt / output tokens | 9455.625 / 1315.50 | 6091.125 / 567.25 |
| Mean serial seconds | 26.34 | 12.40 |
| Common-budget stops | 3 | 0 |
| Question-level execution errors | 0 | 0 |

KAIR had the higher exact-match score in 3 pairs, RAIR in 1, and 4 tied.
Those are outcomes from four questions, not eight independent questions.
No prompt, scoring rule or generation policy was changed after the pilot began,
and no completed arm was rerun to select a better outcome.

The examples expose actionable reasoning and formatting limits:

- For the Danish designer question, KAIR answered `Hans Jørgensen Wegner` in
  both seeds. RAIR abstained after a budget stop and a repeated query.
- For the two city-owned airports, RAIR answered `Yes` in both seeds. KAIR
  answered `Yes` once and gave an expanded sentence once. The latter scores
  zero under the frozen HotpotQA-style special-answer rule against `yes`.
- For the FC Bibo footballers question, neither system exactly matched the
  reference list. Some answers included the player the question excludes;
  others omitted requested players. Partial answer F1 is retained.
- For the filmmaker-experience comparison, RAIR abstained twice. KAIR abstained
  once and correctly answered `Frederick King Keller` once.

Completed-run resume was tested on the actual journal without model inference.
An independent read recomputed all 16 scores and the aggregate, checked balanced
order and resource caps, and verified that the machine summary matched. The
archived model digest is
`2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`.

Artifacts: [frozen manifest](../config/step3_pilot.json),
[human report](../results/step3_paired_pilot.md),
[machine summary](../results/step3_paired_pilot.summary.json), and
[full prompts/responses and result journal](../results/step3_paired_pilot.jsonl).

Step 3 establishes a working controlled measurement pipeline. It does not
establish a research winner or adequate QA accuracy. These four questions now
become development data; keep them outside a future untouched evaluation split.
Reasoning/answer-format improvements, a larger held-out benchmark, and confidence
intervals over independent questions belong to the next authorized project step.

The larger benchmark and question-based confidence intervals were subsequently
completed in [Step 4](BENCHMARK.md), preserving the Step 3 inference systems and
excluding all previously exposed questions. The pilot results above remain the
historical Step 3 record and are not pooled into that benchmark.
