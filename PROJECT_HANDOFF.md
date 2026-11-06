# RAIR versus KAIR technical project handoff

**Inspection date:** 1 November 2026, Asia/Calcutta.  
**Working directory:** `E:\Projects\role_aware_kair`.  
**Companion inventory:** [PROJECT_FILE_MAP.md](PROJECT_FILE_MAP.md).

This is an evidence-based transfer record for a new technical reviewer. It describes the files and measurements present at inspection, rather than treating earlier completion messages or draft builders as proof of delivery. Application code, configuration, existing documentation and frozen experiments were not edited for this handoff.

## 1. Read this first

1. **Both engines and the common evaluation pipeline are implemented and exercised.** The current source matches the frozen Step 9 and Step 10 source hashes. Fresh handoff checks passed **242 Python tests**, JavaScript syntax checks and the progress-client regression check.
2. **Step 10 inference is finished.** Its journal contains all **400 scheduled arms**, on **100 new questions, two seeds and two systems**, followed by a matching model/runtime verification and completed summary. The previous chat's last observation of 377 completed runs is obsolete. Do not rerun the entire study merely to finish those supposedly missing runs.
3. **The final confirmation favors KAIR under this local protocol.** RAIR EM is **37.0%**, KAIR **50.0%**. The prespecified **KAIR minus RAIR EM difference is +13.0 percentage points**, paired question-cluster 95% interval **+5.5 to +21.0 points**. The hypothesis that full RAIR improves accuracy over this competitive baseline is not supported by this confirmation.
4. **Step 10 as a whole is not finished.** The new final report, slides, demo/viva exports, manual failure review, browser acceptance checks and final teacher ZIP have not been produced and verified. Draft authoring scripts exist; their intended outputs do not.
5. **README and some release notes are stale.** In particular, README says Step 10 has not run. The Step 7 teacher package is historical, and the Step 9 deck adds an exploratory appendix. Neither is a consolidated final presentation of the now-completed Step 10 result.
6. **This directory is not a Git repository.** Both Git status and repository-root discovery return `fatal: not a git repository (or any of the parent directories): .git`. There is no available branch, HEAD, commit history or Git diff. Do not invent them.

### Evidence and history limitations

The accessible development conversation contains the user's staged requests and a retained account of earlier Codex work, but not a complete independently accessible export of the user's earlier ChatGPT web conversation or every earlier tool transcript. The original master prompt was readable from:

`C:\Users\rahul\.codex\attachments\63d26e75-5b77-4dab-b940-4c16c2240a23\Pasted text.txt`.

The handoff incorporates its objectives below so the next conversation does not depend on that attachment remaining accessible. Historical decisions are attributed to repository documentation, saved patches, journals and verification records where available. Without Git history and the full earlier web chat, an exhaustive edit-by-edit development log cannot be established. Unrecorded alternatives and rationales are unknown.

Evidence precedence for review:

1. Current implementation and raw frozen journals/manifests.
2. Recomputed scores, current test execution and source/data fingerprints.
3. Dated verification files and recorded diagnostic traces.
4. Historical prose and conversation summaries, which can be stale.
5. Draft scripts and intended outputs, which do not establish completion.

## 2. Original objective and intended contribution

**Title:** RAIR — Role-Aware Iterative Retrieval for Multi-Hop Question Answering.

**Research question:** Can explicitly specialized retrieval responsibilities and evidence-verified shared knowledge improve factual multi-hop answer accuracy compared with competitive KAIR agents that independently attempt the complete question?

RAIR was intended to divide work into decomposition, query planning, BM25 retrieval, exact evidence selection, fact extraction, verification, shared-state updates and synthesis. The baseline was the **competitive mode** of KAIR, initially with two agents, private knowledge/requirements/query history and selected refined-context sharing. KAIR already includes fact checking and the reference also describes collaborative decomposition; neither decomposition nor shared memory alone is a valid novelty claim for RAIR.

The contribution under investigation is the effect of **functional role specialization, controlled fact admission and knowledge flow**, implemented as an inspectable local system and evaluated under shared conditions. Roles are prompts and validated interfaces over one model, not independently trained models. No model training or fine-tuning has been implemented.

Accuracy and correctness were primary. Retrieval effectiveness, evidence/grounding indicators, coverage, robustness, explainability and computation were secondary. The original prompt explicitly said not to assume RAIR would win. The completed negative confirmation is therefore a research finding, not a reason to replace or hide results.

### Intended evaluation

- Same local Ollama model/digest, supplied question document pools, preprocessing, BM25 implementation and depth.
- Gold answers and supporting annotations excluded from controller inputs and used only for post-inference scoring.
- Frozen sampling, common limits, documented decoding/seeds, full traces and retained errors/abstentions.
- Common downstream answer-generation policy to reduce final-generator confounding.
- EM, answer token F1, document retrieval precision/recall/F1, supporting-source metrics, coverage, calls, tokens, time and failure counts.
- Paired comparisons and later ablations; fresh questions after development on exposed questions.
- Future MuSiQue support, additional ablations and stronger generalization evidence. These future extensions are not implemented merely because they appear in the master prompt.

### Intended examiner demonstration

Approximately **5–7 minutes**: introduce a two-hop question; explain competitive KAIR; explain RAIR roles and shared facts; execute both on identical inputs; inspect actual retrieval/evidence/state transitions; present measured comparisons, uncertainty and limitations.

The fictional example is “In which city was the author of The Glass Orchard born?” with book → Mira Solen → Nerava evidence. It is an exposed synthetic demonstration, not an untouched accuracy test. Removing the birthplace sentence tests behavior with missing evidence.

## 3. Actual architecture

### 3.1 Common input, retrieval and inference infrastructure

`src/datasets/hotpotqa.py` separates immutable `QuestionInput(question_id, question, documents)` from `GoldLabels(answer, supporting_facts, question_type, level)` inside `HotpotExample`. Only the input object goes to controllers. `parse_hotpotqa_record` preserves original sentences and support indices; invalid gold references are retained for evaluation auditing rather than silently repaired.

`src/retrieval/document_store.py` defines `Document` and `DocumentStore`, checks question ownership and duplicate IDs, exposes searchable text and original indexed sentences. `BM25Retriever` in `src/retrieval/bm25.py` indexes each question's supplied pool, including title/text. It uses Unicode word tokenization/lowercasing, `k1=1.5`, `b=0.75`, deterministic scoring and pool-order tie breaking. Search returns positive-score matches up to `top_k`, currently 3. This is local distractor-pool retrieval, not open-domain Wikipedia search, dense retrieval or web browsing.

`src/llm/ollama_client.py` provides synchronous `OllamaClient`, `LLMResponse`, `OllamaError` and `summarize_calls`:

- Local HTTP Ollama only; localhost proxies bypassed; one request at a time.
- One independent system/user message pair per operation; structured JSON schema appended and sent as Ollama `format`.
- No automatic model download, generation retry or JSON repair.
- Logs request payload, raw response, elapsed time, error and whether a call is final synthesis.
- Incomplete/truncated generations fail explicitly, while known tokens remain charged and logged.
- Missing token counts are flagged, not estimated.
- `check_ready` checks installed model tags/digest and server version; it does not generate an answer.

`src/progress.py::publish` delivers detached observer payloads and isolates observer failures. Benchmark execution does not enable live UI observers.

### 3.2 RAIR

Entry point: `src/rair/controller.py::RAIRController.run(task)`.

```text
QuestionInput → fresh DocumentStore and RAIRState
  → RAIRDecomposer → actionable gap selection
  → RAIRQueryPlanner + BM25
  → RAIREvidenceFilter → RAIRFactExtractor
  → RAIRVerifier → admit accepted facts / possibly resolve gap
  → repeat while actionable and within limits
  → common RAIRSynthesizer → answer + original citations, abstention, or explicit error
```

**Shared structures in `src/rair/state.py`:**

| Structure | Actual contents and meaning |
| --- | --- |
| `Gap` | ID, description, high/medium/low priority, dependency IDs and resolved flag |
| `Evidence` | Original document ID/title, nonnegative sentence indices and exact selected text |
| `CandidateFact` in `fact_extractor.py` | Proposed statement tied to a gap and supplied evidence; not yet accepted knowledge |
| `VerifiedFact` | Software-managed fact ID, statement, gap ID and supporting evidence |
| `QueryAttempt` | Round, gap, query, retrieved document IDs, retrieval success/failure and evidence feedback |
| `RAIRState` | Question, max/current rounds, gaps, admitted facts and query history; `actionable_gaps`, `resolve_gap`, `record_query`, `is_complete` |
| `RAIRResult` | Prediction/status/stop reason, sources, final state, rounds, model calls, usage, error, budget and planner stalls |

**Responsibilities:**

- `RAIRDecomposer.decompose/parse_payload` produces validated ordered gaps, with bounded count and dependency validation. There are at most six gaps under the current schema. Invalid graphs/identifiers fail instead of being guessed.
- `select_next_gap` prioritizes fewer prior attempts, then priority and original order, among unresolved dependency-satisfied gaps excluding stalled ones.
- `RAIRQueryPlanner.plan` sees the original question, current gap, accepted statements and past attempts/feedback. Normalized duplicates are rejected.
- `RAIRRetrievalStep.run` checks the retrieval budget before spending another planner call. A duplicate query can fall back once to the original question; the fallback is a charged retrieval. Another duplicate stalls that gap while other actionable gaps may continue.
- `RAIREvidenceFilter.filter` uses short runtime sentence aliases (`E1`, etc.), constrained to actual retrieved sentences. Software reconstructs original locations and text. Empty selection is allowed.
- `RAIRFactExtractor.extract` proposes claims using supplied evidence references; software assigns candidate IDs. Empty candidates are allowed.
- `RAIRVerifier.verify` requires a decision for every candidate. `VerificationDecision.accepted` requires support, relevance and answer-type checks to be true, and unresolved-placeholder detection false. `resolves_gap` is separate from acceptance. `commit_decisions` promotes accepted claims and only resolves a gap through an accepted resolving claim. Supported bridge facts may be admitted without completing a gap.
- `RAIRSynthesizer.synthesize` passes original question, accepted statements and unresolved gap descriptions to the common final policy. Unresolved planning hints are not an automatic veto if facts already support the full answer.

**Stopping:** all gaps resolved, round ceiling, no actionable/unstalled gaps, repeated-query exhaustion, common retrieval/model budget, or explicit role/transport/validation failure. Empty retrieval/evidence/candidates are normal outcomes and do not resolve a gap. Retrieval “success” only means a positive BM25 match, not answer correctness. Synthesis can still answer or abstain after a normal search stop.

Current native RAIR policy at five rounds is **5 retrievals and an estimated upper bound of 27 model calls**, including extra stalled planners. The paired benchmark and live dashboard instead attach **4 retrieval / 18 model-call** common budgets. Older documents saying 22 native RAIR calls are stale; use `RAIRController.policy` and `docs/RAIR.md` for the corrected ceiling.

“Verified” is an admission state based partly on model judgments. It is not independent proof of truth or entailment.

### 3.3 Competitive KAIR

Entry point: `src/kair/controller.py::KAIRController.run(task)`. Only `competitive_local` is implemented.

`KAIRState` in `src/kair/state.py` contains agent ID/seed, private `known` facts, `required` strings, query history, original-source `context`, initialized/status flags and next fact number. `KAIRFact` contains fact ID, statement and evidence. A state is complete only after initialization, with nonempty accepted knowledge and no remaining requirements; initial empty requirements do not constitute a solution.

`KAIRAgent.step` in `src/kair/agent.py` performs:

1. Plan one new BM25 query using the whole question, private K/R/Q and available private/shared context.
2. Retrieve with the same retriever and shared budget; preserve the attempt even if later validation fails.
3. Merge incoming selected source context with retrieved original sentences.
4. Update candidate claims and a proposed replacement requirements list. Program assigns candidate IDs; current update allows at most four candidates.
5. Separately check which existing private facts to keep, which candidates to admit and what requirements remain. ID schemas are constrained to actual known/candidate IDs.
6. Filter original sentence context using per-document available source/index constraints. Valid repeated-document selections are combined after validation.
7. Commit K/R/context together only after update, checking and filtering succeed. A passing checker alone is not a committed private-state update.

The controller creates two agents with base seed and base seed + 1. Their role-neutral templates are identical; agent IDs primarily identify traces. Each competition iteration supplies every candidate the same frozen incoming shared context. Starting agent order rotates between iterations. An initialized complete agent stops later scheduled work. Otherwise `select_candidate` chooses an initialized non-error proposal with the fewest unresolved requirements, breaking ties by supplied execution order. Only its **original source context** becomes shared; other agents' fact IDs, private facts and requirements are not merged.

Malformed output/invalid evidence/transport failures retire that agent for the question; a healthy competitor may continue. A stalled agent may run again in a later iteration after new context arrives. All-agents-failed/no valid proposal is a question error. Other stops include agent completion, budget, max iterations, unchanged context with no active agents and all-agent stalls.

Default native limits are 2 agents × 2 iterations × 2 steps = **8 retrieval cycles and 33 model calls**. The common 4/18 cap is shared by all agents together, not multiplied per agent. Final synthesis uses the selected agent's accepted facts and remaining requirements through `RAIRSynthesizer.synthesize_knowledge`; it does not simply answer from the union of every retrieved document.

`KAIRResult` retains all private states, selected agent, iterations, incoming/published context, isolated agent errors, final answer/sources, calls and usage.

### 3.4 Final answer policy and source validation

Both systems use `src/rair/synthesizer.py` and `src/llm/prompts.py` for the common final policy, with temperature zero and the base seed. A runtime schema permits either consistent empty-answer abstention or an answer citing available fact IDs. With no facts, only abstention is allowed. `parse_payload` validates output shape/citations; `resolve_sources` maps cited facts back to deduplicated original sentences.

This controls final-generator policy, but not the semantic content/ordering of each architecture's admitted facts and requirement descriptions. The original synthesizer interface remains, but an architecture-specific versus common-generator ablation has not been conducted. Source-valid citations do not independently establish final-answer entailment.

## 4. Reconstructable development history and superseded decisions

| Stage | Established work and rationale | Evidence and status |
| --- | --- | --- |
| Imported prototype | The user started this version separately from an earlier project, using ChatGPT web. The master prompt described existing setup, loader, BM25, metrics, state and role checks, with full workflow execution still needing confirmation. Do not claim Codex originally authored every imported file. | Original attachment; `results/phase2_*` through `phase7g_*`; source role modules |
| Step 1 | Connected/verified RAIR end to end: bounded controller, strict role/source contracts, citations, traces, diagnostic writer, complete/missing synthetic cases and HotpotQA diagnostics. | `docs/RAIR.md`, `tests/test_rair_*`, `results/phase8_rair_pipeline_*.json`, `results/rair_*.jsonl`; Step 2 notes report 126 preexisting tests |
| Step 2 | Implemented a competitive KAIR baseline, private state and winner-context selection. Serial scheduling and explicit finite launches were local GPU adaptations, not asynchronous replication. Invalid IDs/partial commits were rejected rather than repaired. | `docs/KAIR.md`; 150 historical tests; `results/step2_kair_pipeline_*.json`, `results/kair_*.jsonl` |
| Step 3 | Wrapped both in a common evaluator because standalone temperatures/native limits differed. Added reserved final call, frozen selection/schedule/source hashes, scoring, retained failures and resumable journals. | `docs/EVALUATION.md`; 168 historical tests; 4-question/16-arm paired pilot |
| Step 4 | Ran a prospective 100-question/400-arm untouched comparison. Exposed RAIR validation failures and over-abstention. | `docs/BENCHMARK.md`; raw journal and `results/step4_validation.json`; no current-source inference rerun performed here |
| Step 5 | Used already exposed failures for development. Replaced fragile generated source IDs with aliases, assigned candidate IDs in software, required keyed complete verifier decisions, prevented rejected resolution, admitted supported bridge facts, improved gap scheduling/fallback, relaxed an unnecessary unresolved-gap final veto. | `docs/RAIR_IMPROVEMENTS.md`, `tests/test_step5_improvements.py` |
| Step 5 control design | Chose a fresh same-question three-arm experiment with the archived Step 4 RAIR core and current shared final policy. This superseded using different-cohort Step 4/5 scores as a causal repair estimate. The isolated reference process avoids import/state mixing. | `src/rair/reference.py`, `config/step5_reference.json`, 600-arm Step 5 journal; historical 190/191-test snapshot/current checks recorded separately |
| Standalone ceiling correction | Accounted for extra stalled-gap planner calls in RAIR's native upper bound; retained paired caps. Offline replay checked prior RAIR traces. | `docs/RAIR_IMPROVEMENTS.md`, `results/step5_replay.py`, `results/step5_current_verification.json`; old 22-call prose remains in some docs |
| Step 6 | Built the approved visual concept into a working local dashboard, connected to both real engines with editable inputs, citations, traces, downloads and separate recorded results. Retained a dependency-light Python HTTP/static JS app rather than replacing it with the originally preferred Streamlit. | `docs/DASHBOARD.md`; 207 historical tests; five browser comparisons/ten real engine runs in verification |
| Step 7 | Created the historical teacher report, editable slides, demo/viva material, PDFs and failure review, with blank personal cover fields as requested. | `deliverables/step7/`, generic teacher ZIP, `results/step7_verification.json`; 207 tests, 600-run audit, two new browser comparisons; native Word/PowerPoint artifact checks recorded |
| 30 October review | Fixed KAIR source schemas and merging of valid repeated-document selections; structural validation stayed strict. Tried stronger prompt wording, neutral verifier-field naming and missing-information-first synthesis. These trials did not reliably solve bridge/negative/comparison failures; RAIR/common-final prompt trials were discarded, not promoted. | `docs/PROJECT_REVIEW.md`, `results/post_presentation_20261030/{changes.patch,prompt_trial_roles.json,prompt_trial_pairs.json,verification.json}`; 210 historical tests and eight final paired diagnostic engine runs |
| Step 8 | Expanded the initial dashboard to the original five research views, detailed structured timelines, actual benchmark charts and searchable recorded failure analysis. This addressed the gap between the first UI and the full research aim. | `docs/RESEARCH_DASHBOARD.md`, `results/step8_validation.json`, browser checks; 223 historical tests |
| Responsiveness update | Added optional detached stage callbacks, lightweight cursor polling, one-time completed result retrieval and deferred raw JSON formatting. This reduces transfer/re-rendering and improves feedback; it does not accelerate model generation itself. | `src/progress.py`, controllers, dashboard and `tests/test_live_progress.py` |
| Connection failure repair | User saw “Unknown endpoint / connection interrupted” despite passing shell tests. An older server serving newer JS was the documented diagnosis. Added capability advertisement, legacy full-poll fallback for absent progress endpoints and transient banner clearing on success. User confirmed the dashboard and compatibility tests worked. | `docs/LIVE_UPDATES.md`, `tests/live_progress_client.cjs`; exact original host event is not a newly reproduced failure |
| Testing workflow | User initially asked to run tests personally and send output. Later they explicitly restored autonomous testing and asked for concise completion updates. The later authorization supersedes the earlier manual-test workflow. | Visible conversation; current handoff tests were executed by Codex |
| Step 9 | Added no-verification and no-decomposition interventions, kept common final policy, froze 20 new questions and ran four arms/160 runs. Reported adjusted uncertainty instead of assuming each role helps. | `docs/ABLATIONS.md`, frozen manifest/journal, `deliverables/step9/`, 239 historical tests and four browser engine runs; both component intervals include zero |
| Step 10 freeze/execution | Kept the exact Step 9 main engine source, excluded 245 prior IDs, froze 100 new questions/two seeds/400 arms with KAIR-minus-RAIR EM primary. An initial foreground worker stopped after one completed arm. A persistent worker resumed the original journal and preserved completed work. | `results/step10_build/prepare.py`, manifest, source ZIP, initial/resume logs; journal began 30 October UTC and was resumed on 31 October |
| Step 10 dashboard additions | Reused the verified study reader for confirmation summaries and case traces; added measured charts, intervals, computation and paired outcomes. Added route/corruption/origin tests. | `ConfirmationStudy`, confirmation API routes, `loadConfirmation/loadConfirmationCase`, 242-test suite |
| Step 10 interruption | Physical Escape stopped Computer Use during preparation for native document export. The chat ended with 377/400 last observed; the independent worker continued and finished. It did not produce the new teacher materials by itself. | Visible interruption plus completed raw journal and absent deliverables |
| This handoff | Reinspected current code/evidence, freshly ran tests/JS checks, read-only audited Steps 9/10 and checked Step 10 source ZIP/exclusions/actual confirmation reader. Wrote only these two root Markdown handoff files. | Verification details below; no new model inference, application patch, report build or Git initialization |

Journal opening timestamps are actual recorded UTC metadata, not dates inferred from random seeds: pilot `2026-10-18T13:29:49Z`, Step 4 `2026-10-18T13:41:58Z`, Step 5 `2026-10-18T16:01:35Z`, Step 9 `2026-10-30T15:21:55Z`, Step 10 `2026-10-30T16:23:39Z`. A bootstrap seed resembling a later date is an integer parameter, not evidence of the run date.

## 5. Current implementation and delivery status

| Component | Status supported by evidence | Remaining qualification |
| --- | --- | --- |
| Local client, loader, BM25, metrics | Implemented and tested | One dataset adapter/retrieval setting; not general document ingestion |
| Full RAIR | Implemented; current 200 confirmation runs audited | Model judgment, decomposition completeness, final answer type and abstention remain unreliable |
| Competitive KAIR | Implemented; current 200 confirmation runs audited | Serial local adaptation and common final generator; not a published-score reproduction |
| Common evaluator and recovery | Implemented and tested | Strict source freezes require preserved versions for historical replays; no strict overall token/wall-clock cap |
| Step 9 component study | Executed, audited, historical artifacts available | Only 20 clusters; no established component benefit; native opening of its updated deck was not checked in its verification |
| Step 10 benchmark | **Executed and freshly read-only audited: 400/400** | This does not finish its downstream report/presentation tasks |
| Five-view research dashboard | Implemented; historical live/browser evidence and current tests | Current Step 10 reader/case payload verified directly; new confirmation browser/native artifact acceptance remains unperformed |
| Step 7 teacher package | Historical completed release | Describes Step 5 results/earlier revision, not the current confirmation |
| Step 9 presentation update | Historical completed release | Original 12 historical slides plus three exploratory appendices; not a consolidated Step 10 deck |
| Step 10 analysis/review outputs | Draft scripts written; outputs absent | Need execution, review and honest interpretation of KAIR's advantage |
| Step 10 final report/slides/demo/viva/PDF/ZIP | **Not delivered** | Builder source is not proof of successful generation, rendering or content validation |
| MuSiQue, additional models, round/agent-count/generator sweeps | Planned research | No measurements or complete integrations established |
| PDF upload/OCR, evidence graph, production hosting/auth | Suggested future work | Not part of the current working application; do not advertise as implemented |
| Git version history | Absent | No commits/branches to transfer; preserve frozen hashes and snapshots |

At inspection the following were absent: `deliverables/step10/`, `deliverables/RAIR_KAIR_Final_Teacher_Package_Step10.zip`, `results/step10_analysis.json`, `results/step10_verification.json`, `results/step10_browser_checks.json`, `results/step10_build/reviewed_cases.json`, `visual_review.json` and `presentation.validation.json` in that build folder. The Step 10 scripts depend on several of these and are not yet an executed release pipeline.

## 6. Measurements and testing

### 6.1 Fresh handoff verification on 1 November

- Full command `python -X utf8 -B -m unittest discover -s tests -v` through `.venv`: **242 tests, 0 failures/errors, 17.849 seconds, exit 0**.
- Node syntax checks of `dashboard/static/app.js` and `research.js`: exit 0.
- `tests/live_progress_client.cjs`: PASS for delta polling, replay, result retrieval, stale responses, older-server compatibility and genuine error handling.
- **Read-only** verification of Steps 9 and 10 using `read_journal`, `load_manifest_examples`, `audit_result`, `score_result`, `RunBudget` and fingerprints: **160 and 400 records passed**, including stored post-inference scores and common settings/budgets. Summary files match journal summaries and recomputed aggregates. Current source matches each manifest.
- Step 10 source ZIP CRC/member hashes and exclusion disjointness passed. Its 100 IDs do not overlap the 245 exclusions or Step 9 questions. The saved exact normalized text exposure audit reports no matches across its 24 prior sources; this does not rule out paraphrase overlap or pretraining exposure.
- Actual `ConfirmationStudy.describe()` returned 400 runs/200 pairs, and `case()` returned both engine traces for a real recorded pair, without inference.
- Independent request inspection checked 1,457 recorded Step 9 model attempts and 3,951 Step 10 attempts: every request had `think=false`, and all 160/400 respective final calls used the current common final system prompt. These counts exclude the separately logged warm-ups and any interrupted uncommitted work.
- Before/after SHA256 comparison found **no changes to 104 protected preexisting application, dashboard, test, configuration, requirements, README and launcher files**. The two new root Markdown files are the handoff outputs.

The current Python tests largely run real controller/validation/retrieval code with scripted model transport. They establish software contracts, not semantic model accuracy. Real Ollama accuracy evidence comes from the saved benchmarks, and historical live demonstrations establish only their exercised cases. No new browser session, native Office export, model generation or cross-machine test was run for this handoff. Fresh test output was inspected in the tool session rather than written over historical logs.

### 6.2 Cohorts must remain separate

Percentages below are over every scheduled arm per system, including errors and abstentions.

| Study | Questions × seeds × arms | RAIR EM / answer F1 | KAIR EM / answer F1 | Interpretation |
| --- | --- | --- | --- | --- |
| Step 3 pilot | 4 × 2 × 2 = 16 | 25.0% / 30.6% | 50.0% / 61.3% | Integration pilot; not a final claim |
| Step 4 historical | 100 × 2 × 2 = 400 | 23.0% / 29.8% | 36.0% / 50.5% | KAIR-minus-RAIR EM +13.0 pp, 95% CI +5.5 to +21.0; older engines |
| Step 5 historical | 100 × 2 × 3 = 600 | 40.5% / 47.1% | 36.0% / 45.5% | Main contrast is repair versus old-core control; R versus K inconclusive |
| Step 9 exploratory | 20 × 2 × 4 = 160 | 50.0% / 60.6% | 55.0% / 74.7% | Component study; small sample |
| **Step 10 current confirmation** | **100 × 2 × 2 = 400** | **37.0% / 45.4%** | **50.0% / 63.1%** | **Paired primary EM interval favors KAIR in this protocol** |

Step 4's EM difference/interval happens to equal Step 10's; these are different question cohorts and source versions, not the same journal. Their distinct manifests and raw hashes establish identity. Do not confuse the numerical coincidence with a copied result.

Step 5's reference arm scored 18.5% EM / 21.9% F1, with 111 abstentions and 24 errors. Updated RAIR minus this **same-question old-core/current-final-policy** control was +22.0 EM points, 95% interval +15.0 to +29.5. That supports a bundle of core repairs conditional on the shared policy. Updated RAIR minus KAIR was +4.5 points, interval -3.0 to +12.0, which did not establish superiority.

Step 9 no-gate EM/F1 was 55.0%/73.0%; no-decomposition 47.5%/63.6%. Full RAIR minus no gate EM was -5.0 pp, 97.5% interval -15.0 to +5.0; full minus no decomposition +2.5 pp, interval -15.0 to +17.5. Both include zero. The two prespecified EM contrasts used 97.5% pointwise intervals for approximately 95% family coverage. Full RAIR versus KAIR was secondary. Removal effects also change computation and stopping.

### 6.3 Current Step 10 detailed results

Authoritative files: `config/step10_benchmark.json`, `results/step10_benchmark.jsonl`, `.summary.json`, and `.md`.

| Metric, 200 runs per system | RAIR | KAIR |
| --- | ---: | ---: |
| Exact match | 37.0% (74) | 50.0% (100) |
| Answer F1 | 45.3639% | 63.1274% |
| Answered | 129 | 183 |
| Coverage | 64.5% | 91.5% |
| Abstained | 71 | 17 |
| Question execution errors | 0 | 0 |
| Isolated agent error events | 0 | 3 |
| Citation precision / recall / F1 | 53.225% / 41.2583% / 44.6500% | 69.950% / 59.0250% / 61.3226% |
| Document retrieval precision / recall / F1 | 42.1268% / 89.0000% / 56.2968% | 49.8679% / 84.0000% / 62.0460% |
| Mean LLM calls | 12.525 | 7.230 |
| Mean retrievals | 2.665 | 1.555 |
| Mean recorded prompt tokens | 9228.630 | 9299.800 |
| Mean recorded output tokens | 716.585 | 747.480 |
| Mean total recorded tokens | 9945.215 | 10047.280 |
| Mean controller seconds | 16.5959 | 16.8955 |
| Budget-stop records | 67 | 3 |

All listed answer/source/retrieval metric denominators are 200. Both systems have zero annotation-issue runs and zero incomplete-token-count runs in this study.

Primary KAIR-minus-RAIR EM: **+13.0 pp**, 95% interval **[+5.5, +21.0]**. Secondary answer F1 difference: **+17.7635 pp**, pointwise interval **[+10.7085, +25.1846]**. Bootstrap: 10,000 resamples, seed `20261101`, averaging the two seeds within each of 100 question clusters. This is not 200 independent questions or 400 independent samples. The F1 interval is secondary, without a separate multiple-comparison claim.

Seed-specific EM outcomes: both exact 63 pairs, RAIR only 11, KAIR only 37, neither exact 89. There are 152 ties, including both-exact and neither-exact. Answered-but-nonexact counts are RAIR 55 and KAIR 83; nonexact does not automatically mean semantically false.

RAIR stop reasons: 118 `all_gaps_resolved`, 15 `repeated_query`, 67 `budget_exhausted`. KAIR: 197 `agent_complete`, 3 `budget_exhausted`. A stopping reason is not the same as an answer status. In particular, completeness judgments do not guarantee a correct answer. Fifty RAIR abstentions and four KAIR abstentions occurred despite retrieving all annotated support titles. This indicates downstream selection/admission/synthesis limitations worth investigating, not proof of one isolated cause.

### 6.4 Integrity identifiers and execution caveat

Model tag `qwen3.5:4b`; recorded metadata describes a 4.7B `Q4_K_M` model. Actual experimental context is 4096, irrespective of the model's larger advertised capability.

```text
Model digest
2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd

Dataset SHA256
4e9ecb5c8d3b719f624d66b60f8d56bf227f03914f5f0753d6fa1b359d7104ea

Step 9 manifest fingerprint
969462b4f3bc1ec5c568d4872c3169e37665d4d63f2764aafc236ef8f26f5fc1
Step 9 journal SHA256
7cd67dc416bd20de9d55aa5313d3a6941a0d45dc9fad6e1d5dbb0cff5a449db2

Step 10 manifest fingerprint
8ff50f4d90ec2774a1f23f5e16b0473466f069855e6aaf32df23e90feee3a7a2
Step 10 journal SHA256
9d55b5a02a0d6dd45066df2cf698a9ce264779b2389766fce459887b0e3e7ed8
```

A manifest fingerprint is `fingerprint(manifest)` over canonical JSON, not necessarily the hash of its pretty-printed file bytes. Dataset/journal digests above are byte hashes.

Steps 3–5 recorded Ollama **0.40.6**; Steps 9/10 recorded **0.40.13** with the same model digest. This prevents attributing differences between cohorts solely to an architecture patch.

Step 10 has one metadata record, **two warm-ups**, 400 result records, one consistent final verification and one summary. The extra warm-up reflects resume. The initial completed arm was preserved; only unfinished work was repeated. Usage means cover recorded arms and omit interrupted uncommitted work. Local controller time excludes warm-up and is not total elapsed batch time or a hardware-independent speed claim.

### 6.5 Historical testing and failures

`results/step7_verification.json` records 207 tests, the 600-run audit, two new paired browser rehearsals and artifact/native application checks. `results/step8_validation.json` records 223 tests and four real live engine outputs. `results/step9_verification.json` records 239 tests, 160 audited arms, four live engine outputs, desktop/narrow checks and structural presentation validation; its statement that Step 10 has not run is historical.

Step 10's initial full test run had one Windows `ConnectionAbortedError [WinError 10053]` in an existing cross-origin HTTP rejection test. Its isolated suite and later full suites passed; the final saved log reports 242 tests. `results/step10_test_checks.json` and the initial/recheck/final logs retain this instead of erasing it. The handoff's fresh 242-test run also passed. This does not establish that the intermittent host event has a proven permanent root-cause fix.

## 7. Experimental fairness and paper fidelity

| Control | Implemented behavior | Important limit |
| --- | --- | --- |
| Model | Same tag, recorded digest/version checked before/after benchmark | One local quantized model; same weights do not imply cross-runtime bitwise determinism |
| Input | Same `QuestionInput` document pool per matched pair | Public HotpotQA dev distractor pools, not hidden test or unrestricted corpus |
| Gold isolation | Separate labels; post-inference `score_result`; mutation tests | Does not rule out pretrained model exposure to public data |
| Retrieval | Same document store/BM25/top 3/preprocessing | Architectures generate different queries and may use different numbers of searches |
| Limits | One `RunBudget(4,18)` per arm; KAIR agents share it; final call reserved | Ceilings are not matched realized tokens/calls or overall wall time |
| Decoding | Non-final 0.7 via `generation_temperature`, final 0, context 4096, output 512, thinking false | Standalone RAIR normally requests temperature 0; diagnostic native limits differ |
| Seeds | Same base seeds 42/43; KAIR private seeds base + agent index | Exploration policy differs by design; two seeds provide limited seed robustness |
| Order | Serial counterbalanced R/K schedule; rotated starting arm for component study | Not asynchronous, not exhaustive over all predecessor/cache orders |
| Final answer | Shared synthesizer/prompt/validator | Fact/requirement representations differ; comparison is the whole local workflow under that policy, not pure retrieval alone |
| Failures | Attempted calls charged; errors/abstentions retained; separate agent errors | Uncommitted interrupted work cannot be included in recorded per-arm cost means |
| Scoring | Same lexical and source-set scorer; union of all paid retrievals includes losing KAIR agents | Gold-reference overlap is not human-assessed semantic grounding |

`docs/KAIR.md` records a mapping to journal Algorithm 3 and DOI `10.1109/TCSS.2026.3668728`, and distinguishes the earlier preprint from the journal version. This handoff verifies the implementation and that mapping's presence; it does **not** newly retrieve/revalidate the external paper or independently certify exact paper fidelity.

Documented deviations include serial early skipping instead of asynchronous race/cancel, finite two-step launches/two competition iterations, local model/distractor pools, constrained structured operations and a common fact-based final generator rather than the paper's separate generator over refined context. KAIR has its own fact checking; “RAIR verifies but KAIR does not” is false. A dissertation reviewer should compare the actual journal text and these choices directly.

A defensible present claim is: **the project implements and evaluates an inspectable role-specialized workflow against a documented local competitive KAIR adaptation; the larger current confirmation favors KAIR on EM, while individual RAIR component benefits remain uncertain.** This does not prove KAIR universally superior or RAIR useless.

## 8. Dashboard implementation and verification boundary

Backend: `dashboard/server.py` (`Dashboard`, `custom_task`, `make_server`, `main`). Frontend: static `index.html`, `styles.css`, `app.js`, `research.js`. No frontend framework/build process or Streamlit dependency is required.

| Screen | Implemented functionality | Verification boundary |
| --- | --- | --- |
| Research objective | Fictional two-hop chain, original comparison question, separate historical/current evidence framing | Present in current source; prior five-view checks historical |
| Architectures | RAIR roles/shared state and competitive private agents/context sharing | Describes structured operations, not hidden chain of thought |
| Live execution | Example selector, seed, editable question/source sentences, real R/K run, active phase/counters, stage events, citations, final detailed traces/raw JSON/download | Historical complete/missing/custom/labeled demonstrations and current service/client tests; fresh Step 10 browser rehearsal pending |
| Benchmark | Historical Step 5 charts; separate Step 9 four-arm tables/charts/adjusted contrasts; new Step 10 two-arm quality/cost/interval charts and 200 paired outcomes | Current Step 10 completed-data reader/case verified directly; browser rendering/interaction not newly accepted |
| Findings/failures | Step 5 historical case search, seed/outcome/diagnostic filters, pagination, source pools, gold supports, manual notes and paired timelines | This searchable archive is still Step 5; Step 10 has a separate inline trace inspector under Benchmark, not an equivalent full searchable failure browser |

Important API routes:

```text
GET  /api/bootstrap, /api/health
POST /api/runs
GET  /api/runs/<id>
GET  /api/runs/<id>/progress?after=<cursor>
GET  /api/runs/<id>/results/RAIR or KAIR
GET  /api/runs/<id>/download
GET  /api/research, /api/research/cases, /api/research/case
GET  /api/ablations
GET  /api/confirmation
GET  /api/confirmation/case?question_id=<id>&seed=42
```

`ResearchArchive` validates/indexes the historical journal by offsets and binds optional review notes to its hash. `AblationStudy` and `ConfirmationStudy` verify manifests, journal/summary consistency and expected arm sets, cache by file signature and reject inconsistent data. Current confirmation cases return original recorded results/evaluations, not new model runs. Their inline inspector does not currently provide the historical case browser's full gold-source/filter interface.

Live status uses 500 ms cursor polling, only new detached events and compact counters. Finished full engine results are fetched once; raw JSON formatting is deferred. `live_progress_v1` capability detection and a 1200 ms legacy full-poll fallback support older servers. New events can contain the excerpts needed to explain that stage, so they are not constant-size responses.

The server binds to `127.0.0.1`, checks Host/Origin, serves an explicit asset/API allowlist, uses CSP/no-store/nosniff, validates JSON body sizes and custom sources, and uses text content for untrusted text. It is a local presentation app, not an authenticated public service. One comparison is admitted at a time. Inputs are locked during inference; newest 20 jobs/events are retained in memory, while journals remain on disk. After restart, old in-memory run URLs/events are not reconstructed automatically.

Actual server/model process liveness and the current browser console were not checked in this handoff. Existing stdout files alone do not establish that a service is running today. Launch it as described below. No automatic service restart or browser actions were needed for writing these documents.

## 9. Bugs, failed experiments and technical debt

### Established unresolved research limitations

- **Accuracy hypothesis not confirmed:** Step 10 favors the competitive baseline; presenting an inconclusive historical R/K result as the latest conclusion would be wrong.
- **Excessive RAIR abstention remains:** 71/200 versus 17/200. Fifty RAIR abstentions had full support-title retrieval. Retrieval, selection, admission, gap completeness and final synthesis need separate diagnosis; aggregate recall alone cannot identify causality.
- **Model-dependent verification/completeness:** useful bridge/negative evidence can be rejected; an incomplete relation graph can omit the requested answer relation; comparisons and final answer types can be wrong despite correct source facts. See the recorded October review and Step 9 failure review.
- **No independent hallucination/entailment evaluation:** citation validity/source overlap and semantic model checks are distinct. There is no calibrated confidence/risk assessment or human grounding study.
- **Limited generality:** one model, two seeds, public dev pools, local serial execution; no MuSiQue, multi-model replication or official hidden-test evaluation.

### Engineering and delivery debt

- README's Step 10 status and 239-test current count are stale. Some older native-call ceilings (22) and future-work statements contradict current code. Existing teacher PDFs/decks need clear historical labeling and a consolidated replacement.
- The Step 10 builder chain is incomplete: `analyze.py` would create analysis/verification/census/case traces; manual `reviewed_cases.json` is absent; document/slides builders rely on missing files. `package.py` also needs browser/visual receipts and final outputs. It would update README and presentation documentation if run, so it was deliberately not executed as part of this handoff-only task.
- Artifact builders hardcode this Windows root, user-specific bundled runtime/skill paths and date text. Some historical scripts use native Office automation. These are environment-specific authoring utilities, not installed application dependencies or a portable release build system.
- DOCX rendering was previously adapted to use Word-exported PDFs because LibreOffice was absent; the Step 10 renderer has that callback but has not produced new renders. The historical bundled slide PDF export had a font-module limitation. Do not claim native PDF success for Step 10 from old Step 7 receipts.
- Progress is held in memory; engine results/journals persist, but interactive live event replay does not survive server restart. In-flight calls are not checkpointed. No user-facing cancellation of a running generation is established.
- A CLI benchmark and live dashboard use independent execution paths; the dashboard's one-job lock is not a global interprocess GPU lock. Avoid simultaneous benchmark/live runs when collecting timings or enforce a future explicit scheduling policy.
- Large JSON journals, absolute build-runtime junctions and duplicated snapshot trees complicate transfer. `.gitignore` excludes raw/processed data and results; a future Git repository alone would omit much essential research evidence unless an artifact plan is added.
- Source freezes include every `src/*.py` and `requirements.txt`, but not dashboard/static/test/docs files. Freeze identity is a core-code control, not a signature over the entire final UI/release.
- Resume intentionally refuses a partial final JSONL line, changed source/data/runtime, reordered records or altered scores. This protects integrity but needs an explicit recovery/archive procedure for interrupted writes; do not manually delete/repair records silently.
- The historical isolated reference process and shared synthesizer couple baseline evaluation to concrete archived source and current Python/runtime paths. Preserve and inspect those snapshots before reusing the old-core control.
- One intermittent Windows cross-origin HTTP connection abort was observed in a saved test run; isolated/subsequent suites passed. There is no established current valid-request browser failure from that event, nor a demonstrated permanent host-level fix.
- The earlier “Unknown endpoint” UI error was addressed by compatibility fallback and restart discipline. Serving new static files from a stale Python process remains a deployment/version-consistency concern worth retaining regression coverage for.

### Decisions not to misrepresent

Discarded prompt trials are failed/diagnostic experiments, not verified accuracy improvements. No-gate ablation facts remain **unchecked** even though the inherited field is named `verified_facts`. A common final schema validates structure/citation membership, not entailment. An exact-match failure can be a lexical/alias issue; an exact match is also not a standalone proof of faithful reasoning. Software test success does not imply 100% model accuracy.

## 10. Prioritized remaining work

### P0 — Finish an honest current examiner package

1. Preserve the completed Step 10 manifest/journal/source ZIP and their hashes. Do not resample/rewrite it or selectively regenerate poor outcomes. This handoff's audit already establishes 400 completed arms.
2. Produce the pending post hoc analysis/census from the completed evidence; inspect deterministic examples from both directions and neither-exact groups. Distinguish measured counts, observed trace facts and causal hypotheses. Check aliases/answer types before labeling all nonexact answers false.
3. Complete current browser acceptance on the same-source dashboard: confirmation values/charts/interval signs, all paired outcomes, trace inspection, successful complete/missing-source live comparisons, active updates, downloads, recovery and desktop/narrow layout. Keep historical views separately labeled. Record actual IDs/statuses/console observations.
4. Build a consolidated final report, approximately 14-slide draft deck, 5–7 minute demo and 30-question viva notes. Update all claims to the Step 10 result; explain the Step 5 repair gain and Step 9 uncertainty separately. Leave personal cover fields blank as the user requested.
5. Render and inspect every final document page and slide; export PDFs; validate editable chart values/workbooks, tables, citations and layouts. Native application checks belong to the actual final revision, preferably using a private copy for edit tests.
6. Assemble the final teacher ZIP with precise setup instructions, source/data/artifact availability, frozen evidence, census and verification/checksums. Check ZIP CRCs/entry hashes and reproduction from an isolated extracted source copy. No such ZIP currently exists.
7. Reconcile README/current documentation and give one unmistakable current-package pointer while preserving old releases as historical. The handoff task itself intentionally does not make these edits.

### P1 — Dissertation-quality research and review

1. Obtain the exact KAIR journal source and independently audit Algorithm 3 fidelity and all adaptations. Establish a literature-based contribution claim beyond combining standard components. Current local superiority of RAIR cannot be claimed.
2. Diagnose RAIR's abstentions and relation coverage using exposed cases, source-grounded human review and explicit error categories. Develop answer-type/completeness/negative-evidence tests with positive controls. Evaluate a proposed semantic answer auditor independently; another LLM check is not automatically a reliable fix.
3. Prespecify the next intervention, primary endpoint, sample size/precision goals and compute policy before fresh evaluation. Current Step 10 questions are now exposed. At least the union of its 100 IDs and prior 245 IDs must be excluded from a next untouched cohort, plus any other new demonstrations/exposures.
4. Add suitable simple retrieval/RAG controls and the planned retrieval-round, one-vs-two-agent and generator-policy ablations. Test removal effects under their stated compute/stopping interpretation rather than calling equal ceilings equal compute.
5. Expand models, seeds, datasets (including MuSiQue), question-type analyses and independent grounding evaluation. Report uncertainty, coverage/abstention risk, annotation issues and actual costs. Do not pool old cohorts as one causal comparison.
6. Separate development, confirmation and official hidden-test claims. Public-data pretraining exposure is unresolved. Preserve every failure and version; if engines change, prepare a new protocol instead of editing frozen source hashes.

### P2 — Maintainability and optional product value

Establish real version control and artifact storage, portable dependency/runtime metadata, reproducible release scripts and automated UI checks. Consider persistent live-job restoration, explicit cancellation and shared GPU scheduling. Document/PDF ingestion, page citations/OCR and a source-backed evidence graph could add demonstration value later, but are not prerequisites for truthfully reporting the present experiment and should remain separate from accuracy claims.

## 11. Exact PowerShell commands

Always begin in the project directory; the user's earlier `C:\Windows\System32` shell location caused relative `.venv` and test paths to fail before tests even ran.

### Environment and software checks

```powershell
Set-Location -LiteralPath 'E:\Projects\role_aware_kair'
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v

$rairNode = 'C:\Users\rahul\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
& $rairNode --check dashboard/static/app.js
& $rairNode --check dashboard/static/research.js
& $rairNode tests/live_progress_client.cjs
```

Focused suites:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_live_progress.py -v
.\.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_ablation_dashboard.py -v
.\.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_ablations.py -v
```

Project runtime dependency is `PyYAML==6.0.3`; Python 3.12 was used by the project environment. If rebuilding the environment on another computer, create `.venv` with Python 3.12 and install `requirements.txt`. Node is a development check tool, not required to serve the dashboard. DOCX/PPTX/PDF authoring uses additional bundled libraries outside this requirements file; do not assume those builders run in `.venv` unchanged.

### Audit already completed studies without new inference

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m src.experiments.compare run --manifest config/step9_ablations.json --output results/step9_ablations.jsonl --resume
.\.venv\Scripts\python.exe -X utf8 -B -m src.experiments.compare run --manifest config/step10_benchmark.json --output results/step10_benchmark.jsonl --resume
```

For a completed valid journal, these commands recheck calls/settings/budgets/inputs/scores and regenerate derived `.summary.json`/`.md` reports without calling the model. They **do write those derived reports**. For this handoff, the equivalent checks were called directly without `save_reports`, leaving existing artifacts untouched. If a journal is incomplete, `--resume` can generate its remaining arms; check completion before calling it. CLI exit 1 can also reflect retained question errors in a completed study; read the summary/error output rather than treating all nonzero statuses as the same failure.

Current source matches Steps 9/10. Historical Step 4/5 manifests generally require their saved source versions; do not alter their manifest hashes to force them through current code. Consult `docs/BENCHMARK.md`, `docs/RAIR_IMPROVEMENTS.md` and the preserved snapshots/reference layout.

### Repeat Step 10 inference on the same exposed cohort

With Ollama running and the recorded model/runtime available, choose an output filename that does not exist:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -u -m src.experiments.compare run --manifest config/step10_benchmark.json --output results/step10_replication_20261101.jsonl
```

This is replication on an already exposed cohort, not a new untouched test. Do not run it concurrently with live demos. Existing output paths are refused. A changed model/runtime/source is a different experiment.

### Prepare a genuinely new benchmark

First author a reviewed new settings file that explicitly fixes sampling/exclusions, endpoints, seeds, budgets and bootstrap parameters. Default `settings.yaml` still specifies a **four-question pilot**, not a 100-question confirmation. After that settings file exists:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m src.experiments.compare prepare --config config/reviewed_next_settings.json --output config/next_frozen_benchmark.json
.\.venv\Scripts\python.exe -X utf8 -B -u -m src.experiments.compare run --manifest config/next_frozen_benchmark.json --output results/next_frozen_benchmark.jsonl
```

The two `next` settings/manifest paths above are **future paths, not existing files**. Do not blindly run the command block before creating/reviewing the settings. `results/step10_build/prepare.py` is a one-off Step 10 freezer that intentionally refuses to overwrite the existing freeze; it is not the next-study command.

### Diagnostic real-model runs

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m src.experiments.check_setup
.\.venv\Scripts\python.exe -X utf8 -B -m src.experiments.check_rair_pipeline
.\.venv\Scripts\python.exe -X utf8 -B -m src.experiments.check_kair_pipeline
.\.venv\Scripts\python.exe -X utf8 -B -m src.experiments.run_rair --limit 3
.\.venv\Scripts\python.exe -X utf8 -B -m src.experiments.run_kair --limit 3
```

The role/pipeline/diagnostic runners can call Ollama and create outputs/expose questions. They are not replacements for the frozen paired benchmark and use standalone policies unless explicitly configured otherwise.

### Dashboard

If the installed local Ollama service is stopped, run the installed `ollama serve` in one terminal. It must have the configured model available; the application never auto-downloads it. In a second terminal:

```powershell
Set-Location -LiteralPath 'E:\Projects\role_aware_kair'
.\start_dashboard.cmd
# Equivalent:
.\.venv\Scripts\python.exe -X utf8 -B -u -m dashboard.server
# If 8765 is already occupied:
.\start_dashboard.cmd --port 8766
```

Open `http://127.0.0.1:8765/` (or the chosen port). Stop the foreground server with Ctrl+C. Restart an older server and refresh the browser after code changes; do not leave mismatched static/backend revisions. Recorded research browsing does not generate model calls; live comparisons do. Do not kill an active comparison just to refresh the server.

### Git status

```powershell
git -C E:/Projects/role_aware_kair status --short --branch
git -C E:/Projects/role_aware_kair rev-parse --show-toplevel
```

Both returned exit 1 with `fatal: not a git repository (or any of the parent directories): .git` at handoff inspection. No Git initialization, commit or application change was performed. Frozen snapshots and hashes are the existing provenance mechanism, not a substitute for an invented commit history.

## 12. Suggested entry order for the next reviewer

Read this document and the file map; inspect the Step 10 manifest/raw summary and the two controllers; review the shared client, final policy and evaluation audit functions; then examine current test coverage and the recorded failure reviews. Verify the actual journal before running any long inference command. Finish the missing Step 10 artifacts and browser checks before presenting the new result, and keep any further engine research on a new explicitly versioned protocol.
