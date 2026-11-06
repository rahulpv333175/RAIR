# Live progress and lightweight polling

Status: the user confirmed the dashboard and its tests work. After authorization
to resume autonomous testing, the current full Python suite passed 239 tests,
and JavaScript syntax/polling checks passed. The run instructions below remain
available for reproduction; no user-run checks are pending for Step 9.

The user reported that the first regression commands passed, but the browser
showed `Unknown endpoint` after starting a comparison. This matches an older
Python process serving updated JavaScript without the new progress routes.
The follow-up fix advertises the server's live-progress capability at bootstrap
and uses compatible full-job polling when that feature is absent. An unexpected
`Unknown endpoint` from progress also activates the fallback; other failures
remain visible. Successful polling clears a previous transient error banner.
Restart the Python server and refresh the browser to enable the new live steps.
The user confirmed the additional compatibility checks passed, and they were
rerun successfully during Step 9 verification.

## Behavior

Each engine panel now has a live step list. Completed stages appear while the
remaining inference continues. Expand a step to inspect its structured data.

- RAIR: generated gaps/dependencies, selected gap/query, retrieved titles and
  BM25 scores, selected original sentences, extracted candidates, verifier
  decisions/reasons and newly admitted shared facts.
- KAIR: agent identity and competition, queries/retrieval, candidates,
  provisional binary checks, committed private knowledge/requirements/refined
  context, and selected shared context. A passing checker does not imply a
  private-state commit: filtering must also succeed.
- Existing final answers, complete timelines, raw-result downloads and
  historical research views remain available. Live updates do not expose hidden
  reasoning, stream partial unvalidated JSON, or declare a final answer early.

The browser requests `/api/runs/<id>/progress?after=<cursor>` every 500 ms,
instead of downloading the whole job every 1200 ms. Replies contain status,
counters, completed-result statuses, a cursor and only new stage events. They
exclude source pools, model prompts, response journals and completed traces.
After an engine finishes, `/api/runs/<id>/results/RAIR` or `.../KAIR` supplies
its full result once. Metadata is read once per opened run. Events replay from
cursor zero after refresh and sequence numbers prevent duplicate display.
Full raw JSON is formatted in the DOM only when its disclosure is opened.
Live steps stay in memory for the same retained jobs; saved final journals
remain the persistent evidence after server restart.

## Fairness and limits

Progress callbacks are optional and receive detached copies. A callback failure
is logged and does not stop inference. No prompts, model settings, budgets,
seeds, source inputs, selection policies or serial execution order were changed.
The benchmark runner does not enable observers. Frozen experiment files were
not edited. Current source hashes change because observational hooks were added;
the old Step 8 source-hash audit is historical, not a check of this revision.

The new tests compare scripted model request payloads and complete semantic
results with observers enabled versus disabled, including a mutating or failing
observer. This is regression evidence once the tests pass, not a fresh accuracy
benchmark. Live observation introduces some copying/rendering overhead; elapsed
times from different revisions should not be treated as a controlled speed study.
The change reduces repeated transfer and improves visible progress. It does not
make the local model generate tokens faster. New-event replies can still carry
the source excerpts needed to inspect that stage.

## Run tests in PowerShell

From `E:\Projects\role_aware_kair`:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_live_progress.py -v
```

These tests use scripted model transport, not Ollama inference. They cover
observer neutrality/isolation, updates before engine completion, delta replay,
small idle responses, cursor validation, result routes and download compatibility.

Then check browser polling with Node (already bundled on this computer):

```powershell
$nodeExe = 'C:\Users\rahul\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
& $nodeExe --check dashboard/static/app.js
& $nodeExe tests/live_progress_client.cjs
```

The syntax check should print nothing and succeed. The client checks should
print `PASS: ...`. They check event deduplication, result retrieval once per
engine, metadata recovery and stale-response handling without starting a browser.

Finally run the existing full regression suite:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests
```

Send the complete output, especially tracebacks or any `FAIL`/`ERROR` lines.
Do not run `results/step8_verify.py` as a current-source acceptance test: its
source-hash assertions intentionally refer to the older Step 8 revision.

## Manual browser check

1. Stop an older dashboard server with Ctrl+C. Run `start_dashboard.cmd`, open
   http://127.0.0.1:8765/, and refresh to load the updated scripts.
2. Open **Live execution**, choose **Two-hop example · complete evidence** and
   run. Expand live steps before the comparison finishes. Both engines should
   return Nerava with book/author citations.
3. Refresh during a run: it should reconnect and replay steps without duplicates.
   Input fields stay locked while inference is active; step disclosures and
   research navigation remain usable.
4. Run **Two-hop example · missing evidence**. Inspect the unresolved birthplace
   requirement and confirm the final outputs rather than assuming an answer.
5. In browser Network tools, progress URLs should use an increasing `after`
   cursor. An idle reply has `events: []` and no `results`, `task` or model
   prompts. Each completed engine result should be requested once per page load.
6. Check final detailed traces, raw JSON disclosure, benchmark/failure views
   and run download. Send any visible error and whether the page felt responsive.

The model may finish simple stages between polls, so several updates can appear
together. During a long model call, its current phase remains visible and the
elapsed counter continues to update; there is no invented percentage complete.
