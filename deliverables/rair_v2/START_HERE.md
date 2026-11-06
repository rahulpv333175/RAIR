# RAIR v2 Deliverables — START HERE

Welcome to the **RAIR v2 Research Update package**.

This directory contains the complete deliverables, outcome census, failure analysis, and audit documentation for the evaluation of **Role-Aware Iterative Retrieval (RAIR v2)** versus competitive **KAIR** on HotpotQA multi-hop question answering.

---

## 1. Directory Contents

* **`RAIR_v2_Outcome_Census.csv`**: Full line-by-line census of all 140 system runs (70 matched pairs) with exact match scores, F1, latency, tokens, and stop reasons.
* **`RAIR_v2_Findings.md`**: Executive summary of empirical results, paired bootstrap confidence intervals, and head-to-head metrics.
* **`RAIR_v2_Failure_Review.md`**: Diagnostic error review analyzing Step 10 failure resolution and remaining edge cases.
* **`RAIR_v2_Presentation.md`**: 15-slide structured presentation deck with speaker notes for viva or defense.
* **`RAIR_v2_Research_Update.zip`**: Self-contained compressed archive containing all deliverables.

---

## 2. Independent Audit & Reproduction

To verify the research artifacts locally:

```powershell
# 1. Run core unit test suite (all tests pass)
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_rair_*.py"
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_kair.py"

# 2. Re-verify the frozen source hash
.\.venv\Scripts\python.exe -c "import hashlib, json; h = hashlib.sha256(open('src/llm/prompts.py', 'rb').read()).hexdigest(); f = json.load(open('results/rair_v2/rair_v2_freeze.json', 'r', encoding='utf-8')); assert h == f['source_sha256']['src/llm/prompts.py']; print('HASH VERIFIED:', h)"

# 3. Re-run combined analysis and bootstrap uncertainty calculation
.\.venv\Scripts\python.exe tools\analyze_overall.py
```

---

## 3. Key Findings at a Glance

* **Exact Match (EM):** RAIR v2 **57.1%** vs KAIR **55.7%** (+1.4 pp net advantage across 70 pairs).
* **Historical Recovery:** RAIR improved from **22.0%** in Step 10 to **57.1%** in RAIR v2 (+35.1 pp surge).
* **Retrieval Recall:** RAIR v2 achieved **90.7% gold document recall** vs KAIR's **85.7%**.
* **Efficiency:** RAIR v2 executed in **14.9s** (vs 17.1s) and consumed **9,441 prompt tokens** (vs 9,772).
