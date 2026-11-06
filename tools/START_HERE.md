# RAIR v2 — Phase 1 (reversible development patch)

**Research aim:** Evaluate whether admitting supported intermediate facts while keeping completion criteria strict, plus preserving bridge-entity identity during extraction, reduces RAIR false abstention and improves answer correctness without admitting unsupported claims.

This is an **unvalidated development change**, not an improved benchmark result. The original Step 10 journal and unchanged KAIR remain the historical baseline. The supplied script only changes `src/llm/prompts.py` after creating a content-addressed backup.

## Apply on Windows

1. Save `apply_rair_v2_phase1.py` into `E:\Projects\role_aware_kair\tools\`.
2. Open PowerShell:

```powershell
cd E:\Projects\role_aware_kair
.\.venv\Scripts\python.exe tools\apply_rair_v2_phase1.py
.\.venv\Scripts\python.exe -m py_compile src\llm\prompts.py
.\.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests
```

The patch checks the exact source anchors and refuses to modify unknown versions. If prior experimental edits differ, it exits with a message and leaves the file unchanged. Share that error rather than forcing the patch.

## Scope of Phase 1

- The fact extractor must name a supported bridge entity, rather than replacing it with an ambiguous reference.
- The verifier must admit supported partial facts that do not yet complete a gap.
- No unsupported relation may be promoted; `resolves_gap` remains separate from fact admission.
- No changes to KAIR, evaluation, frozen results, budgets or model settings.

## Evidence required before making claims

1. Run 3 targeted development cases: the animation comparison, Teutonic Knights, and the Grizzly River Boys bridge case. Include an unsupported-relation negative control.
2. Track source-backed fact admission, correct bridge-entity names, gap completion, and final answer vs abstention.
3. Evaluate a disjoint question set with *unchanged* KAIR under equal budgets and identical source pools. Include latency, tokens, accuracy, abstention and claim support.
4. Run a larger confirmatory experiment only after freezing v2; preserve all runs, including failures.

For IEEE submission, report both positive and negative results truthfully. Avoid presenting development-set improvements as independent generalization. No acceptance or publication outcome is guaranteed.
