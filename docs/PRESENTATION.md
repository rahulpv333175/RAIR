# Step 7 final report and teacher presentation

**Later update:** the [Step 9 presentation copy](../deliverables/step9/RAIR_KAIR_Presentation_Step9.pptx)
preserves these 12 historical slides and adds three measured component-study
slides. See [Step 9 findings](../deliverables/step9/Step9_Findings.md) and
[paired failure examples](../deliverables/step9/Step9_Failure_Review.md).
The original Step 7 package below remains unchanged.

This page and its teacher package describe the 27 October release and frozen
Step 5 experiment. A subsequent [30 October maintenance review](PROJECT_REVIEW.md)
corrected KAIR source handling without changing those artifacts or scores.

The project is complete as a local research prototype and teacher demonstration.
Step 7 prepared the submission materials, analyzed saved failures and verified
the release. It introduced no inference changes and did not tune or replace the
frozen benchmark.

## Deliverables

Download the [complete teacher package](../deliverables/RAIR_KAIR_Teacher_Package.zip),
or use the files directly:

| Material | Editable file | PDF |
| --- | --- | --- |
| Final report, 12 pages | [Word](../deliverables/step7/RAIR_KAIR_Final_Report.docx) | [PDF](../deliverables/step7/RAIR_KAIR_Final_Report.pdf) |
| Presentation, 12 slides with notes | [PowerPoint](../deliverables/step7/RAIR_KAIR_Presentation_Final.pptx) | [PDF](../deliverables/step7/RAIR_KAIR_Presentation_Final.pdf) |
| Demo script, 3 pages | [Word](../deliverables/step7/RAIR_KAIR_Demo_Script.docx) | [PDF](../deliverables/step7/RAIR_KAIR_Demo_Script.pdf) |
| Viva preparation, 30 questions, 6 pages | [Word](../deliverables/step7/RAIR_KAIR_Viva_Questions.docx) | [PDF](../deliverables/step7/RAIR_KAIR_Viva_Questions.pdf) |

The package also includes a [failure review](../deliverables/step7/Remaining_Failure_Review.md),
a [600-run outcome census](../deliverables/step7/Benchmark_Outcome_Census.csv),
verification records and [presentation instructions](../deliverables/step7/START_HERE.md).
Student or team names, college, guide and other personal fields are deliberately
blank at the user's request. Fill those fields and save updated PDFs before class.

## Conclusions and remaining failures

Updated RAIR scored 40.5% exact match, the earlier-core control 18.5%, and KAIR
36.0%, each over all 200 planned runs. The primary RAIR gain over the earlier
core was 22.0 percentage points, with a question-cluster 95% interval of
15.0 to 29.5. All three arms used the same current final-answer policy.
RAIR minus KAIR was 4.5 points with an interval of -3.0 to +12.0, so superiority
over KAIR is not established.

RAIR's 119 nonexact outcomes consist of 58 answered nonexact runs and 61
abstentions. The 58 split into 31 zero-token-overlap and 27 partial-overlap
answers, which are lexical categories rather than semantic correctness labels.
The abstentions split into 39 budget stops, 15 repeated-query stops and seven
after all planned gaps were marked resolved. Twenty-nine had no admitted facts,
32 had some facts, and 42 had retrieved all gold support titles. That does not
prove the necessary sentences or complete reasoning chain reached the answer.

KAIR produced 75 answered nonexact runs, 50 abstentions and three question errors.
Its 25 agent error events are recorded separately; healthy competitors sometimes
continued. The three whole-question errors were NoValidProposal.

The manual review purposefully selected eight RAIR and four KAIR question-seed
examples. It found missed relations in decomposition, rejected bridge and
negative evidence, missing second entities, incomplete final reasoning, checker
false positives and malformed KAIR evidence. It also found wording, number and
name-alias mismatches. These cases illustrate mechanisms and do not estimate
their prevalence. No frozen scores were changed to reward semantic aliases.

## Final verification

- A fresh full suite passed **207 tests**, with zero failures and zero errors.
- The offline audit checked all **600 records**, their input fingerprints,
  source citations, scores, actual call budgets and scheduled question-seed-arm
  entries, then reproduced both exact-match contrast intervals.
- Engine hashes match the Step 5 current-source verification. Dashboard hashes
  match Step 6. Frozen dataset, manifest, summary and journal hashes are retained.
- Two fresh browser rehearsals exercised four actual engine runs. With complete
  evidence both returned **Nerava**. With the city evidence removed both
  **abstained**. Model identity remained stable and browser warning/error logs
  were empty. The earlier four Step 6 scenarios remain separately documented.
- All **21 document pages** were exported through installed Word 16.0,
  rasterized and visually reviewed. All **12 slides** were rendered and inspected
  through installed PowerPoint 16.0. Native chart data match the source scores;
  chart editing, resizing, saving and reopening passed in a private test copy.
- The screenshot is embedded in the final deck. Native review caught and fixed
  an earlier path-only image reference before handoff. No external media files
  are needed to display the final deck.
- Package contents and file hashes were checked after ZIP creation.

See [release verification](../results/step7_verification.json). Audit and artifact
builder sources are retained in `results/step7_build/`. The packaged DOCX renderer
could not use LibreOffice on this host, so its conversion callback used PDFs
exported by installed Word. The bundled slide PDF exporter lacked a font module;
installed PowerPoint supplied the final PDF and native previews. No dependency
was installed or managed runtime modified.

## What remains before class

Fill personal fields and rehearse the [demo script](../deliverables/step7/RAIR_KAIR_Demo_Script.pdf).
Keep Ollama and the local dashboard running, and keep the PDFs available as a
fallback. The bundle does not contain model weights, the Python environment or
the full dataset. Other presentation applications and another computer were not
tested. IEEE publisher access was blocked during the final link check; the
project's earlier journal-text verification and algorithm mapping are retained.

Further engine improvements, larger samples, additional models and component
ablations are future research. Any tuning based on the now-exposed final cohort
must be followed by a newly frozen untouched evaluation before new claims.
