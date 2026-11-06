# RAIR vs KAIR

A local Python research project comparing Role-Aware Iterative
Retrieval (RAIR) with a competitive KAIR baseline on multi-hop QA.

## Current status

**Step 9 complete:** two component removals and competitive KAIR were tested
against full RAIR on 20 previously unscheduled questions, two seeds and 160
frozen runs. All arms had zero question-level execution errors. EM was 50.0%
for full RAIR, 55.0% KAIR, 55.0% without the gate and 47.5% without decomposition.
Both prespecified component intervals include zero; a benefit is not established.
All 239 automated tests pass. The current dashboard includes the component
study, and a validated 15-slide presentation adds its findings. See
[methods](docs/ABLATIONS.md), [findings](deliverables/step9/Step9_Findings.md),
[case review](deliverables/step9/Step9_Failure_Review.md) and
[verification](results/step9_verification.json).
**RAIR v2 verified (2 November 2026):** Targeted interventions for bridge-entity preservation and intermediate fact admission were evaluated across two disjoint HotpotQA cohorts (Phase 2: 10 questions / 20 pairs; Phase 3: 25 questions / 50 pairs; combined: 35 questions / 70 pairs / 140 system runs under equal 4-retrieval / 18-LLM call limits). Across the combined 70-pair evaluation, RAIR v2 scored **57.1% Exact Match** versus **55.7% for competitive KAIR** (+1.4 pp net advantage, 8 paired wins vs. 7 KAIR wins and 55 ties), with **90.7% gold document retrieval recall** (vs. 85.7% for KAIR), lower prompt token usage (9,441 vs. 9,772), faster execution (14.9s vs. 17.1s), and a **+35.1 pp EM recovery over Step 10** (57.1% vs 22.0%), dropping abstentions from 71.0% to 20.0%. See the comprehensive [RAIR v2 Research Report](results/rair_v2/RAIR_V2_FINAL_REPORT.md), [Phase 2 benchmark](results/rair_v2/phase2_benchmark.md), [Phase 3 confirmatory benchmark](results/rair_v2/phase3_confirmatory_benchmark.md), and [source freeze](results/rair_v2/rair_v2_freeze.json).

**Step 10 confirmatory benchmark complete:** 400 scheduled arms (100 questions, 2 seeds, 2 systems) were executed and audited under the frozen protocol, establishing the historical baseline prior to RAIR v2.

**Live responsiveness update — verified:** completed stages now
appear during inference. Cursor-based polling returns only new events and
compact status; each finished engine result is fetched once. Full raw JSON is
rendered only when expanded. Optional observers leave model inputs, settings,
budgets and engine order unchanged. The user confirmed the dashboard works;
the current full suite passes **239 tests**, including neutrality, compatibility
and ablation checks. JavaScript polling regressions also pass. See
[test commands and manual checks](docs/LIVE_UPDATES.md).
The verification records below describe the earlier tested Step 8 revision.

**Step 8 complete:** the local dashboard now has the five research views from
the original aim: objective, architectures, live execution, controlled benchmark,
and findings/failures. Detailed timelines expose recorded retrievals, evidence,
candidate admissions, shared/private state and final citations. Eight charts use
the frozen experiment; all 200 RAIR/KAIR pairs are searchable and inspectable.
All **223 tests** pass. Four live engine runs verified complete and missing
evidence demonstrations. Engine source and frozen experiment files are unchanged.
See the [research dashboard guide](docs/RESEARCH_DASHBOARD.md) and
[Step 8 verification](results/step8_validation.json).

**Maintenance review, 30 October 2026:** KAIR now constrains generated source
references to available documents and sentences, and safely combines valid
repeated-document selections. All **210 tests** pass. Eight final live engine
runs exercised four matched, already-exposed diagnostic cases through the
dashboard backend. RAIR and the common final-answer policy are unchanged;
ineffective prompt experiments were discarded. See the
[project review and recommended next steps](docs/PROJECT_REVIEW.md) and
[maintenance verification](results/post_presentation_20261030/verification.json).
The Step 5 benchmark and Step 7 teacher package remain historical evidence;
their scores do not measure this maintenance revision.

Step 1: RAIR is connected end to end. The Ollama client, HotpotQA loader,
BM25 retriever, specialized roles, bounded controller, source citations,
call/token tracing, and diagnostic command-line runner are implemented.

Step 2: the local competitive KAIR baseline is also implemented, with private
agent memory, independently sampled whole-question proposals, fact checking,
context filtering, partial-proposal selection, and bounded competition.
See [KAIR execution and reference mapping](docs/KAIR.md) for its local adaptations.

Step 3 adds the common evaluation pipeline: frozen paired sampling, enforced
shared budgets, matched generation settings, common scoring, full traces,
resumable execution and generated reports. See
[evaluation protocol and validation](docs/EVALUATION.md) and the
[paired pilot report](results/step3_paired_pilot.md).

Step 4 completed a larger untouched benchmark: **100 new questions, two seeds,
400 system runs**, excluding 25 previously exposed questions. In the fixed local
configuration, RAIR scored **23.0% exact match / 29.8% answer F1** and KAIR
**36.0% / 50.5%**. KAIR's paired exact-match advantage was **13.0 percentage
points**, with a question-cluster 95% interval of **5.5–21.0 points**.
All errors and abstentions were retained; no common-budget violations occurred.
See [the benchmark report](results/step4_untouched_benchmark.md) and
[protocol, validation and limitations](docs/BENCHMARK.md).

Step 5 completed the RAIR validation and abstention repairs, followed by
**100 further new questions, two seeds and 600 runs**, including a Step 4 RAIR
core control with the same updated final policy. Updated RAIR scored **40.5%
exact match / 47.1% F1**, versus **18.5% / 21.9%** for the control and
**36.0% / 45.5%** for KAIR. RAIR errors fell from **24 to zero** and abstentions
from **111 to 61**, on those same questions. Its core exact-match gain was
**22.0 points**, 95% question-cluster interval **15.0–29.5 points**.
The 4.5-point RAIR advantage over KAIR is inconclusive: its interval includes zero.
The Step 5 revision passed **191 tests**; all 200 RAIR traces also replay identically after
a standalone call-estimate correction. See [Step 5 results and reproduction](docs/RAIR_IMPROVEMENTS.md)
and [the fresh benchmark](results/step5_fresh_benchmark.md).

These findings apply to this model, supplied document pools and common limits.
**Step 6 is complete:** the local dashboard now runs both real controllers,
shows answers and source citations, exposes execution traces and JSON downloads,
supports editable source documents, and displays the frozen benchmark separately.
All **207 tests** pass; five browser comparisons exercised ten real engine
runs across four scenarios, including missing evidence and a custom question. See the
[dashboard guide](docs/DASHBOARD.md) and [actual screenshot](docs/assets/dashboard_step6_desktop.png).
**Step 7 is complete:** the [teacher presentation package](deliverables/RAIR_KAIR_Teacher_Package.zip)
contains a 12-page final report, 12-slide editable PowerPoint with presenter notes,
a three-page demo script, 30 viva questions and answers, PDF copies, and a
trace-based failure review. Covers leave space for personal details.
A fresh check passed all **207 tests**, reaudited and rescored all **600 frozen
runs**, and reproduced both exact-match contrast intervals. Two new browser
rehearsals confirmed complete-evidence answers and missing-evidence abstentions.
All document pages and slides were visually reviewed; the deck was opened,
rendered and its chart edited and reopened in installed PowerPoint.
See [Step 7 handoff](docs/PRESENTATION.md), [verification](results/step7_verification.json),
and [package instructions](deliverables/step7/START_HERE.md).
Fill the cover fields and rehearse before class. The remaining model failures
are documented; no inference code or frozen benchmark was changed in Step 7.
See [RAIR execution](docs/RAIR.md) for the controller policy and standalone limits.

## Open the dashboard

With Ollama running and the configured model installed, double-click
`start_dashboard.cmd` or run it from PowerShell. Open **http://127.0.0.1:8765**.

```powershell
.\start_dashboard.cmd
# Or:
.\.venv\Scripts\python.exe -X utf8 -B -u -m dashboard.server
```

Choose an example or supply your own question and source sentences, then click
**Run comparison**. The dashboard uses the existing Python environment and adds
no dependencies. Its server stays local to this computer. See the
[presentation walkthrough and limits](docs/DASHBOARD.md).

## Run RAIR

From the project root in PowerShell, with Ollama running and the configured
model installed:

```powershell
# Complete and missing-evidence cases using the real local model.
.\.venv\Scripts\python.exe -m src.experiments.check_rair_pipeline

# First three HotpotQA questions, including post-inference answer scores.
.\.venv\Scripts\python.exe -m src.experiments.run_rair --limit 3

# Choose another diagnostic range or a new output filename.
.\.venv\Scripts\python.exe -m src.experiments.run_rair --offset 3 --limit 3 --output results/rair_next3.jsonl

# Offline unit and integration tests; no Ollama required.
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Each run uses a new output file. The HotpotQA runner flushes each finished
question to JSONL, so completed records survive interruption. It returns
a nonzero exit code if any question has an execution error; ordinary
abstentions are valid completed runs. No model is downloaded automatically.

## Run KAIR

```powershell
# Whole-question competition with complete and missing evidence.
.\.venv\Scripts\python.exe -m src.experiments.check_kair_pipeline

# The same diagnostic question range and answer evaluator as RAIR.
.\.venv\Scripts\python.exe -m src.experiments.run_kair --limit 3
```

The default uses two agents with seeds 42 and 43 and temperature 0.7.
Each competition iteration allows each agent two retrieval/update cycles;
there are at most two competition iterations. A complete candidate stops
later scheduled work. Otherwise only the candidate with the fewest remaining
requirements publishes its source context. Private knowledge is never merged.

These are bounded serial local adaptations of the reference algorithms.
Current maximum budgets differ: RAIR allows 5 retrieval calls and 27 LLM
calls, while KAIR allows 8 retrieval calls and 33 LLM calls. Actual usage is
recorded. These diagnostics do not constitute a budget-matched comparison.

## Run the common comparison

The completed pilot's frozen protocol is `config/step3_pilot.json`. For a new
experiment, choose new manifest/output filenames and prepare before inference:

```powershell
.\.venv\Scripts\python.exe -B -m src.experiments.compare prepare --output config/new_pilot.json
.\.venv\Scripts\python.exe -B -u -m src.experiments.compare run --manifest config/new_pilot.json --output results/new_pilot.jsonl

# Resume the same journal after an interruption, retaining completed failures.
.\.venv\Scripts\python.exe -B -u -m src.experiments.compare run --manifest config/new_pilot.json --output results/new_pilot.jsonl --resume
```

Both systems get at most four retrievals and 18 LLM calls per run, with one
call reserved for the common final synthesizer. Non-final temperature is 0.7
for both; KAIR retains distinct agent seeds. Actual tokens and runtime are
reported separately. The pilot covers four questions beyond the first 20
development examples, with base seeds 42 and 43 and balanced execution order.

The runner verifies code/data hashes and model identity, scores all planned
runs including errors and abstentions, and writes full `.jsonl`, machine
`.summary.json` and human-readable `.md` outputs. All 207 current automated tests pass.
See [the evaluation guide](docs/EVALUATION.md) for scoring definitions and limits.

The completed Step 4 benchmark uses `config/step4_benchmark.json`. With its
frozen source snapshot restored, its original journal can be validated and
its reports regenerated without new inference:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -u -m src.experiments.compare run --manifest config/step4_benchmark.json --output results/step4_untouched_benchmark.jsonl --resume
```

A completed run with question errors returns exit code 1 while retaining the
complete results. The [archive validation](results/step4_validation.json) passed,
and the [source snapshot](results/step4_source_snapshot.zip) restores the frozen
code/configuration/tests for future reproduction. KAIR used fewer calls but more
prompt tokens; the benchmark does not establish an overall cost saving.

Historical manifests deliberately reject changed source code. Step 5 preserves
its measured source separately from the final standalone cost-estimate correction;
the [Step 5 guide](docs/RAIR_IMPROVEMENTS.md) explains both archives and the
network-free replay that verifies equivalent benchmark inference.

## Research question

Can explicit pipeline-role specialization and shared evidence-verified
knowledge improve multi-hop factual QA compared with competitive
KAIR agents that independently address the whole question?

Accuracy and correctness are the first priorities.
Efficiency improvements must be measured, not assumed.

## RAIR pipeline

Question
-> Decompose into information gaps
-> Select an actionable gap
-> Query planner
-> BM25 retrieval
-> Evidence filter
-> Fact extractor
-> Verification gate
-> Shared knowledge update
-> Repeat as needed
-> Answer synthesizer, with citations or abstention

"Verified" means accepted by our evidence-support checks.
It does not imply that an LLM verifier guarantees factual truth.

## KAIR baseline

Use the competitive mode from Algorithm 3 of the reference paper,
with two agents initially.

Each agent maintains private knowledge, unresolved requirements,
query history, and working context.

Preserve query planning, knowledge updating, fact checking,
context-preserving filtering, and iterative retrieval.

When no agent completes the task, the paper selects the candidate
with the fewest unresolved requirements and shares its refined context.

Do not expose gold answers or gold supporting-fact annotations to
agents, verifiers, stopping rules, or the selector.

KAIR also describes a collaborative decomposition mode.
Decomposition and shared knowledge alone are not RAIR's novelty claim.

## Initial local adaptations

- Model: qwen3.5:4b through Ollama.
- Dataset: HotpotQA development set in the distractor setting.
- Retrieval scope: each question's supplied document pool.
- Initial BM25 retrieval depth: top 3 passages.
- One LLM request at a time.

This is a local adaptation, not an exact reproduction of the paper's
models, retrieval setting, or asynchronous execution.

Serial execution changes the competitive scheduler and cancellation
behavior. Document that difference before reporting results.

## Comparison controls

Both systems must use the same questions, document pools,
document preprocessing, BM25 implementation, and model version.

Use a common final-answer generation policy and answer evaluator.
Keep answer text separate from citations for answer scoring.

Keep gold annotations exclusively in the evaluation layer.

Preserve independent sampling for competitive KAIR agents rather
than creating two identical deterministic copies.

RAIR diagnostic outputs record prompts, decoding settings, seeds, model
identity, budgets, raw responses, call counts, tokens, and runtime.
KAIR uses the same accounting helpers and diagnostic writer, and also records
agent-specific calls, proposal states, context selection, and isolated agent errors.

Report answer scores over all evaluated questions, including
abstentions, and report answer coverage separately.

Equal numbers of rounds do not imply equal computation.
Measure actual LLM calls, retrieval calls, tokens, and runtime.

## Phase 1 setup check

Run from the project root:

    .\.venv\Scripts\python.exe -m src.experiments.check_setup

Expected final line:

    PHASE 1 PASSED

This check does not contact Ollama or test GPU inference.

## Reference

Song, S., Chawla, S., and Madisetti, V. K. (2026).
KAIR: Knowledge-Aware Iterative Retrieval for Multiagent Systems.
IEEE Transactions on Computational Social Systems.
DOI: 10.1109/TCSS.2026.3668728
