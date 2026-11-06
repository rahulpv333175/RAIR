# Teacher presentation package

Step 7 is complete for the local RAIR and KAIR research prototype.

## Files

- RAIR_KAIR_Final_Report.docx and .pdf: 12-page final report.
- RAIR_KAIR_Presentation_Final.pptx and .pdf: 12 slides, including editable diagrams, tables, a native chart and presenter notes in the PowerPoint.
- RAIR_KAIR_Demo_Script.docx and .pdf: 3-page script with setup, spoken explanations and a recorded-evidence fallback.
- RAIR_KAIR_Viva_Questions.docx and .pdf: 30 questions and answers across 6 pages.
- Remaining_Failure_Review.md: 12 trace-based examples with question IDs and seeds.
- Benchmark_Outcome_Census.csv: all 600 frozen outcomes.
- Verification.json: release checks, provenance and file hashes.

## Before presenting

1. Fill the student or team names, roll numbers, college, department, guide and presentation date in the editable documents. Fill the presentation cover fields too. Save updated PDF copies after those edits.
2. Open the PowerPoint in slide-show mode and rehearse once. The slides take about 8 to 10 minutes, followed by a 6 to 8 minute demo. Adjust to the teacher's time limit.
3. On this computer, open E:\Projects\role_aware_kair and run start_dashboard.cmd. Ollama must have qwen3.5:4b installed and running. Open http://127.0.0.1:8765/. No Internet is needed for the configured local demo.
4. Keep the PDF copies and the saved Step 6 screenshot available if live inference is unavailable. Clearly label saved evidence as recorded.

## Results to state accurately

Updated RAIR scored 40.5% EM and KAIR 36.0% on the final cohort. RAIR minus KAIR was +4.5 percentage points, 95% question-cluster interval -3.0 to +12.0. Superiority over KAIR is not established.

The primary matched control supports a +22.0-point gain over the earlier RAIR core, with interval +15.0 to +29.5. All arms use the same current final policy. These conclusions concern one local model, the sampled supplied-document tasks and common resource caps.

Passing 207 tests verifies software behavior, not perfect answer accuracy. Remaining failures are documented. The report does not silently upgrade aliases or wording differences to exact matches.

## Reproduction and evidence

The project root retains the full raw journals, manifests, measured-source archives and verification scripts. This presentation bundle is not a copy of the Python environment, model weights or full dataset. Use the existing project source package and README for setup or reproduction on another computer.

Step 7 added no reasoning changes and did not rerun or tune the research benchmark. Two new browser rehearsals verified complete evidence and missing evidence. Exact Word and PowerPoint outputs were opened and rendered in installed Microsoft Office 16.0. Chart edit, resize, save and reopen were tested on a private copy. Other slide applications and another machine were not tested.
