# RAIR v3 Engineering & Research Plan: Pushing Multi-Hop QA Beyond 65% EM

**Author:** Autonomous Agentic AI Research  
**Date:** 2 November 2026  
**Status:** Pre-Registration Plan & Design Specification  
**Target:** Elevate RAIR Exact Match from 57.1% to 65%+, reduce abstentions from 20% to <10%, and expand the lead over competitive KAIR.

---

## 1. Baseline Performance Context (RAIR v2 Achievements)

In RAIR v2, we resolved the primary failure mechanism of Step 10 (conflating intermediate fact admission with gap resolution):
* **Step 10:** 22.0% Exact Match, 71.0% Abstentions (-27.0 pp deficit vs KAIR).
* **RAIR v2 (Pooled 140 runs across 70 pairs):**
  * Exact Match: **57.1%** (+35.1 pp gain over Step 10; +1.4 pp lead over KAIR)
  * Gold Document Recall: **90.7%** (vs 85.7% for KAIR)
  * Latency: **14.9s** (vs 17.1s for KAIR, 12.9% faster)
  * Prompt Tokens: **9,441** (vs 9,772 for KAIR, 3.4% fewer tokens)
  * Head-to-Head: 8 RAIR wins, 7 KAIR wins, 55 ties.

While RAIR v2 established parity and a net lead, **20.0% of runs still abstained** (14/70) and several answered questions suffered from **near-miss lexical mismatches**.

---

## 2. Granular Root Cause Analysis of Remaining Failures

A systematic review of all 30 non-exact runs in RAIR v2 (`tools/inspect_nonexact.py`) revealed four distinct, addressable defect categories:

### Defect 1: Polar / Boolean Question Misalignment (EM Impact: ~3-5 pp)
* **Example Case:** `5aba8533...` — *"Were both events in the 19th/20th century?"*
  * **Gold:** `"yes"`
  * **RAIR v2 Prediction:** `"World War II and the American Civil War"` (EM=0, F1=0)
* **Root Cause:** The synthesizer prompt instructs the model to produce the *"shortest complete answer using ONLY admitted facts"*. On yes/no questions, the LLM assumes "complete answer" means stating the named entities rather than a boolean token.

### Defect 2: Conversational Span Wrapping in Synthesizer (EM Impact: ~4-6 pp)
* **Example Case 1:** `5ade15f3...` — *"In which film did Katherine Waterston portray Chrisann Brennan?"*
  * **Gold:** `"Steve Jobs"`
  * **RAIR v2 Prediction:** `"Katherine Waterston portrayed Chrisann Brennan in "Steve Jobs" (2015)"` (EM=0, F1=0.36)
* **Example Case 2:** `5ac3b62b...` — *"What act did FDR sign in 1936...?"*
  * **Gold:** `"Rural Electrification Act"`
  * **RAIR v2 Prediction:** `"The Rural Electrification Act of 1936"` (EM=0, F1=0.75)
* **Root Cause:** The model outputs a complete grammatical sentence repeating the question premise rather than extracting the minimal target noun phrase.

### Defect 3: Controller Late-Stage Budget Exhaustion (Coverage Impact: ~10 pp)
* **Occurrence:** 8 of the 14 abstentions in RAIR v2 were caused by `budget_exhausted` (18 LLM calls or 4 retrievals).
* **Root Cause:** After the Decomposer and Fact Extractor successfully locate and verify facts for all gaps, the controller does not immediately break; it initiates redundant rounds of query planning and evidence filtering on already-resolved gaps, hitting the 18-call ceiling before synthesis can be called.

### Defect 4: Repeated Query Stalls (Coverage Impact: ~5 pp)
* **Occurrence:** 4 of the 14 abstentions in RAIR v2 were caused by `repeated_query`.
* **Root Cause:** When BM25 does not find the second hop in the top-3 results of query $Q_1$, the Query Planner produces the same search terms for round 2. The controller's loop protection halts the system with `repeated_query`.

---

## 3. Targeted Technical Interventions for RAIR v3

### Intervention 1: Polar Auxiliary Question Detection in Synthesizer
In `src/llm/prompts.py` (Synthesizer Prompt):
```markdown
Boolean / Polar Question Rule:
- If the question begins with an auxiliary or modal verb ("Is", "Are", "Was", "Were", 
  "Did", "Do", "Does", "Has", "Have", "Can", "Could"), the answer MUST be strictly 
  either "yes" or "no". Do NOT restate the subject, entities, or explanatory clauses.
```

### Intervention 2: Minimal Span Extraction Rule
In `src/llm/prompts.py` (Synthesizer Prompt):
```markdown
Minimal Span Rule:
- When asked "In which film/book/album/city/country...", output ONLY the proper name 
  of the work or place (e.g., "Steve Jobs", not "Katherine Waterston portrayed X in 
  the film Steve Jobs"). Strip introductory prepositional phrases, actor names, 
  and parenthetical release years unless specifically asked.
```

### Intervention 3: Early Exit on Full Gap Resolution
In `src/rair/controller.py`:
* When `state.all_gaps_resolved()` is `True`, immediately terminate the retrieval/verification loop and advance to `synthesizer.run()`.
* Saves 4–6 LLM calls per run on complex questions, completely preventing spurious budget exhaustion.

### Intervention 4: Query History Avoidance in Query Planner
In `src/llm/prompts.py` (Query Planner Prompt):
* Pass `state.executed_queries` into the planner prompt.
* Add instruction: *"Do NOT repeat any of the following previously executed queries: {executed_queries}. If previous queries did not resolve the gap, reformulate using alternative entity synonyms, occupations, or document titles."*

---

## 4. Staged Execution Protocol & Safety Gates

1. **Gate 1: Diagnostic Regression Suite**
   * Re-run all 4 targeted near-miss failure cases:
     * `5aba8533...` -> must answer `"yes"`.
     * `5ade15f3...` -> must answer `"Steve Jobs"`.
     * `5ac3b62b...` -> must answer `"Rural Electrification Act"`.
     * `5a7f7b3b...` -> query planner must reformulate rather than repeat.
   * Run the adversarial negative control to ensure 100% precision rejection of unsupported claims.

2. **Gate 2: Unit Test Suite Integrity**
   * All 158 tests across `test_rair_*.py`, `test_kair.py`, `test_metrics.py`, `test_bm25.py`, and `test_ablation_dashboard.py` must pass cleanly.

3. **Gate 3: Disjoint Paired Benchmark (Phase 1 of v3)**
   * Sample 20 new, strictly untouched questions (seeds 42, 43; 40 paired runs).
   * Exclude all 380 previously touched question IDs.
   * Evaluate under identical 4/18 budget caps with unchanged KAIR baseline.

4. **Gate 4: Dashboard Integration & Release**
   * Update `dashboard/ablations.py`, `server.py`, and `research.js` to expose RAIR v3 alongside v2 and historical benchmarks.
   * Generate updated outcome census and research update package.
"""
    path.write_text(content, encoding="utf-8")
    print(f"[V3_PLAN] Wrote {path}")

def main():
    build_docs_rair_v3(DOCS / "RAIR_V3_PLAN.md")

if __name__ == "__main__":
    main()

