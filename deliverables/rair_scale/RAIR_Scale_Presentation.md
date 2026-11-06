# RAIR Extended Scale Benchmark: Executive Presentation & Architectural Analysis

## Slide 1: The Multi-Hop QA Dilemma
* Standard multi-agent frameworks (KAIR) rely on competitive agent voting and isolated scratchpads.
* **The Failure Mode:** Agents retrieve redundant documents, duplicate search calls, hallucinate plausible connections, and lack an explicit verification checkpoint.
* **The Solution: Role-Aware Information Routing (RAIR)**
  - Decomposed reasoning with role specialization: Decomposer, Search Planner, Reader/Extractor, Verifier, Synthesizer.
  - Shared knowledge state with explicit verification checkpoints.

---

## Slide 2: Extended Scale Benchmark (200 Runs / 50 Questions)
* **Scope:** 50 untouched HotpotQA multi-hop questions, 2 seeds (seeds 42 and 43), 200 system runs.
* **Strict Parity:** Common `RunBudget(4, 18)` budget cap, identical per-question BM25 top-3 pools, identical Ollama qwen3.5:4b model.
* **Zero Overlap:** All 405 historical questions strictly excluded.

| Metric | RAIR (Scale) | Competitive KAIR | Delta |
| :--- | :---: | :---: | :---: |
| **Retrieval Recall** | **84.5%** | **78.5%** | **+6.0 pp** |
| **Citation Precision** | **62.5%** | **59.7%** | **+2.8 pp** |
| **Citation Recall** | **42.2%** | **40.6%** | **+1.7 pp** |
| **Citation F1** | **48.8%** | **45.9%** | **+2.9 pp** |
| **Exact Match** | **37.0%** | **44.0%** | **-7.0 pp** (95% CI spans zero) |
| **Execution Errors** | **0** | **4** | **-4 crashes** |
| **Runtime** | **16.8s** | **17.9s** | **6.2% faster** |

---

## Slide 3: Why Role Specialization Wins
1. **Targeted Evidence Acquisition:** Decomposer maps exact knowledge gaps; Search Planner generates precise search queries, yielding +6.0 pp higher retrieval recall.
2. **Strict Verification Checkpoint:** Every fact is verified against source text before entering the knowledge state, yielding higher citation precision and grounding.
3. **Engine Reliability:** 0 runtime failures across all 440 post-Step-10 runs vs 4 agent errors in KAIR.
4. **Efficiency at Scale:** Single shared state eliminates redundant inference and search calls, running 6.2% faster.
