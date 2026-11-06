# RAIR versus KAIR repository file map

Inspected **1 November 2026** at `E:\Projects\role_aware_kair`. Paths below are relative to that root unless explicitly absolute. This map covers active implementation files, configurations, tests, important documentation, frozen evidence and delivery/build utilities. Generated per-run files and duplicated historical source trees are identified by family rather than listing every copied package file or dependency binary.

Read [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) for measured results, development history, verification limits, priorities and exact execution commands. **Step 10 inference is complete; its final presentation package is not.** No `.git` repository was found.

## 1. Current structure

```text
role_aware_kair/
├── PROJECT_HANDOFF.md             Technical transfer and evidence/status record
├── PROJECT_FILE_MAP.md            This inventory
├── README.md                      Entry guide; some current-status statements stale
├── requirements.txt               PyYAML==6.0.3
├── start_dashboard.cmd            Windows launcher
├── .gitignore                     Ignore rules; does not imply Git initialization
├── .venv/                         Local Python environment, not project source
├── .chart-data-*/                 Generated presentation chart-data workspace
├── src/
│   ├── settings.py, progress.py
│   ├── datasets/                  HotpotQA input/gold adapter
│   ├── retrieval/                 Original source store and BM25
│   ├── llm/                       Local Ollama transport and RAIR/common prompts
│   ├── rair/                      Shared state, specialized roles, controller, controls
│   ├── kair/                      Private agents, prompts, state and competition
│   ├── evaluation/                Budgets, metrics, manifests, audits and uncertainty
│   └── experiments/               CLI runners, freezer and role diagnostics
├── dashboard/
│   ├── server.py                  Local HTTP service and live orchestration
│   ├── research.py                Frozen historical Step 5 archive/case index
│   ├── ablations.py               Step 9 and Step 10 verified result readers
│   └── static/                    HTML, CSS and browser JavaScript
├── tests/                         Python scripted-transport and HTTP tests; Node client test
├── config/                        Live defaults, frozen protocols and exclusion records
├── data/
│   ├── raw/                       Full supplied HotpotQA distractor development JSON
│   └── processed/                 Exposed development inputs and bound review notes
├── docs/                          Methodology, milestones, review notes and screenshots
├── results/
│   ├── *.jsonl, *.summary.json, *.md   Diagnostic/benchmark journals and derived reports
│   ├── *_validation.json, *_verification.json, *_tests*   Dated evidence
│   ├── *_source*.zip               Frozen source/archive versions
│   ├── post_presentation_20261030/  Retained maintenance/prompt-trial evidence
│   ├── step5_reference/            Archived old-core subprocess source
│   ├── step5_snapshot_validation/  Historical restored test copy
│   ├── step5_final_snapshot_validation/  Historical final restored test copy
│   ├── step7_build/                Historical authoring/render/application-check workspace
│   ├── step9_build/                Historical appendix authoring/validation workspace
│   └── step10_build/               Pending analysis and final-package builders
└── deliverables/
    ├── RAIR_KAIR_Teacher_Package.zip    Historical Step 7 package
    ├── Step9_Research_Update.zip       Historical component-study update
    ├── step7/                         Historical report/slides/demo/viva/PDFs
    └── step9/                         Findings, cases, census, screenshot and 15-slide deck
```

`deliverables/step10/` and `RAIR_KAIR_Final_Teacher_Package_Step10.zip` do **not** exist at this inspection. A directory or filename appearing in a builder is an intended output, not an existing deliverable.

## 2. Root files and dependencies

| File | Purpose / review note |
| --- | --- |
| `PROJECT_HANDOFF.md` | Current evidence-based handoff; separates completed inference, historical results and unfinished release work |
| `PROJECT_FILE_MAP.md` | Current implementation/evidence inventory |
| `README.md` | Setup and milestone guide; still says Step 10 has not run and includes older test counts; reconcile before presenting |
| `requirements.txt` | Only pinned application Python dependency: `PyYAML==6.0.3`; core HTTP/retrieval/evaluation use standard library |
| `start_dashboard.cmd` | Changes to its own directory and runs `.venv\Scripts\python.exe -X utf8 -B -m dashboard.server`; forwards port/config arguments |
| `.gitignore` | Ignores `.venv`, Python caches, `.env`, raw/processed data and results; important research artifacts need deliberate preservation when Git is later established |
| `.venv/` | Installed local Python environment; not a portable application/source archive |
| `.chart-data-*/` | Generated chart workbook materialization workspace; not an authoritative benchmark dataset |

The local model service is an external installed Ollama executable and model store, not a Python dependency or source module. Node is used for development checks and presentation authoring, not for serving this static dashboard. Artifact scripts additionally depend on bundled `python-docx`, `pypdf`, Poppler and `@oai/artifact-tool`/render helpers; these are not declared by the application's one-line requirements file.

## 3. Active source files

Line numbers below refer to this inspection and can drift in later edits. Function/class names are better stable search targets.

### Configuration, dataset and retrieval

| File | Main symbols | Purpose |
| --- | --- | --- |
| `src/settings.py` | `PROJECT_ROOT`, `project_path` (line 11), `load_settings` (16) | Root-relative settings/path handling; YAML-safe loading also accepts JSON settings; validates required sections without contacting Ollama |
| `src/progress.py` | `publish` (6) | Optional detached progress observer dispatch; failures do not stop inference |
| `src/datasets/hotpotqa.py` | `QuestionInput`, `GoldLabels`, `HotpotExample`, `parse_hotpotqa_record`, `load_hotpotqa` | Separate inference input from gold labels, preserve source sentences/indices and validate dataset shape/IDs |
| `src/retrieval/document_store.py` | `Document`, `DocumentStore`, `normalize_whitespace` | Per-question source ownership/lookup, searchable text and original indexed sentence access |
| `src/retrieval/bm25.py` | `tokenize`, `RetrievalResult`, `BM25Retriever.search` | Deterministic per-pool lexical retrieval, positive-score ranking, stable ties and optional charged retrieval budget |

### Local model and prompts

| File | Main symbols | Purpose |
| --- | --- | --- |
| `src/llm/ollama_client.py` | `OllamaClient.check_ready/chat`, `LLMResponse.json_object`, `OllamaError`, `summarize_calls` | Synchronous local JSON generation, actual decoding controls, no silent retry/repair, model identity, raw traces and token/error accounting |
| `src/llm/prompts.py` | RAIR role system prompts/schemas and common synthesizer prompt/schema | Decomposition, planning, filtering, extraction, verification and final policy definitions; runtime roles further constrain schemas to actual IDs |
| `src/kair/prompts.py` | Planning/update/check/filter prompt and schema constants | Role-neutral whole-question agent operations; used identically for competing agents |

### RAIR

| File | Main symbols | Purpose |
| --- | --- | --- |
| `src/rair/state.py` | `Gap`, `Evidence`, `VerifiedFact`, `QueryAttempt`, `RAIRState` | Shared gaps/dependencies, source-backed admitted knowledge, attempts, round state and validation/actionability helpers |
| `src/rair/decomposer.py` | `RAIRDecomposer.decompose/parse_payload`, `_validate_dependency_graph`, `DecompositionError` | Bounded ordered information gaps with valid dependencies; rejects malformed plans |
| `src/rair/query_planner.py` | `select_next_gap` (31), `RAIRQueryPlanner.plan`, `RepeatedQueryError` | Least-attempted actionable-gap scheduling, query creation/normalization and duplicate detection |
| `src/rair/retrieval_step.py` | `RetrievalStepResult`, `RAIRRetrievalStep.run` | Connects planner and BM25; checks budget before planning; records attempts, query origin, charged original-question fallback and rounds |
| `src/rair/evidence_filter.py` | `RAIREvidenceFilter.filter/parse_payload` | Runtime sentence-alias selection and strict reconstruction of available original source text/indices; legacy parser remains |
| `src/rair/fact_extractor.py` | `CandidateFact`, `RAIRFactExtractor.extract/parse_payload` | Cited candidate claims from supplied evidence; assigns IDs in code and rejects unavailable evidence |
| `src/rair/verifier.py` | `VerificationDecision.accepted`, `RAIRVerifier.verify/parse_response/commit_decisions/verify_and_commit` | Support/relevance/type/placeholder admission checks, keyed complete candidate decisions, separate resolution and safe fact promotion |
| `src/rair/synthesizer.py` | `SynthesisResult`, `RAIRSynthesizer.synthesize/synthesize_knowledge`, `parse_payload`, `resolve_sources` | Common final answer/abstention policy and original sentence citation resolution, reused by KAIR |
| `src/rair/controller.py` | `RAIRResult` (24), `RAIRController` (43), `policy`, `_invoke`, `run` | Full bounded role orchestration, stop/error handling, partial-state finalization and stage-tagged result traces |
| `src/rair/ablations.py` | `WholeQuestionGap`, `UncheckedAdmission`, `AblationResult`, `NoVerificationRAIRController`, `NoDecompositionRAIRController` | Declared component interventions; no gate means unchecked admitted facts despite legacy state field name; no decomposition means one whole-question gap |
| `src/rair/reference.py` | `ReferenceResult`, `ReferenceRAIRController` (21) | Hash-validates archived Step 4 code, runs it in a fresh interpreter and replaces only final synthesis with current common policy; transfers actual budgets/calls back |

### KAIR

| File | Main symbols | Purpose |
| --- | --- | --- |
| `src/kair/state.py` | `KAIRFact`, `KAIRState`, `complete` | Private known facts/requirements/query history/context; initialized nonempty knowledge required for completion |
| `src/kair/agent.py` | `merge_context`, `parse_evidence`, `context_payload`, `requirements`, `selected_ids`, `id_schema`, `evidence_schema`, `KAIRAgent.call/step` | Plan/retrieve/update/check/filter cycle, source constraints/merging, independent agent sampling and atomic private-state commit |
| `src/kair/controller.py` | `KAIRResult` (22), `select_candidate` (43), `KAIRController` (49) | Serial competitive iterations, rotated order, complete-agent early skip, fewest-requirements partial selection, winner-only context sharing, separate agent errors and common final synthesis |

### Evaluation

| File | Main symbols | Purpose |
| --- | --- | --- |
| `src/evaluation/budget.py` | `RunBudget`, `BudgetExhausted` | Charges actual retrieval/model attempts; reserves a final call and prevents generations after finalization |
| `src/evaluation/metrics.py` | `normalize_answer`, `exact_match`, `answer_f1`, `RetrievalMetrics`, `retrieval_metrics` | HotpotQA-style lexical answer scoring and set-based evidence/retrieval overlap; no independent semantic entailment scorer |
| `src/evaluation/paired.py` | `CONTROLLERS`, `ABLATIONS`, `METRICS`, `fingerprint`, `source_hashes`, `system_names`, `schedule`, `prepare_manifest`, `load_manifest_examples`, `score_result`, `audit_result`, `aggregate`, `render_report` | Common protocol: sample/exclude without gold-based filtering, freeze source/data/inputs, order arms, validate controls/calls, score after inference, retain all outcomes, aggregate and report |
| `src/evaluation/uncertainty.py` | `percentile`, `paired_bootstrap` | Deterministic percentile intervals over question clusters, keeping each question's seeds together; 95% default and 97.5% component-contrast mode |

### Experiment entry points

All commands run as `python -m src.experiments.<module>` from the project root. Diagnostic checks can create outputs or call the local model; read their CLI before reuse.

| File | Entry / purpose |
| --- | --- |
| `src/experiments/compare.py` | `main`, `run`, `read_journal`, `save_reports`, `identity`; frozen paired prepare/run/resume CLI; completed resume audits and rewrites derived reports without inference |
| `src/experiments/run_rair.py` | `main(argv, controller_type=..., system=...)`; standalone bounded subset writer with metadata, flushed per-question results and post-inference answer scores; `--config`, `--offset`, `--limit`, `--output` |
| `src/experiments/run_kair.py` | Wraps the shared diagnostic writer with `KAIRController`; standalone KAIR CLI |
| `src/experiments/prepare_ablations.py` | `prepare`; one-off component-study protocol preparation/exclusion helper |
| `src/experiments/check_setup.py` | Local environment/project configuration diagnostic |
| `src/experiments/check_llm.py` | Model connection/structured-response checks; `validate` and `main` |
| `src/experiments/check_dataset.py` | Dataset/source annotation auditing; `audit_support_references`, output writer and CLI |
| `src/experiments/check_bm25.py` | Diagnostic retrieval against gold support titles after retrieval; `evaluate_example` |
| `src/experiments/check_metrics.py` | Deterministic metric diagnostic |
| `src/experiments/check_rair_state.py` | Shared state/dependency/actionability example |
| `src/experiments/check_rair_decomposer.py` | Decomposer role diagnostic |
| `src/experiments/check_rair_query_planner.py` | Planner diagnostic with an existing author fact |
| `src/experiments/check_rair_retrieval_step.py` | Planner/BM25 integration diagnostic |
| `src/experiments/check_rair_evidence_filter.py` | Original-sentence selection diagnostic |
| `src/experiments/check_rair_fact_extractor.py` | Candidate/evidence-reference diagnostic |
| `src/experiments/check_rair_verifier.py` | Candidate decisions and shared admission diagnostic |
| `src/experiments/check_rair_synthesizer.py` | Cited answer/abstention diagnostic |
| `src/experiments/check_rair_pipeline.py` | `make_task` supplies complete/missing fictional book-author-city cases; end-to-end RAIR check |
| `src/experiments/check_kair_pipeline.py` | End-to-end competitive baseline check using the illustrative cases |

`src/__init__.py` and `__init__.py` in `datasets`, `retrieval`, `llm`, `rair`, `kair`, `evaluation`, `experiments`, plus `dashboard/__init__.py`, are package markers rather than separate engine entry points.

## 4. Dashboard files

| File | Important symbols / purpose |
| --- | --- |
| `dashboard/server.py` | `custom_task` (35), `Dashboard` (58), `make_server` (264), `main` (424); validates examples/custom inputs, admits one live job, runs real controllers in a worker, checkpoints exposure/results, withholds gold until both results, exposes snapshots/progress/results/downloads and fixed archive routes |
| `dashboard/research.py` | `diagnostics`, `ResearchArchive._ensure/describe/list_cases/case`; validates/indexes historical Step 5 rows by offsets, pairs outcomes, filters/paginates cases, returns original source pools/gold supports and hash-bound manual notes |
| `dashboard/ablations.py` | `AblationStudy.describe/case`; verifies Step 9's four-arm journal/summary and caches by signature; `ConfirmationStudy` fixes Step 10 filenames and R/K arm set, reusing the reader |
| `dashboard/static/index.html` | Five screen structure, controls/source editor, engine panels, historical benchmark and separately labeled Step 9/10 sections |
| `dashboard/static/styles.css` | Teal/purple visual system, cards, tables/charts/timelines, focus/reduced-motion and responsive layout |
| `dashboard/static/app.js` | Live state/input editing, readiness, submission, `poll`, stage replay, one-time result retrieval, source links, downloads, legacy fallback and deferred raw formatting |
| `dashboard/static/research.js` | `renderDetailedTrace`, `researchView`, `researchChart`, historical benchmark/failure rendering, case filtering/inspection; `loadAblations`; `loadConfirmation/loadConfirmationCase` for actual final data and inline recorded traces |

Main service routes and safety/retention limits are documented in the handoff. The new Step 10 backend reader was verified with real completed data in this inspection; its current full browser acceptance remains pending.

## 5. Tests

Fresh discovery runs **242 tests**. Most use scripted model transport so they exercise actual code paths without real model generation. Individual historical role check JSONs are not substitutes for these tests.

| File | Coverage |
| --- | --- |
| `tests/test_dataset.py` | Original text/index preservation, input/gold isolation, duplicate/question ownership, BOM handling and invalid gold reference auditing |
| `tests/test_bm25.py` | Tokenization, relevance/top-k, positive matches, score order and stable ties |
| `tests/test_metrics.py` | Normalization, EM, multiset token F1, yes/no special cases, empties and retrieval overlap |
| `tests/test_rair_state.py` | Dependencies, fact/source validity, attempts, duplicate queries, round limits and serialization |
| `tests/test_rair_decomposer.py` | Gap IDs, priorities, dependencies, cycles/order, bounded/strict payload shape |
| `tests/test_rair_query_planner.py` | Actionability/priorities, new/valid query shape, duplicate/length rejection |
| `tests/test_rair_retrieval_step.py` | Budget check before planning, query recording, matching/no-match retrieval, rounds and ownership |
| `tests/test_rair_evidence_filter.py` | Exact sentence reconstruction and rejection of invalid/unavailable/duplicate source selections |
| `tests/test_rair_fact_extractor.py` | Candidate IDs/statements/evidence membership, strict schema and empty outputs |
| `tests/test_rair_verifier.py` | Admission guards, full candidate decisions, safe promotion, acceptance versus resolution and rejected claims |
| `tests/test_rair_synthesizer.py` | Valid cited answer versus consistent abstention, unknown/duplicate citations and strict fields |
| `tests/test_rair_controller.py` | Full role orchestration, partial knowledge/stops/errors, source citations, fresh state, CLI checkpointing/gold mutation and truncated/invalid model output accounting |
| `tests/test_kair.py` | Private-state isolation, first completion, rotation/ties, winner-only sharing, source bounds/merging, atomic commits, failed/stalled agents, requirements checking, seeds, common final IDs and diagnostic CLI |
| `tests/test_evaluation_pipeline.py` | Shared/reserved budgets, blocked versus attempted calls, protocol/source/data controls, scoring all paid retrievals, gold mutation, failed-arm retention, interruption and completed resume |
| `tests/test_step4_benchmark.py` | Prefix/explicit exclusions, reproducible sampling, protocol integrity and paired question-cluster bootstrap behavior |
| `tests/test_step5_improvements.py` | Alias/ID contracts, rejected-resolution handling, partial facts, fair gap attempts, final schemas, corrected native ceiling and reference subprocess/hash/budget transfer |
| `tests/test_dashboard.py` | Live service with actual controllers/scripted transport; same inputs/policy, order, deferred gold, errors, one job, validation, retention, HTTP assets/Host/Origin/body/download contracts |
| `tests/test_research_dashboard.py` | Historical archive integrity, groups/flags, filters/pagination, source pools, offsets, hash-bound notes, API validation and no live-model side effects |
| `tests/test_live_progress.py` | Observer neutrality/failure isolation, detached event replay, visible early stages, small responses, cursor/result/download and origin contracts |
| `tests/test_ablations.py` | Exact declared removals, no fabricated verifier decisions, preserved provenance/final call, whole-question gap, four-arm schedule and adjusted interval labeling |
| `tests/test_ablation_dashboard.py` | Four-arm summary/contrast integrity, tamper rejection, separate two-arm confirmation, real reader contracts, query validation and 200/400/403/404/503 HTTP behaviors |
| `tests/live_progress_client.cjs` | Browser-client polling regression harness: incremental replay, metadata/result retrieval, stale responses, older-server fallback and error recovery |

Tests are discovered with `-s tests`; there is no need to turn this directory into a new package or replace the existing discovery workflow.

## 6. Configuration files

| File | Purpose |
| --- | --- |
| `config/settings.yaml` | Live/diagnostic defaults and common pilot controls; Qwen tag, local URL, context/output caps, temperatures, BM25 top-k, RAIR rounds, KAIR count/iterations/steps and paths. Its evaluation sample is **4**, not the final 100 |
| `config/step3_pilot.json` | Frozen 4-question/two-seed common integration protocol |
| `config/step4_benchmark.yaml` | Historical 100-question benchmark settings |
| `config/step4_benchmark.json` | Frozen Step 4 questions, source/data fingerprints, settings and 400-arm schedule |
| `config/step4_exclusions.json` | Provenance for prior local exposure exclusions used by Step 4 |
| `config/step5_development_selection.json` | Selected exposed development cases and reasons, not a random generalization test |
| `config/step5_development.yaml` | Settings for the deliberately selected repair-development cohort |
| `config/step5_development.json` | Frozen development experiment manifest |
| `config/step5_benchmark.yaml` | Fresh three-arm repair evaluation settings, including reference configuration |
| `config/step5_benchmark.json` | Frozen 100-question/600-arm Step 5 study and controls |
| `config/step5_exclusions.json` | Prior exposed/scheduled ID provenance for Step 5 |
| `config/step5_reference.json` | Archived old-core source inventory/hash, archive digest and reference layout settings |
| `config/step9_ablation_settings.json` | Four-arm component experiment settings, endpoints, budgets and bootstrap controls |
| `config/step9_ablations.json` | Frozen 20-question/two-seed/160-arm component study |
| `config/step9_exclusions.json` | Records the 225 prior IDs excluded before Step 9 |
| `config/step10_settings.json` | Final confirmation settings: sample 100, selection seed 20261031, seeds 42/43, 4/18 ceilings, 10000 resamples, bootstrap seed 20261101 |
| `config/step10_benchmark.json` | Frozen current confirmation: exact questions/schedule/settings/source/data hashes; 400 arms |
| `config/step10_exclusions.json` | Provenance of 245 excluded prior locally exposed/scheduled dataset IDs |

Do not regenerate or edit a completed experiment's manifest to admit changed code. `source_hashes()` covers all `src/*.py` and `requirements.txt`; it does not cover the full dashboard or this handoff. The JSON settings files are readable through YAML-safe configuration loading, while manifests are read as JSON by the runner.

## 7. Data

| File | Purpose / boundary |
| --- | --- |
| `data/raw/hotpot_dev_distractor_v1.json` | Supplied full HotpotQA development distractor data, 46,320,117 bytes; original question pools, answers and support annotations. Gold is not a controller argument |
| `data/processed/hotpot_dev_smoke_inputs.json` | Preserved smoke input material from dataset setup |
| `data/processed/step5_development.json` | Already exposed development examples used by diagnostics/dashboard catalog |
| `data/processed/step8_failure_notes.json` | Post hoc historical failure annotations, accepted only when bound to the matching Step 5 journal hash |

Raw and processed data are ignored by `.gitignore`. The next reviewer needs the actual data/evidence files, not just Python source, for reproducible audits and historical case browsing.

## 8. Documentation and visual assets

| File | Purpose / currentness |
| --- | --- |
| `docs/RAIR.md` | Full current RAIR workflow, stops, trace schema and corrected native ceiling |
| `docs/KAIR.md` | Competitive baseline's journal/preprint mapping, local deviations and historical Step 2 diagnostics; some old native RAIR ceiling/future-evaluation prose is stale |
| `docs/EVALUATION.md` | Original common pilot protocol, gold isolation, budgets, scoring/resume and historical test evidence; use current code for corrected standalone ceilings |
| `docs/BENCHMARK.md` | Step 4 selection, controls, results and limitations |
| `docs/RAIR_IMPROVEMENTS.md` | Step 5 observed failures, concrete repairs, same-question reference-control design, fresh results, replay/cost-ceiling correction and reproduction |
| `docs/DASHBOARD.md` | Initial working dashboard, launch/use instructions and historical Step 6 checks |
| `docs/PRESENTATION.md` | Historical Step 7 delivery/verification and Step 9 update pointers; not proof of final Step 10 delivery |
| `docs/PROJECT_REVIEW.md` | October maintenance fixes, discarded prompt alternatives, residual answer-quality failures and future work |
| `docs/RESEARCH_DASHBOARD.md` | Five-view Step 8 UI, detailed timelines, archive metrics/failure inspection and validation |
| `docs/LIVE_UPDATES.md` | Lightweight events/polling, old-server fallback, observer neutrality, regression/manual checks; contains superseded requests for user-run test output |
| `docs/ABLATIONS.md` | Step 9 intervention definitions, prespecified adjusted inference, results and limits |
| `docs/assets/project_output_concept_v1.png` | Earlier approved target dashboard concept; not actual measured results |
| `docs/assets/project_output_concept_prompt.txt` | Prompt/provenance for that concept image |
| `docs/assets/dashboard_step6_desktop.png` | Historical desktop dashboard screenshot |
| `docs/assets/dashboard_step6_mobile.png` | Historical narrow layout screenshot |
| `docs/assets/dashboard_step7_missing.png` | Historical missing-evidence rehearsal screenshot |
| `docs/assets/dashboard_step8_benchmark.png` | Historical five-view research benchmark screenshot |

No `docs/STEP10.md` final release guide exists yet. The pending package script intends to create/update documentation; it has not executed those steps.

## 9. Frozen experiments and important result records

### Paired study files

Each listed study has three separate files: the raw `.jsonl` journal, derived `.summary.json` and derived `.md` report. The journal/manifests are primary provenance; a prose report alone does not prove execution or version identity.

| Stem under `results/` | Purpose |
| --- | --- |
| `step3_paired_pilot` | Completed 16-arm integration pilot, four questions/two seeds |
| `step4_untouched_benchmark` | Completed historical 400-arm comparison of earlier engines |
| `step5_development` | Deliberately selected, exposed repair-development comparison; not untouched performance evidence |
| `step5_fresh_benchmark` | Completed 600-arm fresh comparison with old-core/current-final-policy control |
| `step9_ablations` | Completed 160-arm exploratory four-arm study |
| `step10_benchmark` | Completed current 400-arm confirmation, freshly audited during handoff |

For example, `results/step10_benchmark.jsonl`, `results/step10_benchmark.summary.json` and `results/step10_benchmark.md` all exist. **`results/step10_analysis.json` and `step10_verification.json` do not yet exist.** Fresh handoff audit facts are recorded in `PROJECT_HANDOFF.md`, not in a fabricated Step 10 release receipt.

### Validation, replay, exposure and archive records

| File or family | Purpose |
| --- | --- |
| `results/phase2_llm_check.json` | Historical local inference/structured response diagnostic |
| `results/phase3_dataset_check.json` | Historical dataset audit |
| `results/phase4_bm25_check.json` | Historical retrieval diagnostic |
| `results/phase5_metrics_check.json` | Historical metric check |
| `results/phase6_rair_state_check.json` | Shared-state diagnostic |
| `results/phase7a_decomposer_check.json` through `phase7g_synthesizer_check.json` | Separate decomposer/planner/retrieval/filter/extractor/verifier/synthesizer role outputs; diagnostic evidence, not a paired benchmark |
| `results/phase8_rair_pipeline_*.json` | Dated full RAIR pipeline attempts, including superseded/failed trials |
| `results/rair_*.jsonl`, `results/kair_*.jsonl` | Dated standalone dataset diagnostics with their own policies; not interchangeable with common-budget studies |
| `results/step2_kair_pipeline_*.json` | Dated competitive baseline synthetic pipeline attempts/smokes |
| `results/step4_validation.json` | Historical Step 4 control/score audit |
| `results/step4_source_snapshot.zip` | Frozen old-core source used for historical/reference reproduction |
| `results/step5_audit.py` | Historical repair-study audit helper; inspect its version assumptions before rerunning |
| `results/step5_replay.py` | Stored-response replay checker for the repair/call-estimate boundary |
| `results/step5_validation.json` | Measured-run Step 5 audit |
| `results/step5_current_verification.json` | Later Step 5 current-source/replay verification |
| `results/step5_final_tests.json` | Historical final source regression evidence |
| `results/step5_development_comparison.json` | Summary of deliberately selected development comparisons |
| `results/step5_kair_smoke.json`, `step5_reference_smoke.json` | Baseline/control diagnostic traces |
| `results/step5_source_snapshot.zip`, `step5_final_source_snapshot.zip` | Preserved measured/final repair-source packages; version boundary matters |
| `results/step5_snapshot_check.json`, `step5_final_archive_check.json`, `step5_final_source_snapshot.zip`, `step5_final_tests.json` | Snapshot/restoration checks and final archived source/test evidence |
| `results/step6_audit.py` | Historical live dashboard release audit |
| `results/step6_archive_check.json`, `step6_browser_checks.json`, `step6_tests.json`, `step6_validation.json` | Initial live/HTTP/browser/tests/archive verification |
| `results/step6_dashboard_source.zip` | Initial dashboard source release snapshot |
| `results/step6_downloaded_run.json` | Retained downloaded real run used to verify download functionality |
| `results/step7_verification.json` | Historical report/slides/rehearsal/native Office/ZIP verification; not current Step 10 evidence |
| `results/step8_before.json` | Pre-change frozen evidence/source hash inventory |
| `results/step8_previous_dashboard.zip` | Preserved previous UI source |
| `results/step8_verify.py`, `step8_test_output.txt`, `step8_browser_checks.json`, `step8_validation.json` | Five-view UI checks; source-hash assertions deliberately belong to that older revision |
| `results/step9_source.zip` | Frozen component-study core source |
| `results/step9_analysis.json` | Component-study stops/errors, groups and deterministic illustrative pairs |
| `results/step9_verification.json` | Dated 160-run, 239-test, browser and 15-slide structural release receipt; its Step 10-not-run limit is historical |
| `results/step9_preflight_tests.txt`, `step9_tests.txt`, `step9_audit_output.txt`, `step9_run_output.txt` | Component study's original test/audit/execution output |
| `results/step10_source.zip` | Frozen confirmation core source and manifest; CRC/member source hashes freshly checked |
| `results/step10_exposure_audit.json` | Saved normalized prior-question-text audit; no exact normalized matches recorded; not a semantic/pretraining leakage proof |
| `results/step10_test_checks.json` | Latest saved 242-test/JS status and preserved transient Windows abort/recheck explanation |
| `results/step10_tests.txt` | Initial suite log with one Windows HTTP connection abort |
| `results/step10_http_recheck.txt` | Passing isolated HTTP suite recheck |
| `results/step10_tests_final.txt` | Passing saved final 242-test suite from the Step 10 development session |
| `results/step10_run_output.txt` | Initial worker output before interruption after the first saved arm |
| `results/step10_resume_output.txt` | Persistent resumed worker output; ends with saved journal/report confirmation for all 400 arms |
| `results/step10_resume_error.txt` | Worker stderr, empty at inspection |
| `results/step10_ollama_stdout.log`, `step10_ollama_stderr.log` | Local model-service execution logs, not primary score summaries |
| `results/step1_ollama_stdout.log`, `step1_ollama_stderr.log` | Large historical service logs; not benchmark datasets |
| `results/step9_dashboard_*.log`, `step10_dashboard_*.log`, `step10_dashboard_final_*.log` | Dashboard process logs; existence does not prove current server liveness |

### Saved live jobs

`results/dashboard_<run_id>.jsonl` records accepted exposure before inference, followed by environment, each real engine result, identity verification and completion/error. There are multiple historical jobs, not one replaceable cache file. The Step 9 verified complete/missing examples are:

- `results/dashboard_03cd16c374224515ab41a9daf71358e0.jsonl` — both engines answered the complete fictional chain.
- `results/dashboard_e501ef918f6146fda583a92d63e09c46.jsonl` — both abstained on missing birthplace evidence.

Other dated dashboard journals support Steps 6–8 and maintenance diagnostics. Preserve their individual source/settings metadata and exposure contribution; do not relabel them as final untouched benchmark questions.

### October maintenance work

| Location | Purpose |
| --- | --- |
| `results/check_post_presentation_fixes.py` | Focused maintenance diagnostic driver |
| `results/check_post_presentation_pairs.py` | Matched end-to-end diagnostic driver |
| `results/verify_post_presentation_fixes.py` | Maintenance verification helper |
| `results/post_presentation_20261030/before_roles.json` | Before-fix role probes |
| `.../wire_probe.json` | Structured source-schema/transport probe |
| `.../prompt_trial_roles.json`, `.../prompt_trial_pairs.json` | Discarded prompt trial evidence; not successful production fixes |
| `.../changes.patch` | Saved retained maintenance patch, not a Git commit history |
| `.../previous_source.zip`, `.../final_source.zip` | Before/retained source snapshots |
| `.../kair_smoke.json`, `.../final_pairs.json` | Final baseline smoke and four matched diagnostic pairs |
| `.../tests.json`, `.../verification.json` | Historical 210-test/source/result verification |
| `.../dashboard_<id>.jsonl` | Preserved individual trial/final live execution records |

The `.../` rows immediately above mean the exact `results/post_presentation_20261030/` prefix, not the repository root.

## 10. Preserved source copies and authoring workspaces

### Archived source trees

| Directory | Purpose |
| --- | --- |
| `results/step5_reference/` | Archived Step 4 code, requirements, tests/config and `REPRODUCE.txt` for the isolated old-core control; its `src/` is not the active top-level source |
| `results/step5_snapshot_validation/` | Historical extracted measured snapshot used for independent tests; includes copied code/reference layout |
| `results/step5_final_snapshot_validation/` | Historical extracted final snapshot validation tree; includes copied source, tests and nested reference code |

Do not edit these copies to “fix” current application behavior or flatten their functions into the active source map. Reference integrity depends on exact file inventories and hashes.

### Historical Step 7 builders

| File under `results/step7_build/` | Purpose |
| --- | --- |
| `analyze.py`, `failure_analysis.json`, `outcome_census.csv` | Historical post hoc outcome and failure analysis |
| `build_documents.py`, `viva_content.json` | Historical report, demo and viva authoring |
| `build_slides.mjs` | Historical 12-slide editable deck authoring |
| `export_native.ps1`, `check_powerpoint.ps1` | Environment-specific Office export/application-check utilities; not core application entry points |
| `render_documents.py`, `document_render_checks.json` | Packaged DOCX rasterizer adaptation and recorded page checks |
| `verify_live.py`, `live_verification.json`, `verification_core.json`, `finish_release.py` | Rehearsal/evidence/packaging helpers and receipts |
| `powerpoint_application_check.json`, `chart_edit_test*.pptx` | Historical native chart edit/resize/save/reopen proof copies |
| `*.validation.json`, `slide_text.json`, `slides_render/`, `powerpoint_render/`, document-named render folders | Historical package/font/layout/text and visual QA artifacts |
| `candidate.pptx`, `superseded_presentation.*` | Intermediate/superseded artifacts, not final outputs |

### Historical Step 9 builders

| File under `results/step9_build/` | Purpose |
| --- | --- |
| `analyze.py`, `case_traces.json` | Component-study analysis and selected raw cases |
| `update_slides.mjs` | Imports historical deck and appends three component-study slides |
| `restore_chart.py` | Restores original chart/workbook parts lost during import/export, preserving actual original values/lineage; historical repair helper |
| `inspect_slides.mjs`, `slide_text.json`, `slides_build.log` | Text/render/build inspection |
| `verify_release.py`, `presentation.validation.json` | Historical release verification and structural/font/chart receipt |
| `candidate*.pptx`, `slides_render/`, `reference-11.png`, `reference-12.png`, montage | Intermediate exports and visual QA references |

### Current pending Step 10 builders

These source files exist. They have not produced a final release. Read their preconditions before running them; several missing input receipts must be generated through real review, not set to true merely to bypass assertions.

| File under `results/step10_build/` | Actual purpose and current condition |
| --- | --- |
| `prepare.py` | **Already used** one-off freeze: preserve main Step 9 source, gather exclusions, create settings/manifest/source ZIP. Refuses existing outputs; do not rerun to overwrite the cohort |
| `check_exposure.py` | Checks exact normalized question texts in earlier JSONL first records against the new cohort; its audit output exists |
| `analyze.py` | Pending full audit/post hoc analysis, outcomes/census/reference answers and deterministic case traces; writes absent `step10_analysis.json`, `step10_verification.json` and `deliverables/step10/` outputs. Completed-run resume inside it rewrites derived reports but should perform no inference |
| `inspect_cases.py` | Compact read-only display of pending `case_traces.json`, original gold support sentences, explicit states/decisions; currently lacks its generated input |
| `build_documents.py` | Draft consolidated report, demo script and 30 viva answers from actual completed statistics; needs absent analysis/verification files. Hardcoded authoring date/runtime assumptions need review |
| `build_slides.mjs` | Draft new 14-slide editable presentation with actual confirmation data and two manually reviewed cases; needs absent `reviewed_cases.json` and finalization/render validation |
| `render_documents.py` | Canonical DOCX page rasterizer using PDFs exported through native Word; asserts PDF freshness; no final Step 10 DOCX/PDFs currently available |
| `package.py` | Draft ZIP/checksum/CSV/chart/PDF/source/release validation pipeline. Requires browser/visual receipts and actual artifacts. Also intends to update README, presentation docs and current package pointers; not executed in this handoff-only task |
| `node_modules` | Junction to user-specific bundled Node packages, not checked-in project dependencies or a portable installation |

Absent expected inputs/receipts include `results/step10_analysis.json`, `step10_verification.json`, `step10_browser_checks.json`, and `results/step10_build/{case_traces.json,reviewed_cases.json,visual_review.json,presentation.validation.json}`. See P0 tasks in the handoff for the required order and acceptance checks.

## 11. Delivered historical files

| File | Purpose / boundary |
| --- | --- |
| `deliverables/RAIR_KAIR_Teacher_Package.zip` | Historical Step 7 teacher bundle; not the final confirmation package |
| `deliverables/Step9_Research_Update.zip` | Historical component-study update with its own evidence |
| `deliverables/step7/RAIR_KAIR_Final_Report.docx` and `.pdf` | Historical editable report and reading copy |
| `deliverables/step7/RAIR_KAIR_Presentation_Final.pptx` and `.pdf` | Historical 12-slide deck/PDF |
| `deliverables/step7/RAIR_KAIR_Demo_Script.docx` and `.pdf` | Historical three-page demo notes |
| `deliverables/step7/RAIR_KAIR_Viva_Questions.docx` and `.pdf` | Historical 30-question viva preparation |
| `deliverables/step7/Benchmark_Outcome_Census.csv` | Historical Step 5 run-level census |
| `deliverables/step7/Remaining_Failure_Review.md` | Historical reviewed failures, not final Step 10 failure taxonomy |
| `deliverables/step7/START_HERE.md`, `Verification.json` | Historical release instructions/receipt |
| `deliverables/step9/RAIR_KAIR_Presentation_Step9.pptx` | Fifteen slides: preserves original twelve historical slides and adds three exploratory slides |
| `deliverables/step9/Step9_Findings.md` | Four-arm measured findings and uncertainty |
| `deliverables/step9/Step9_Failure_Review.md` | Post hoc trace cases, including harmful over-rejection and useful verification examples |
| `deliverables/step9/Step9_Outcome_Census.csv` | All 160 component-study outcomes |
| `deliverables/step9/Step9_Dashboard.png` | Historical real UI screenshot |
| `deliverables/step9/START_HERE.md` | Component-study update instructions |

The word “Final” in an old filename is not evidence that it includes the latest experiment. New review/presentation work should preserve those historical artifacts and clearly distinguish the next consolidated release.

## 12. Review and transfer boundaries

The active application is top-level `src/` plus `dashboard/`; `tests/` verifies it; `config/` freezes specific studies. Frozen data/results/source archives are essential evidence. Build/render workspaces and old copied source trees are supporting provenance, not alternate live engines unless a reference controller explicitly loads them.

No existing application source or configuration was changed for this map/handoff. The Git status command fails because no repository exists; there is no meaningful Git modified/untracked list to report. Use the hashes, manifests, raw journals, saved verification records and fresh handoff checks described in `PROJECT_HANDOFF.md` until real version control and artifact storage are established.
