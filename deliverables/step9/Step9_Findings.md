# Step 9: component study findings

20 previously unscheduled questions, two seeds, four arms: 160 serial runs. All scores include errors and abstentions. The cohort was frozen before execution and excludes 225 prior scheduled/exposed dataset IDs. No model or protocol changes were made in response to these results.

| Arm | EM | Answer F1 | Coverage | Abstained | Errors | Mean calls | Mean tokens | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RAIR | 50.0% | 60.6% | 70.0% | 12 | 0 | 11.35 | 8981 | 14.74 |
| KAIR | 55.0% | 74.7% | 95.0% | 2 | 0 | 8.53 | 12250 | 19.38 |
| RAIR_NO_VERIFICATION | 55.0% | 73.0% | 95.0% | 2 | 0 | 7.33 | 4937 | 7.32 |
| RAIR_NO_DECOMPOSITION | 47.5% | 63.6% | 77.5% | 9 | 0 | 9.22 | 7459 | 11.32 |

## Prespecified component contrasts

Full RAIR minus each removal, with 97.5% pointwise question-cluster bootstrap intervals. Two primary EM comparisons use Bonferroni-style approximate 95% family coverage. F1, cost and RAIR-versus-KAIR are secondary. Seeds stay together; there are 20 independent question clusters, not 40.

- **RAIR_minus_RAIR_NO_VERIFICATION, exact_match:** -5.0 percentage points; interval [-15.0, +5.0]. Interval includes zero; direction is not established.
- **RAIR_minus_RAIR_NO_VERIFICATION, answer_f1:** -12.4 percentage points; interval [-25.0, +0.3]. Interval includes zero; direction is not established.
- **RAIR_minus_RAIR_NO_DECOMPOSITION, exact_match:** +2.5 percentage points; interval [-15.0, +17.5]. Interval includes zero; direction is not established.
- **RAIR_minus_RAIR_NO_DECOMPOSITION, answer_f1:** -3.0 percentage points; interval [-22.0, +15.0]. Interval includes zero; direction is not established.

## Failure and outcome census

| Compared with full RAIR | Both EM-correct | Only full correct | Only other correct | Both nonexact |
| --- | --- | --- | --- | --- |
| KAIR | 16 | 4 | 6 | 14 |
| RAIR_NO_VERIFICATION | 19 | 1 | 3 | 17 |
| RAIR_NO_DECOMPOSITION | 16 | 4 | 3 | 17 |

Exact-match failures include aliases and partial lexical overlap; they are not automatically semantic errors. Stop/error counts and deterministic illustrative pairs are in `results/step9_analysis.json`. No automatically selected illustration establishes why an architecture succeeded.

## What the removals mean

- **No gate:** all structurally valid extracted candidates enter shared memory without a semantic verifier call; a nonempty admission resolves its gap. Stored facts in that arm are unchecked, despite the legacy shared-state field name. Source validity is still enforced.

- **No decomposition:** one original-question gap replaces generated subquestions and dependencies. The same query planner, evidence filter, extractor, verifier and final synthesis remain.

The final synthesis prompt is identical in all arms. Removing a component necessarily changes calls, available budget usage and stopping behavior; this study estimates the whole removal intervention, not its effect at equal actual compute. Positions are cyclically rotated and balanced; this is not all possible predecessor orders. Local runtime measurements are descriptive, not a hardware-independent speed claim.

## Examiner explanation

“We tested our design rather than assuming every added role helps. We removed verification and decomposition separately, reran all systems on identical fresh inputs, measured both quality and cost, and reported the uncertainty. A component may reduce errors while increasing calls or abstention. We do not claim an improvement when the interval includes zero.”

## Step 10

Freeze the final chosen systems and run a larger untouched confirmation cohort, excluding these 20 questions and every earlier exposed ID. Choose the primary endpoint and sample size before execution. Update the final teacher report and release package after that study.
