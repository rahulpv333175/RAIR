# Remaining failure review

This is post hoc descriptive analysis of the unchanged Step 5 journal. No model tuning, inference rerun, changed gold labels or new semantic scoring was performed.

The census covers all 600 runs. The twelve cases below were selected purposefully to illustrate different trace mechanisms, not randomly sampled. Their categories can overlap and do not estimate population prevalence.

| Outcome out of 200 | RAIR | KAIR |
| --- | ---: | ---: |
| Exact match | 81 | 72 |
| Answered nonexact | 58 | 75 |
| Abstained | 61 | 50 |
| Whole question errors | 0 | 3 |

RAIR abstentions: 39 budget stops, 15 repeated-query stops and 7 after all planned gaps were marked resolved. Of 61 abstentions, 29 had no accepted facts, 32 had some, and 42 had retrieved every gold support title. Retrieved titles do not establish useful sentence selection or sound reasoning.

KAIR recorded 25 agent error events, but only three whole-question NoValidProposal errors. Agent events are not additional question outcomes.

## Inspected examples

### 1 Answer span mismatch

System **RAIR**, question `5abbfbcf55429965836003cf`, base seed **42**.

Question: James Leal Greenleaf worked on a monument located where? 

Gold: National Mall

Recorded answer: on the western end of the National Mall in Washington, D.C.

Status: answered. Stop: all_gaps_resolved. EM 0.0, token F1 0.364.

Gold is National Mall. The answer includes its western end and Washington DC. The cited location supports that longer span, so a strict EM failure does not establish a wholly wrong location. F2 also illustrates a verifier false positive: its attached Greenleaf sentence does not state United States.

### 2 Number wording mismatch

System **RAIR**, question `5a84524a554299123d8c2203`, base seed **42**.

Question: How many books are in the text composed by the founder Nyaya school of Hindu philosophy and is used in the development of Indian logic?

Gold: five books

Recorded answer: 5

Status: answered. Stop: all_gaps_resolved. EM 0.0, token F1 0.000.

Gold is five books, prediction is 5. The original source explicitly says five books. EM and token F1 are both zero because normalization does not map digits to words. Keep the frozen score unchanged.

### 3 Name alias mismatch

System **RAIR**, question `5a750de95542993748c897ac`, base seed **42**.

Question: What Jurassic Park star was also in the Rainbow Warrior?

Gold: Nigel John Dermot Neill

Recorded answer: Sam Neill

Status: answered. Stop: all_gaps_resolved. EM 0.0, token F1 0.333.

Prediction Sam Neill and gold Nigel John Dermot Neill name the same person within the supplied Sam Neill document. Both film links were found. This is an illustrative alias limitation, not permission to retrospectively rescore.

### 4 Decomposition misses requested relation

System **RAIR**, question `5abe953b5542993f32c2a170`, base seed **42**.

Question: what is one of the stars of  The Newcomers known for

Gold: superhero roles as the Marvel Comics

Recorded answer: Christopher McCoy

Status: answered. Stop: all_gaps_resolved. EM 0.0, token F1 0.000.

The only gap asks for cast members, omitting what a star is known for. It resolves and returns Christopher McCoy instead of the requested superhero roles. A valid source ID and resolved gap do not prove the original question was answered.

### 5 Bridge fact rejected

System **RAIR**, question `5a8efef05542997ba9cb3178`, base seed **42**.

Question: In what city did Jack J. Stephans coach from 1979 to 1980?

Gold: New York City

Recorded answer: [abstained]

Status: abstained. Stop: all_gaps_resolved. EM 0.0, token F1 0.000.

The verifier rejects the supported coaching-at-Fordham link because it is not a city. Only Fordham is in New York City reaches memory. The final synthesizer abstains without the coaching link even though the planner reports all gaps resolved.

### 6 Useful partial facts rejected

System **RAIR**, question `5a7183575542994082a3e85e`, base seed **42**.

Question: Who was the architect of a Dutch museum dedicated to the arts and history in Amsterdam, located at the Museum Square?

Gold: Petrus Josephus Hubertus (Pierre) Cuypers

Recorded answer: [abstained]

Status: abstained. Stop: budget_exhausted. EM 0.0, token F1 0.000.

Across four retrievals the verifier rejects the arts/history and Museum Square facts separately for not repeating the entire requested description. Both gold support titles were retrieved, but no facts entered memory. Budget exhaustion follows.

### 7 Second entity retrieval fails

System **RAIR**, question `5a79cd665542994bb94570bf`, base seed **42**.

Question: Who was born first, Teru or Mike Shinoda?

Gold: Teruhiko

Recorded answer: [abstained]

Status: abstained. Stop: repeated_query. EM 0.0, token F1 0.000.

Only Teru's birth date enters memory. Mike Shinoda's support title is not retrieved in this run. Queries stall and the controller abstains. More permissive synthesis alone would not supply a sourced second date.

### 8 Negative evidence rejected and unsafe synthesis

System **RAIR**, question `5adcfb5f5542990d50227d81`, base seed **43**.

Question: Are Grant Nicholas and Danny Shirley both American singers?

Gold: no

Recorded answer: yes

Status: answered. Stop: budget_exhausted. EM 0.0, token F1 0.000.

Welsh is repeatedly rejected as irrelevant to deciding whether Grant Nicholas is American. Only Danny Shirley's American nationality enters memory. The final yes incorrectly generalizes from one person to both. Both negative-evidence handling and final completeness need future work.

### 9 Shared number wording mismatch

System **KAIR**, question `5a84524a554299123d8c2203`, base seed **42**.

Question: How many books are in the text composed by the founder Nyaya school of Hindu philosophy and is used in the development of Indian logic?

Gold: five books

Recorded answer: 5

Status: answered. Stop: agent_complete. EM 0.0, token F1 0.000.

KAIR also returns 5 against five books and receives EM zero and F1 zero. The same metric limitation applies to both systems.

### 10 Missing second date and verifier false positive

System **KAIR**, question `5a79cd665542994bb94570bf`, base seed **42**.

Question: Who was born first, Teru or Mike Shinoda?

Gold: Teruhiko

Recorded answer: [abstained]

Status: abstained. Stop: budget_exhausted. EM 0.0, token F1 0.000.

The selected A2 has only Teru's date and requires Mike Shinoda's date, so it abstains at the budget. A1 also accepted a comparative before claim with only Teru's source attached, illustrating that its checker can admit unsupported reasoning.

### 11 Both proposals fail structural validation

System **KAIR**, question `5ae60d36554299546bf8303e`, base seed **43**.

Question: When did Belgium racer Stoffel Vandoorne win the Monaco GP2 Series round?

Gold: 22 and 23 May 2015

Recorded answer: [abstained]

Status: error. Stop: all_agents_failed. EM 0.0, token F1 0.000.

Both agents fail filtering because one document appears more than once in selections. No initialized healthy proposal remains, causing the question-level NoValidProposal error. No repair or retry is silently applied.

### 12 Malformed source identifiers retire agents

System **KAIR**, question `5a800ddd5542992097ad2fd0`, base seed **42**.

Question: what 6-story building was listed on the National Register of Historic Places in 1980?

Gold: Worcester Cold Storage and Warehouse Co. fire

Recorded answer: [abstained]

Status: error. Stop: all_agents_failed. EM 0.0, token F1 0.000.

Both agents use a malformed document ID in update evidence. Strict validators reject the proposals. This accounts for one of the three question-level errors, rather than an abstention.

## Evidence and next action

Frozen raw journal SHA256: `4104fadcc70d71eaf672b607f09db77b8307db38c0697860d2388296b6410b18`.
Frozen summary SHA256: `05b36432e34d340d2011e9f57643be82ea16671bf31a34bca6ddf8ad021ce409`.

The full original sources, state, rounds or agents are retained in results/step7_build/failure_analysis.json. The CSV is a complete outcome census, not a manually relabeled correctness dataset.

Prioritize bridge and negative evidence handling, relation-complete decomposition, final checks for every compared entity, and constrained KAIR source selections. Develop on exposed questions and freeze a new untouched cohort for evaluation. Preserve this benchmark as historical evidence.
