# Step 9: four illustrative paired cases

These are post hoc illustrations selected by a fixed rule: the first sorted
question/seed in each observed full-only or removal-only exact-match group.
They are not a representative manual sample or proof of a single causal
mechanism. Evidence is preserved in `results/step9_ablations.jsonl` and the
extracted `results/step9_build/case_traces.json`.

## The gate can prevent distracting admissions

**Question:** Blinding Edge Pictures produced which 2000 film starring Bruce Willis?
**ID/seed:** `5a8b3af455429971feec467b`, 43.

Full RAIR answered **Unbreakable**, citing the production-company sentence
and the film's cast sentence. Its verifier rejected a candidate about
**The Whole Nine Yards** because the evidence did not connect that film to
Blinding Edge Pictures. The no-gate arm admitted that distracting candidate,
later queried the broader producer/actor/year combination and accumulated
another Whole Nine Yards claim. It ultimately abstained. The admission/path
difference is observable; the model did not record a separate explanation of
its final abstention, so no hidden rationale is asserted.

## The gate can also reject useful evidence

**Question:** Where does the Husband character reside in the 1847 book published as Ellis Bell?
**ID/seed:** `5a81967a55429926c1cdad44`, 43.

Both versions generated the same initial gaps. The second asks for a character
named “Husband.” Full RAIR repeatedly rejected the retrieved fact that Edgar
Linton resides at **Thrushcross Grange**, interpreting “Husband” as a literal
character name. It exhausted the retrieval budget and abstained. Without the
semantic gate, the same residence fact entered memory and the final answer was
Thrushcross Grange, matching gold and citing the original Edgar Linton sentence.
This illustrates a decomposition/verification mismatch and lost coverage, not
evidence that semantic checks should always be removed.

## Correct retrieval does not guarantee correct final comparison

**Question:** Who was born last, Dave Peverett or Jang Hyun-seung?
**ID/seed:** `5a7a633a55429941d65f2609`, 42.

Full RAIR gathered two separate birth-date gaps and answered **Jang Hyun-seung**.
The no-decomposition arm also retrieved the correct dates—1943 and 1989—but
answered **Dave Peverett**. Its original citations were valid; the final temporal
comparison was wrong. It stored the facts in the reverse order from full RAIR.
This is an observable synthesis failure with successful evidence retrieval;
the individual example cannot separate explicit gaps from changed knowledge
ordering or other downstream consequences of the removal.

## Decomposition can omit the actual requested relation

**Question:** The battle culminating the Runaway Scrape lasted how long?
**ID/seed:** `5a85f8665542994775f606ce`, 42.

Full RAIR generated only a battle-identity gap. Its extractor found both the
Battle of San Jacinto and its **18-minute** duration, but the verifier rejected
the duration as irrelevant to that identity gap. The controller marked all
planned gaps resolved, and final synthesis abstained because the admitted facts
did not supply the requested duration. The no-decomposition arm kept the whole
question as its gap, admitted the duration evidence and answered **18 minutes**
with the original Battle of San Jacinto sentence. This shows that “all gaps
resolved” is a controller state, not a guarantee that decomposition covers the
original question.

## What to say to the examiner

“The ablations reveal tradeoffs. Verification can reject distractions but also
discard useful evidence. Decomposition can guide retrieval but can omit the
requested relation. Valid citations do not guarantee correct synthesis. Our
20-question study does not establish that either component improves accuracy
overall, so a larger untouched confirmation study is still needed.”
