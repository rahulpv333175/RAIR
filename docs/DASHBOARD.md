# Step 6: working RAIR vs KAIR dashboard

**Current dashboard: Step 8.** The live application described below is now part
of a five-view research dashboard. Use the [Step 8 guide](RESEARCH_DASHBOARD.md)
for the added timelines, benchmark charts, archived case browser and validation.
Step 6 results below remain historical checks of the initial dashboard.

The presentation concept is now a working local web application. The Python
server calls the existing RAIR and KAIR controllers; answers and traces are
generated live, not copied from the concept image. No reasoning-engine source
or frozen benchmark result was changed for this step.

## Open and run

Open **http://127.0.0.1:8765** while the dashboard server is running. From the
project root in PowerShell:

```powershell
.\start_dashboard.cmd
# Equivalent command:
.\.venv\Scripts\python.exe -X utf8 -B -u -m dashboard.server
```

Ollama must be running with the configured model, currently `qwen3.5:4b`.
If its service is stopped, run `ollama serve` in a separate terminal. The
dashboard reports an unavailable service or missing model and disables model
runs until a connection check succeeds. It never downloads a model itself.
If installation is needed, use the existing project's setup and
`requirements.txt`; this dashboard adds **no Python or JavaScript dependencies**.
Node was used only for development-time JavaScript syntax checks.

An existing server may already be using port 8765. Open its URL, or choose
another port with `start_dashboard.cmd --port 8766`. Stop a foreground server
with Ctrl+C. The server binds only to `127.0.0.1`; this is a local presentation
application, not a publicly deployed website.

## Present the project

1. Choose **Two-hop example · complete evidence**. Expand the source documents
   to show the book-to-author and author-to-city links, then run the comparison.
   Both live engines returned **Nerava** in validation.
2. Compare the answer panels and click a citation to inspect its original source.
   Open **Execution trace** to show RAIR's gaps, queries and verified facts, or
   KAIR's private agent knowledge and selected proposal. The full raw model
   requests, responses and resource counters are available inside each trace.
3. Choose **Two-hop example · missing evidence** and run again. Both engines
   abstained in validation, rather than supplying the unsupported city.
4. Choose **Write your own question and sources**, or edit an existing example.
   Source titles and sentence text are editable; put one sentence on each line.
   Sources can be added or removed. A run uses exactly that question and pool
   for both systems. Custom cases have no fabricated gold scores.
5. Try a **previously evaluated development question**. Its gold answer and
   exact-match/F1 scores appear only after both engines return. Editing that
   case turns it into an unscored custom case rather than reusing stale labels.
6. Show the **recorded Step 5 benchmark** separately: 100 questions, two seeds,
   600 runs including the old-core control. Live examples do not alter that
   table. Its statistical caveat remains visible: superiority over KAIR was
   not established.
7. Use **Download run JSON** to retain a complete comparison, including sources,
   predictions, states, budgets and model calls. Refreshing the page restores
   the browser's last retained run while the same server is running.

The source editor accepts one to twenty documents, with at most 100 nonempty
sentence strings per document, 100,000 source characters in total, and a question
of at most 2,000 characters. HTTP request bodies are limited to 256,000 bytes.
These are interface bounds; they do not enlarge the model's context window.

## Controls and saved evidence

- One comparison runs at a time. Both systems use the same configured local
  model, source pool, seed base, generation settings and final-answer policy.
- Default caps are **four retrievals and eighteen model calls per system**,
  including a reserved final call. Non-final temperature is 0.7 and final
  temperature is zero. KAIR retains independent agent seed offsets.
- A question-free warm-up happens before either system and is logged separately.
  Even seeds run RAIR first; odd seeds reverse the order. A single interactive
  example is a demonstration, not a new controlled research benchmark.
- The model digest and Ollama version are checked before and after the pair.
  A changed identity invalidates the comparison while preserving its traces.
- Inputs are locked during a run. Changing the question, a source or the seed
  clears prior result labels. Errors and abstentions have separate states.
- Every accepted question is checkpointed before inference in a new
  `results/dashboard_<run_id>.jsonl` journal. Completed engine results are
  appended immediately, followed by identity verification and a summary.
  Existing experiment files are never overwritten.
- The server retains the latest twenty runs in memory. Older journals stay on
  disk. After a server restart, old in-memory download URLs are unavailable;
  the saved JSONL journals remain readable. Closing a tab does not cancel an
  in-flight local comparison; stopping the server can interrupt its current arm.
- Gold labels are absent from catalog responses and controller inputs. They
  are consulted only after both systems return. The dropdown uses already
  exposed development questions. Future untouched evaluations must exclude
  any previously demonstrated IDs and matching custom question texts.

The HTTP service serves only its three UI assets and defined API routes.
Project files are not a public directory. Host/origin checks reject cross-origin
requests; POSTs require JSON. Dynamic answer/source/trace text uses DOM text
content rather than HTML. The interface includes labeled controls, keyboard
focus, live status text, reduced-motion support and keyboard-scrollable tables
and raw traces.

## Validation

All **207 automated tests passed**: the existing 191 engine/evaluation tests
plus sixteen dashboard tests covering real controllers with scripted model
transport, source and gold isolation, shared limits, seed ordering, model
identity changes, offline handling, concurrency, journal retention, input
validation, HTTP routes, same-origin enforcement and downloads. A fault-injection
test verifies that completion is published only after the summary is saved;
a simulated disk-full error instead yields a failed comparison with retained traces.

Four scenarios were run through the actual browser and installed model, with
the complete-evidence scenario repeated after the final server correction:
**five comparisons and ten real engine runs**.

| Browser case | RAIR | KAIR |
| --- | --- | --- |
| Complete two-hop example | Nerava, with source citations | Nerava, with source citations |
| Missing city evidence | Abstained | Abstained |
| Custom director / birthplace sources, seed 43 | Selvara, with source citations | Selvara, with source citations |
| Pondicherry Gramin Bank development question | Regional Rural Bank; EM/F1 1.0 | Regional Rural Bank; EM/F1 1.0 |

Browser checks verified source links, traces, editable/addable/removable sources,
run recovery after reload, the real JSON download, input locking, stale-result
clearing and absence of console errors. Desktop (1440 × 1000) and narrow
(390 × 844) viewport checks found no page-wide horizontal overflow. The benchmark
table scrolls inside its own container on narrow screens.

See [automated test results](../results/step6_tests.json),
[browser checks](../results/step6_browser_checks.json),
[combined validation](../results/step6_validation.json),
[source package](../results/step6_dashboard_source.zip),
[desktop screenshot](assets/dashboard_step6_desktop.png), and
[narrow-screen screenshot](assets/dashboard_step6_mobile.png).

## Limits and next boundary

This step implements the dashboard and connects the already tested engines.
It does not improve their reasoning or replace the Step 5 experiment. Answers
can still be wrong and evidence checks remain model-based. A failed individual
engine still appears alongside the other result; an environment or transport
failure can stop the overall comparison. No model retry or fabricated result
is substituted.

Public hosting, accounts, arbitrary PDF ingestion and external web retrieval
are outside this step. **Steps 6 and 7 are complete.** The final report, slides,
demo script, viva preparation and release checks are linked from the
[presentation handoff](PRESENTATION.md). Step 7 left both engines and the
dashboard unchanged, and rehearsed the complete and missing evidence cases again.
