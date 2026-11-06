# Step 5: RAIR validation and abstention improvements

This step develops changes using previously exposed questions, then tests the
frozen implementations on a separate question cohort. Step 6 requires the
user's next instruction.

## Problems established by Step 4

RAIR produced 24 question-level errors in 200 runs: 11 in verification, 10
in evidence filtering, two in extraction and one in final synthesis. Its 99
abstentions included 73 repeated-query stops. These are development findings,
not independent evidence for the changes below.

The old model-generated document IDs, candidate IDs and citation IDs allowed
invalid identifiers. Array-shaped verification also allowed missing decisions.
Repeated queries could stop the entire controller even when another independent
gap remained. Role instructions sometimes rejected useful, directly supported
partial facts or treated unnecessary unresolved planning gaps as a final veto.

## Changes

- Evidence selection uses short sentence aliases constrained to the actual
  retrieved sentences. Software reconstructs original document IDs, sentence
  indices and verbatim evidence. Unknown aliases still fail validation.
- Candidate IDs are assigned by software. Extraction can cite only the
  supplied evidence IDs. Verification requires exactly the supplied candidate
  keys, with one decision per candidate.
- A rejected candidate can never resolve a gap. If the model nevertheless marks
  it resolving, that flag becomes false; the other decisions remain usable.
  This never changes a failed acceptance guard to a pass.
- Supported bridge or answer facts may enter memory even if they do not
  completely answer the current gap. The evidence, relevance, value-type and
  unresolved-placeholder guards remain. Resolution still requires the specific
  requested information.
- Decomposition asks for the minimum necessary information. Scheduling tries
  less-attempted actionable gaps first. A duplicate query can use the original
  question once as a deterministic fallback. The fallback costs a retrieval;
  no additional model call is hidden. A stalled gap does not stop another
  actionable gap. All calls remain inside the common limits.
- All systems use the same updated final-answer policy. Its runtime schema
  permits either a consistent abstention or an answer citing available fact
  IDs. With no facts, only abstention is permitted. Unresolved planning hints
  cannot veto a complete supported answer; missing factual links still require
  abstention.

The public strict parsers and their legacy payload fixtures remain available;
the live roles adapt the more constrained wire representations into those
parsers. KAIR's agent, competition and memory code is unchanged.

## Evaluation design

Development uses 12 previously exposed Step 4 questions: four validation
failures, six repeated-query abstentions and two correct-answer controls.
Both systems receive these same questions. This deliberately selected diagnostic
set is not a benchmark of general accuracy.

The fresh benchmark prospectively excludes all 125 previously exposed dataset
IDs. Selection never consults gold answers or supporting-fact labels. It uses
100 new questions, seeds 42 and 43, and three arms: updated RAIR, KAIR and the
archived Step 4 RAIR core. Each arm receives only the same question and supplied
document pool. Gold is used only after inference for scoring.

The old-core control runs in an isolated Python process from the hash-verified
Step 4 source archive. Only its final synthesizer is replaced with the shared
current policy. Thus the primary contrast measures the RAIR core changes,
conditional on the shared final policy. It does not isolate each individual
change or measure the effect of the final-policy change alone.

All arms use qwen3.5:4b, local per-question BM25, top three documents, 4096
context tokens, 512 output tokens, matched non-final temperature 0.7, final
temperature zero, and caps of four retrievals and 18 model calls including a
reserved final call. KAIR keeps its independent agent seed offsets. Three-arm
execution order rotates across questions and reverses for the second seed.

The primary endpoint is updated RAIR minus reference RAIR exact match. Answer
F1 and the RAIR/KAIR comparison are secondary. Confidence intervals use 10,000
paired question-cluster bootstrap resamples, keeping both seeds together.
All errors and abstentions remain in the accuracy denominator. Coverage is
reported alongside correctness and actual token use.

## Fresh results

All **600 planned runs completed**, with 200 per arm on 100 questions
(79 bridge, 21 comparison). The model digest was
`2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`,
Ollama version `0.40.6`. Model identity matched before and after the run.

| System | Exact match | Answer F1 | Coverage | Abstentions | Question errors |
| --- | --- | --- | --- | --- | --- |
| Updated RAIR | **40.5% (81/200)** | **47.1%** | **69.5%** | **61** | **0** |
| Step 4 RAIR core, shared current final policy | 18.5% (37/200) | 21.9% | 32.5% | 111 | 24 |
| KAIR, shared current final policy | 36.0% (72/200) | 45.5% | 73.5% | 50 | 3 |

The primary updated-RAIR-minus-reference exact-match gain is **22.0 percentage
points**, with a **95% paired question-cluster interval of 15.0–29.5 points**.
The secondary F1 gain is 25.2 points, interval 18.2–32.7. Updated RAIR alone
was exactly correct in 47 seed-specific comparisons, the control alone in three,
with 150 ties. These are 200 comparisons but only 100 question clusters.

This supports a substantial improvement over the previous RAIR core within
this protocol. It does not establish that RAIR beats KAIR: updated RAIR minus
KAIR exact match is **+4.5 points**, interval **−3.0 to +12.0**. The F1 difference
is also inconclusive. Do not substitute the earlier Step 4 cohort's scores for
the same-question reference control when estimating the repair's effect.

All 24 reference errors were in the targeted stages: 11 verification, ten
filtering and three extraction. Updated RAIR had no question errors or truncated
generations. KAIR's three question errors were `NoValidProposal` competitions;
its 25 isolated agent errors and three truncated generations are retained
separately and may overlap those question outcomes. Final synthesis had no
question-level failures in any arm.

Repeated-query stops fell from 85 to 18. Total abstentions fell from 111 to 61;
these are different measures because a stopped search can still synthesize an
answer. RAIR's 61 common-budget stops are also retained, whether the final
prediction answered or abstained.

| Mean cost per planned run | Updated RAIR | Reference RAIR | KAIR |
| --- | --- | --- | --- |
| Model calls | 12.265 | 10.635 | 9.570 |
| Retrievals | 2.685 | 2.225 | 2.130 |
| Prompt tokens | 8956.67 | 7187.245 | 10564.15 |
| Output tokens | 700.05 | 774.71 | 800.22 |
| Total recorded tokens | 9656.72 | 7961.955 | 11364.37 |
| Serial controller seconds | 14.90 | 15.17 | 16.92 |

The repairs use more calls and tokens than the old core. Updated RAIR uses more
calls but fewer recorded tokens than KAIR. These are descriptive local costs,
not a universal speed or price advantage. Timing excludes controller setup and
the reference interpreter's startup. All token counts were available, all
citations referred to original source locations, and no gold annotation issues
required exclusion from source metrics. Source-sentence citation F1 was 47.6%
for updated RAIR, 21.2% for the control and 49.1% for KAIR.

The deliberately selected development cohort yielded no question errors in
either system: RAIR answered nine of 12 with three exact matches; KAIR answered
seven with four exact matches. See the [development report](../results/step5_development.md).
These selected cases are diagnostic evidence, not a second generalization test.

## Verification and source versions

The [measured-run audit](../results/step5_validation.json) passed. It rescored
all 600 outcomes, checked every budget, generation setting, final policy,
execution position and reference provenance, verified prior-artifact hashes
and exclusions, and independently reproduced the confidence intervals using
standard-library inclusive quantiles. Completed-journal resume regenerated
reports with all network/model requests blocked. The frozen measurement archive
was independently restored and passed **190 tests**.

An offline boundary test additionally exposed an understated standalone cost
estimate: five retrieval rounds plus five stalled-gap planner calls can use
27 calls rather than the advertised 22. After the complete frozen run and its
audit, only the controller's policy metadata and documentation were corrected.
No inference method or prompt changed. The hard common cap remains 18 calls.

The final code passes **191 tests**, including that boundary case. All **200
recorded RAIR runs** were replayed without network access: every model request
and result matched, including answers, citations, memory, stopping reasons and
budget counts, after removing only wall-clock timings. An AST comparison also
confirmed unchanged inference code. See [current-code verification](../results/step5_current_verification.json)
and [test results](../results/step5_final_tests.json).

- [Frozen manifest](../config/step5_benchmark.json),
  [configuration](../config/step5_benchmark.yaml),
  [prior-exposure audit](../config/step5_exclusions.json).
- [Full benchmark journal](../results/step5_fresh_benchmark.jsonl),
  [machine summary](../results/step5_fresh_benchmark.summary.json),
  [generated report](../results/step5_fresh_benchmark.md).
- [Measured source archive](../results/step5_source_snapshot.zip): the exact
  source/configuration/tests frozen before the 600-run experiment.
- [Final source archive](../results/step5_final_source_snapshot.zip): the final
  code with the standalone estimate correction and its regression test.

The original manifest intentionally rejects the later metadata-only source
revision. To reproduce that exact frozen manifest, extract the measured archive
into a separate project folder, install `requirements.txt`, supply the original
dataset under `data/raw/`, and use the recorded model/runtime. Preserve existing
journals; use a new output filename. Alternatively, repeat the same cohort with
the final code by preparing a new manifest:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m src.experiments.compare prepare --config config/step5_benchmark.yaml --output config/step5_replication.json
.\.venv\Scripts\python.exe -X utf8 -B -u -m src.experiments.compare run --manifest config/step5_replication.json --output results/step5_replication.jsonl
```

This is replication of already exposed questions, not a new untouched test.
A completed run containing question errors returns exit code 1 while preserving
its complete journal and summary. The original measured audit was performed
before the metadata correction; `results/step5_replay.py` verifies the final
source against that audited measurement without new inference.

## Limits

This remains a local competitive KAIR adaptation, not a replication of a
published asynchronous deployment. Source overlap measures citation selection,
not semantic entailment. The same small model performs extraction and
verification, so a valid source ID or accepted claim does not guarantee factual
correctness. Equal caps do not imply equal token use or latency.

RAIR still abstains on 61 of 200 runs. Of its 139 answered runs, 81 exactly
match gold; the other 58 are not exact matches and may receive partial F1.
Validation success therefore does not mean reasoning is fully solved. The
fresh HotpotQA cohort is ordinarily answerable; the synthetic missing-evidence
checks do not establish broad unanswerable-query calibration. Other models,
the full dataset and independent external corpora have not been evaluated here.

Step 5 completes the targeted reliability repairs and their controlled fresh
evaluation. Step 6 subsequently implemented the separate
[working dashboard](DASHBOARD.md); the Step 5 results above remain the recorded
research experiment.
