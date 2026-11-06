# Project review and next research steps

Review date: 30 October 2026.

The seven planned steps are complete as a local research prototype: both
engines, common evaluation, two benchmark stages, dashboard, final report,
slides, demo script and viva preparation exist. Answer reliability still needs
research. A completed implementation is different from a system that always
produces a supported correct answer.

## Bugs corrected in this review

KAIR's final context filter previously rejected multiple valid selections from
the same source document. Candidate extraction already had a safe way to merge
such selections. The filter now uses that same path: validate every original
document and sentence first, then combine indices and reconstruct exact text.
An unavailable sentence or unknown document still fails validation; there is
no guessed source, rewritten evidence or hidden model retry.

KAIR's update and filter generations now receive runtime source schemas limited
to the available document IDs and that particular document's available sentence
indices. An empty context permits no candidates or selected sources. This closes
an unconstrained source-generation contract while retaining independent parser
checks. Public payload shapes, private knowledge, competition selection and
budgets are preserved. No dependency was added.

Three focused regression tests cover valid repeated-source selection, bounded
generation choices and rejection of unavailable sentences in a repeated source.
The existing empty-context test also checks that generation permits no source
claims. The scripted transport fixture understands the new constrained schema.

## Problems that remain

The live before-fix role probes reproduced rejection of useful bridge facts,
rejection of negative evidence and an unsafe positive comparison when only one
person's attribute was known. Stronger prompt wording did not reliably solve
these cases. A neutral verifier field-name experiment helped bridge admission
in its small probe but still rejected negative evidence and sometimes marked a
city gap complete with an institution alone. A missing-information-first answer
experiment still answered the incomplete comparison incorrectly.

The attempted prompt changes were discarded after end-to-end diagnostics
continued to produce incorrect answers. Final RAIR prompts and the common
answer synthesizer are restored exactly to the pre-review version. The retained
production change concerns KAIR source handling only. Prompt-only trials are
saved separately and must not be reported as successful fixes or new accuracy
measurements.

The tests and diagnostics are in `results/post_presentation_20261030/`.
The final verification record lists the source hashes, unchanged benchmark
hashes, matched diagnostic outcomes and remaining failures. The live runtime is
Ollama 0.40.13 with the same model digest as the original experiment; the frozen
benchmark used Ollama 0.40.6. Do not attribute changes from the old benchmark to
one patch on the basis of these selected cases.

Final checks passed all **210 automated tests**. Four diagnostic pairs exercised
eight actual engine runs with the same input pools, model identity, generation
settings and limits of four retrievals and eighteen model calls per engine:

| Diagnostic | RAIR | KAIR |
| --- | --- | --- |
| Complete fictional chain | Nerava with both sources | Nerava with both sources |
| Missing city evidence | Abstained | Abstained |
| Negative nationality comparison | Abstained despite a gold answer of no | Answered no; one competitor hit its output-token limit |
| Previously failing KAIR source-validation case | May 22 2015, partial reference overlap | May 22 2015, partial reference overlap; no source-validation error |

All eight runs completed without a whole-question execution error. The KAIR
token-limit event remains in its trace and resource totals; it was not silently
retried or removed. Both date answers receive partial F1 under the existing
scorer, not an exact match. These cases verify execution and expose residual
answer-quality limits, rather than proving a general accuracy gain. The
separate KAIR standalone smoke check also passed complete and missing evidence.

## Difference between RAIR and the implemented KAIR baseline

| Aspect | RAIR | Competitive KAIR baseline |
| --- | --- | --- |
| Organization | A controller assigns specialized responsibilities | Each competing agent attempts the entire question |
| Memory | Accepted facts, gaps and query history in one shared state | Private knowledge and requirements per agent |
| Planning | Initial gap dependency graph and actionable-gap scheduling | Each agent revises its own unresolved requirements |
| Verification | Separate candidate decisions control shared fact admission and gap resolution | Each agent checks its proposed knowledge updates before committing them |
| Information sharing | Every role can use the shared accepted facts | The selected proposal supplies original source context; private facts are not merged |
| Final answer | Common final synthesizer | The same common final synthesizer |
| Execution | Serial local model requests | Serial local adaptation with rotated agent order |

Both use the same underlying Qwen model, BM25 implementation, supplied source
pools and comparison caps. Roles are prompt responsibilities, not separately
trained language models. KAIR already has fact checking; RAIR cannot claim that
verification is absent from its baseline.

The KAIR paper also describes collaborative shared knowledge and specialized
gap assignment. Those ideas alone are not original RAIR contributions. See the
[primary preprint section on multi-agent extension](https://arxiv.org/html/2503.13275v2#S3.SS3)
and the journal-specific mapping in [KAIR.md](KAIR.md). This project is best
positioned as an implemented refinement and controlled evaluation of explicit
role responsibilities, fact admission and gap scheduling, rather than a claim
to have invented collaborative iterative retrieval.

The earlier final benchmark supports a 22.0-point gain over the earlier RAIR
core with a shared current final policy. RAIR's 40.5% exact match versus KAIR's
36.0% is numerically higher, but the paired interval includes zero. Superiority
over KAIR is not established. These are historical Step 5 results and do not
measure this source-handling revision.

## Recommended major next steps

1. **Answer faithfulness and completeness.** Build a separately testable audit
   of the original question, all required entities, supporting facts and final
   answer. Reject answers with a missing link or unresolved contradiction while
   retaining the rejected answer and reason in the trace. Test positive cases,
   missing evidence, negative evidence, bridge facts and deliberate unsupported
   claims. A second LLM judgment is not automatically reliable; evaluate it
   independently and charge its calls to an explicitly revised common budget
   for both systems. Report accuracy, unsupported answers and coverage together.
2. **Component experiments and a new untouched evaluation.** Compare the full
   workflow with controlled versions that remove verification or explicit gap
   planning, alongside a simple retrieval baseline and competitive KAIR. Use
   prospectively defined controls, enough repeated seeds, matched resource
   ceilings and actual token accounting. This answers which component helps,
   which costs it adds, and whether improvements generalize. Use exposed cases
   for development; freeze and evaluate a new question cohort for final claims.
3. **A practical document assistant.** Add PDF or text upload with stable
   document and page identifiers, run both engines on the same resulting
   corpus, and show clickable original-page citations. A college handbook or
   technical manual provides a concrete demonstration use case. Keep ingestion
   independent of the engine so retrieval and model behavior can still be
   compared fairly. Scanned documents would require an explicitly tested OCR
   path.
4. **A visual evidence chain.** Show the actual entity-to-entity links, their
   admitted claims, source sentences and missing links alongside the existing
   traces. This improves explanation during the demonstration. It does not by
   itself improve accuracy or prove that a model-accepted link is true.

The strongest next research milestone is the first item followed by a fresh
fair evaluation. Component experiments make the contribution defensible to a
teacher. Document upload adds practical value after the answer-quality checks
have been established.

## Presentation claim

"We investigate whether explicit role separation, controlled fact admission
and gap scheduling improve inspectable multi-hop question answering under
matched resource limits. We implement a competitive KAIR baseline, retain
failures in evaluation, and show both numerical results and uncertainty."

The existing teacher package remains the historical 27 October submission.
Its frozen results and files were preserved. Present the maintenance checks
separately; do not replace the reported scores with outcomes from a small,
purposefully selected diagnostic set.
