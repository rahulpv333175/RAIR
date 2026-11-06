# RAIR Held-Out Test Benchmark Package (4 November 2026)

Welcome to the RAIR Held-Out Test Benchmark release. This package contains the complete results, census, failure audit, and executive presentation for the 200-run test benchmark on 50 untouched questions.

## Directory Contents

* **`RAIR_Test_Outcome_Census.csv`**: Granular census of all 200 system runs (100 matched pairs) including question IDs, predictions, EM, F1, tokens, and latency.
* **`RAIR_Test_Findings.md`**: Comprehensive findings document with paired statistical comparisons and 95% bootstrap confidence intervals.
* **`RAIR_Test_Failure_Review.md`**: Granular failure audit and residual error analysis.
* **`RAIR_Test_Presentation.md`**: Executive presentation slide deck outlining the architectural rationale and empirical proof.

## Research Dashboard

The research dashboard is live at `http://127.0.0.1:8765`. Select the **Test** tab to inspect the interactive comparison table, paired exact-match charts, and complete execution traces for all 100 matched pairs.
