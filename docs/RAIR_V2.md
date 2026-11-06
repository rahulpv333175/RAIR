# Role-Aware Iterative Retrieval v2 (RAIR v2)

This document provides the technical specification, architectural design, and empirical validation of **RAIR v2** on multi-hop question answering (HotpotQA).

---

## 1. Architecture Overview

RAIR structures iterative multi-hop retrieval into six specialized functional roles coordinated by a central controller:

1. **Decomposer:** Breaks the complex root question into a sequence of dependent sub-questions (gaps).
2. **Query Planner:** Formulates focused retrieval queries for the active unresolved gap.
3. **Evidence Filter:** Selects relevant sentences from retrieved documents.
4. **Fact Extractor:** Extracts candidate factual claims grounded in the filtered evidence.
5. **Verifier:** Checks candidate claims against evidence and decides admission into shared memory.
6. **Synthesizer:** Formulates the final concise answer using admitted facts in shared memory.

---

## 2. The Step 10 Dilemma & v2 Root Cause Analysis

In the Step 10 evaluation, RAIR achieved only 22.0% Exact Match and abstained in 71% of runs, while competitive KAIR scored 49.0% EM.

An audit of all 200 Step 10 RAIR runs (`results/improvement_v2/failure_audit.csv`) revealed that:
* In **50 runs**, RAIR retrieved every annotated gold document but admitted **zero facts** into memory.
* The verifier conflated `answer_type_ok` (fact admission) with `resolves_gap` (gap satisfaction). Intermediate bridge facts were rejected because a single fact did not completely answer the multi-hop gap.
* The fact extractor replaced bridge entity names with ambiguous pronouns (`"The band"` instead of `"Diamond Rio"`), breaking subsequent retrieval steps.

---

## 3. RAIR v2 Engineering Interventions

Implemented in [`src/llm/prompts.py`](../src/llm/prompts.py):

### 3.1 Bridge-Entity Identity Preservation (Fact Extractor)
* **Rule 11:** Explicitly name identified bridge entities in candidate claims (e.g., *"The band previously named X is Y"*).
* **Rule 12:** Preserve each comparison attribute or category as a separate supported candidate.
* **Rule 14:** Resolve pronouns and generic references using document titles.

### 3.2 Decoupled Fact Admission Gate (Verifier)
* **`answer_type_ok`:** Set to `true` if the candidate provides a supported factual value, attribute, entity, or relation useful to the question, including intermediate bridge facts.
* **`resolves_gap`:** Maintained as strict; set to `true` only when the candidate fully completes the active gap.
* Valid bridge facts enter shared memory with `answer_type_ok=true` and `resolves_gap=false`.

### 3.3 Adversarial Negative Control
Synthetic unsupported relations were evaluated to verify that loosening fact admission does not accept hallucinations:
* Real retrieved evidence for *Diamond Rio* + synthetic unsupported relation:
  `"The band originally known as the Grizzly River Boys was founded by Mira Solen to conquer Prussia."`
* **Result:** **REJECTED** (`supported_by_evidence=False`, `accepted=False`).

---

## 4. Empirical Evaluation Across 70 Matched Pairs (140 Runs)

Evaluated across two disjoint HotpotQA cohorts (Phase 2: 10 questions / 20 pairs; Phase 3: 25 questions / 50 pairs) under identical resource caps (`RunBudget(4, 18)`):

| Metric | RAIR v2 | Competitive KAIR | Net Delta |
| :--- | :---: | :---: | :---: |
| **Exact Match (EM)** | **57.1% (40/70)** | 55.7% (39/70) | **+1.4 pp** |
| **Answer F1** | **63.6%** | 64.4% | **-0.8 pp** |
| **Cumulative Retrieval Recall** | **90.7%** | 85.7% | **+5.0 pp** |
| **Abstention Rate** | **20.0% (14/70)** | 12.9% (9/70) | +7.1 pp |
| **Paired Head-to-Head** | **8 wins** | 7 wins | **+1 win (55 ties)** |
| **Mean Prompt Tokens** | **9,441** | 9,772 | **-3.4%** |
| **Mean Execution Latency** | **14.9s** | 17.1s | **-12.9%** |

### Recovery Over Step 10
* **Exact Match Surge:** 22.0% -> 57.1% (**+35.1 percentage points**).
* **Abstention Drop:** 71.0% -> 20.0% (**-51.0 percentage points**).
* **Retrieval Advantage:** RAIR v2 consistently locates 5.0 pp more ground truth evidence than KAIR.

---

## 5. Artifacts and Reproduction

* **Freeze Ledger:** [`results/rair_v2/rair_v2_freeze.json`](../results/rair_v2/rair_v2_freeze.json)
* **Source Snapshot:** [`results/rair_v2/rair_v2_source_snapshot.zip`](../results/rair_v2/rair_v2_source_snapshot.zip)
* **Full Research Report:** [`results/rair_v2/RAIR_V2_FINAL_REPORT.md`](../results/rair_v2/RAIR_V2_FINAL_REPORT.md)
* **Outcome Census:** [`deliverables/rair_v2/RAIR_v2_Outcome_Census.csv`](../deliverables/rair_v2/RAIR_v2_Outcome_Census.csv)
