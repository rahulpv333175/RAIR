# Step 9 research update

Step 9 is complete. This folder supplements the existing project and preserves
the original Step 7 teacher package as historical evidence.

- **Step9_Findings.md**: measured results, uncertainty and interpretation.
- **Step9_Failure_Review.md**: four paired cases showing both benefits and
  drawbacks of verification/decomposition.
- **RAIR_KAIR_Presentation_Step9.pptx**: 15 editable slides. Slides 1–12 retain
  the earlier historical presentation; slides 13–15 add the separate Step 9
  study. Personal cover fields remain blank.
- **Step9_Outcome_Census.csv**: all 160 scheduled outputs and their scores/costs.
- **Step9_Dashboard.png**: verified dashboard results view.

The dashboard runs on http://127.0.0.1:8765/. Its Benchmark view contains a
separately labeled Step 9 section. The server was refreshed and real live
complete/missing-evidence comparisons were checked without connection errors.

Full RAIR scored 50.0% EM, KAIR and no-gate 55.0%, and no-decomposition 47.5%.
Both prespecified component intervals include zero. The result is a useful
tradeoff study, not evidence that every added component improves accuracy.

Evidence and reproduction details are in `docs/ABLATIONS.md`,
`config/step9_ablations.json`, `results/step9_ablations.jsonl`,
`results/step9_verification.json` and the frozen `results/step9_source.zip`.
The update ZIP includes these records; it is not a standalone replacement for
the original project, dataset, virtual environment or local Ollama installation.

**Step 10:** freeze the final design and run a larger untouched confirmation
cohort, then consolidate the final teacher report and submission package.
That next experiment has not been started.
