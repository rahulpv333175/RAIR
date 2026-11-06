# RAIR v2 Failure Review & Error Analysis

**Date:** 2 November 2026  
**Audited Systems:** RAIR v2 vs Competitive KAIR  
**Corpus:** 35 Disjoint HotpotQA Questions (70 Matched Pairs / 140 Runs)  

---

## 1. Resolution of Historical Step 10 Failure Modes

In Step 10, RAIR abstained on **71 out of 100 runs** (71.0% abstention rate). The failure audit (`results/improvement_v2/failure_audit.csv`) identified three root causes, all resolved in RAIR v2:

| Historical Failure Mode | Step 10 Manifestation | RAIR v2 Resolution | Outcome in RAIR v2 |
| :--- | :--- | :--- | :--- |
| **False Fact Rejection** | 50 runs retrieved all gold documents but admitted 0 facts | Decoupled `answer_type_ok` from `resolves_gap` in verifier | Gold evidence admitted into memory; abstentions fell to 20% |
| **Bridge Entity Loss** | Extractor emitted `"The band was previously known as X"` | Added Rule 11 (explicit bridge naming) & Rule 14 (title grounding) | Bridge entities (*Diamond Rio*, *Warner Animation Group*) correctly preserved |
| **Partial Attribute Rejection** | Comparison styles rejected because no final count was supplied | Added Rule 12 (comparison attribute preservation) | Multi-attribute lists accepted as valid candidate facts |

---

## 2. Analysis of Remaining RAIR v2 Abstentions (14 / 70 Runs)

In RAIR v2, only **14 abstentions** occurred across 70 runs (20.0% abstention rate). A detailed diagnostic breakdown reveals:

1. **Budget Exhaustion (8 runs):**
   * Occurred on complex questions with distractor documents that closely mirrored the target entity.
   * RAIR reached its limit of 18 LLM calls or 4 retrievals while continuing to verify candidate claims.
   * *Example:* `5ac397fe...` (Seed 42) — Exhausted 18 calls exploring alternate historical candidates.
2. **Repeated Query Protection (4 runs):**
   * The query planner detected that reformulated search queries matched previously executed queries, stopping cleanly rather than looping.
   * *Example:* `5a7f7b3b...` — Stopped at round 3 with `repeated_query` after two consecutive identical searches.
3. **Synthesis Conservatism (2 runs):**
   * All gaps were resolved, but the final synthesis prompt abstained due to residual ambiguity in the gold context.
   * *Example:* `5ae22f4e...` — Both RAIR and KAIR abstained on both seeds because the context contained conflicting founding dates.

---

## 3. Contrast with KAIR Errors and Hallucinations

KAIR exhibited a lower abstention rate (9 abstentions, 12.9%), but demonstrated notable failure modes:
* **Premature Convergence / Incomplete Evidence:** In 10 runs, KAIR generated confident answers based on partial retrieval, producing incorrect answers where RAIR v2 correctly retrieved the second hop and answered correctly (e.g., `5abef8fd...` where KAIR answered `4` and RAIR answered `seven`).
* **Agent Competition Overhead:** When competing agents produced diverging proposals, KAIR required up to 17 LLM calls and 19+ seconds to resolve disputes, whereas RAIR's sequential roles resolved evidence in 14.9s average latency.
