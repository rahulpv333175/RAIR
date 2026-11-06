# Step 8: research dashboard

The dashboard implements the five presentation views in the original master
prompt. It reuses the local Python server, existing RAIR/KAIR controllers and
teal/purple interface. It adds no dependencies. Streamlit was a preference in
the original aim; this implementation retains the existing working web app.

## Start locally

Run `start_dashboard.cmd` from the project root, then open
http://127.0.0.1:8765/. Stop the server with Ctrl+C. Ollama and the configured
model are needed only for live inference. Archived research browsing works
without model inference. No cloud service, model download or publication is added.

## What an examiner can inspect

| View | Content |
| --- | --- |
| Research objective | Two-hop example, comparison question and scope of conclusions |
| Architectures | Specialized RAIR roles and shared state versus competing KAIR agents with private knowledge and selected shared context |
| Live execution | Same editable question/source pool and resource ceilings; active operation counters; detailed completed traces for each engine |
| Benchmark | Frozen protocol/model digest, all answer/retrieval/support metrics, coverage, abstentions, errors, calls, tokens, time and eight comparison charts |
| Findings and failures | All 200 question–seed pairs in four exact-match groups, search, seed/diagnostic filters, pagination, original source pools and paired timelines |

RAIR timelines show gaps/dependencies, selected gap, queries, BM25 titles/scores,
selected sentences, candidate facts, individual verifier booleans/reasons,
admitted facts, accumulated knowledge, feedback, unresolved gaps and citations.
KAIR timelines show competition order, incoming context, each agent's queries,
retrieval, candidates, binary admission decisions, private knowledge/requirements,
refined context, eligible proposal counts, selected agent and propagated context.
The KAIR binary checker does not record per-candidate reasons; none are invented.
Failed attempts retain their partial trace and error. These are explicit program
states and model outputs, not hidden chain-of-thought. Full JSON remains available.

## Preserved research evidence

The read-only archive streams the 39 MB Step 5 journal to build a compact byte
offset index. It checks the manifest fingerprint, planned result schedule,
verification/environment records, closing summary and per-arm metric means.
Selected original source pools must match their frozen task fingerprints.
Subsequent file changes invalidate the index until restart. A page of 20 pairs
is about 36 KB; the largest full pair is about 332 KB. The browser does not
download the entire journal to display the case list.

There are 100 questions, two seeds, 200 paired RAIR/KAIR outcomes and 600 runs
including the earlier RAIR core control. Group counts are 54 both correct,
27 only RAIR correct, 18 only KAIR correct and 101 both failing exact match.
All planned runs, including abstentions and errors, remain in the denominator.
Twelve prior purposeful manual reviews are bound to the exact journal hash.
They illustrate mechanisms and are not estimates of population frequencies.
Diagnostic flags overlap and are not automatic causal explanations.

Frozen EM is 40.5% RAIR versus 36.0% KAIR. RAIR minus KAIR is +4.5 percentage
points, with paired question-cluster 95% interval −3.0 to +12.0 points: superiority
is not established. The +22-point improvement versus the earlier RAIR core
has interval +15.0 to +29.5 points and measures a bundled core change under a
common final-answer policy. Current live engines include later maintenance;
the dashboard does not assign the historical scores to them. Support-reference
scores do not establish entailment or prove reduced hallucinations.

## A 5–7 minute demonstration

1. **0:00–0:45:** Objective — connect book → author → birth city.
2. **0:45–1:45:** Architectures — explain private full-question competition,
   then specialized roles, admission gate and shared knowledge.
3. **1:45–3:15:** Live execution — run the complete illustrative example;
   open a retrieval round, a verifier decision and both cited source sentences.
   Show the missing-evidence example if time permits.
4. **3:15–4:30:** Benchmark — compare EM/F1, retrieval/support scores and
   actual calls/tokens/time; explain the inconclusive RAIR-versus-KAIR interval.
5. **4:30–6:30:** Findings — inspect a RAIR-only and KAIR-only pair, then a
   reviewed bridge rejection or span mismatch. Show the original evidence.
6. **6:30–7:00:** State limitations and the next research experiment.

## Verification

- Full Python suite: **223 tests passed**, including archive integrity,
  filtering/pagination, unsafe query rejection, source-pool consistency,
  same-origin protection, inference isolation and attachment headers.
- Both JavaScript files pass Node syntax checks.
- All 600 recorded results validated; all 200 paired cases loaded on demand.
- Engine source, dependency list, raw dataset, benchmark configuration, journal
  and summary match the hashes saved before Step 8.
- Browser checks cover all five views, four outcome filters, search with no
  matches, seed/diagnostic filters, pagination, admission timelines, historical
  execution errors and preservation of live inputs while browsing.
- Four real engine runs through the UI: both return **Nerava** with both
  source titles for complete evidence; both abstain for missing birthplace
  evidence. These are exposed diagnostic examples, not new benchmark questions.
- Desktop 1440×1000 and narrow 390×844 checks show no page-width overflow;
  wide tables scroll within their regions. Viewport override was reset.
- No browser warning/error logs observed. Native buttons/selects/details and
  accessible table captions are used; no full assistive-technology audit.

Evidence: `results/step8_validation.json`, `results/step8_test_output.txt`,
`results/step8_verify.py` and `docs/assets/dashboard_step8_benchmark.png`.
The local QA server is stopped after verification; restart with the launcher.

## Limits and next step

The JSON endpoint and attachment headers are tested. The in-app browser's
download-capture capability timed out, so saving the attachment through that
browser is not verified. The underlying paired records remain accessible by
the read-only API and in the frozen journal.

Step 8 completes the requested dashboard scope. Component ablations and a
fresh untouched comparison of the maintained engines have not been run.
Those are the next research work, requiring a frozen protocol before execution.
The Step 7 teacher package remains historical and should be updated after the
research scope and any new experiments are agreed. No next step is started here.
