# RAIR end-to-end execution

The controller in `src/rair/controller.py` accepts only a `QuestionInput`:
question ID, question text, and the question's document pool. Gold answers
and supporting-fact annotations remain in the experiment/evaluation layer.

## Execution policy

1. Create fresh shared state and a separate document store for the question.
2. Decompose the question into validated, ordered information gaps.
3. Select the least-attempted actionable gap, then priority and original order.
   Dependencies must already be resolved; stalled gaps are excluded.
4. Plan a new query and retrieve up to the configured BM25 `top_k` documents.
5. Select exact source sentences, extract candidate claims, and verify them.
6. Promote accepted claims to shared memory. Resolve the gap only when the
   verifier explicitly says an accepted candidate resolves it.
7. Repeat until all gaps are resolved, no gap is actionable, or the retrieval
   round limit is reached. A repeated query can fall back once to original
   question terms, paying for that retrieval. Further duplicates stall only
   that gap; another actionable gap can continue. Pass evidence outcomes to planning.
8. Synthesize from verified facts only. An answer may be generated from
   sufficient verified facts at the round limit even if some proposed gaps
   remain open. Insufficient facts should produce an empty answer and abstention.

Empty retrieval, evidence, or candidate sets are normal outcomes; they do
not resolve a gap. Downstream roles skip generation when their input set
is empty. Unresolved dependencies never become actionable merely because
a retrieval returned documents.

With `max_rounds = 5`, each question uses at most five retrieval calls and
27 LLM generation calls: one decomposition, up to four calls per retrieval
round, up to five extra stalled-gap planner calls, and one final synthesis.
The shared comparison instead enforces four retrievals and 18 calls, including
one reserved final call. Calls run sequentially. Each request also
has the configured timeout and generation-token limit. There are no automatic
retries or JSON repairs. This is a call/round budget, not a strict overall
wall-clock or total-token budget.

Malformed output, invalid source references, truncated
generations, and transport failures stop that question with `status: error`,
an empty prediction, and the failing stage/type/message. Previously completed
rounds and model calls remain available in its result. Errors are counted
separately from ordinary abstentions. An error in one question does not prevent
the dataset runner from attempting subsequent questions.

Stalls appear in `planner_stalls`; `stop_reason: repeated_query` means no
unstalled actionable gap remains. Final synthesis can still answer from
sufficient verified facts or abstain. Stalled planning calls count toward
usage; a duplicate search is not executed. See [Step 5](RAIR_IMPROVEMENTS.md)
for constrained source IDs, partial-fact admission and the shared final policy.

## Outputs

`python -m src.experiments.run_rair --limit 3` creates a timestamped JSONL
file in `results`. Relative arguments resolve against the project root.
`--offset`, `--limit`, `--config`, and `--output` are supported. Explicit
output filenames must be new; existing outputs are never overwritten.

The first line records configuration, dataset SHA-256, selected question IDs,
Ollama/model identity, and the execution policy. Each subsequent result contains:

- `prediction`: answer text, cited verified fact IDs, and abstention flag.
- `sources`: deduplicated original source sentences for the cited facts,
  including document ID, title, and zero-based sentence index.
- `state`: gaps, dependencies, verified facts, query history and round counter.
- `rounds`: queries, ranked documents, selected evidence, candidates, decisions,
  promoted facts, query origin and gap-resolution outcomes.
- `planner_stalls`: gap IDs and reasons for duplicate queries that could not
  use the question fallback.
- `llm_calls`: exact request payloads, raw responses, stage, timing, and
  transport/generation errors. Semantic validation errors are in the result's
  `error` field even when the HTTP generation itself succeeded.
- `usage`: actual generation attempts, retrieval calls, reported prompt/output
  tokens, model-call time, and full question time.
- `evaluation`: answer exact match and answer F1, computed after inference.

Token totals include counts from failed generations when Ollama returned
them. `token_counts_complete: false` means at least one attempt lacked counts;
reported totals are then only the known usage, not an estimate of missing usage.
Server-readiness requests are outside the generation-call budget.

The final summary scores all selected questions, including abstentions and
execution errors as empty predictions. It also reports answer coverage and
separate answered/abstained/error counts. The JSONL writer flushes each finished
question and the summary counts each stopping reason. An interrupted batch has
no final summary; completed lines can still be inspected. The in-flight question
is not checkpointed mid-generation.

## Validation and limits

`python -m unittest discover -s tests` exercises the real role implementations,
controller, retriever, validation, and dataset runner with scripted model
responses. Scripted transport tests verify integration behavior, not model
reasoning quality. A gold-label mutation test checks that changing annotations
does not change any model request.

When the sandbox restricts its default temporary directory, the same test suite
can be run with Python's temporary directory set to the writable project root.
This changes only where test fixtures are created.

`python -m src.experiments.check_rair_pipeline` runs the actual local model on
a constructed two-hop question without manually seeding gaps or verified facts.
It checks both a complete author-to-birthplace chain and a document pool without
the birthplace. The missing-evidence case uses two retrieval rounds. Each run
saves its settings, environment, budgets, traces, and individual pass/fail results.

These are integration diagnostics. They are not a full HotpotQA benchmark or
evidence that RAIR outperforms KAIR. Verification and final answer sufficiency
remain model judgments: source/index validation does not prove semantic support
or guarantee a correct final answer. Larger experiments and comparison controls
belong to subsequent project steps.

## Step 1 validation: 18 October 2026

- Setup check passed on Python 3.12.10.
- All 126 automated tests passed, including 22 new controller, runner, logging,
  and retrieval-budget tests. The sandbox run used the project root for temporary fixtures.
- The final live smoke check passed both cases using Ollama 0.34.1 and
  `qwen3.5:4b`: complete evidence produced `Nerava` with both source citations;
  removing the birthplace produced an empty-answer abstention.
  [Full smoke trace](../results/phase8_rair_pipeline_20261018T124631423018Z.json).
- The final three-question HotpotQA diagnostic completed with two answers,
  one abstention and zero execution errors. Exact match and answer F1 were
  both 0.3333 over all three questions; answer coverage was 0.6667.
  [Full dataset trace](../results/rair_20261018T124712290938Z.jsonl).

The first question was answered `Yes`, matching its reference. The second
returned `United States ambassador to Ghana` while the reference was
`Chief of Protocol`, so its score was zero. The third stopped on a repeated
query and abstained: its verifier had rejected useful series-identification
facts. These are remaining model/reasoning limitations, not successful answers.

During integration, the verifier's value-type instruction and the extractor's
entity-description instruction were clarified. A stalled planner now ends
retrieval explicitly and proceeds to synthesis rather than becoming a generic
execution error. Earlier failed diagnostics are preserved in `results`.
The two smoke cases were rerun with the final role prompts and controller.

The three HotpotQA questions were used for development diagnosis. Keep them
outside any future untouched evaluation subset. Step 1 establishes runnable,
bounded and traceable RAIR execution; it does not establish adequate research
accuracy. These are Step 1's historical results. Subsequent work is documented
in [KAIR](KAIR.md) and [Step 3 evaluation](EVALUATION.md).
