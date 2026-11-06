# RAIR Held-Out Test Benchmark Failure Review & Residual Error Census

**Date:** 4 November 2026  
**Total Evaluated Runs:** 100 RAIR runs across 50 fresh untouched questions  

---

## 1. Residual Outcome Breakdown

* **Exact Match (EM = 1.0):** 56/100 (56.0%)
* **Answered with Partial/Lexical Miss (0.0 < F1 < 1.0):** 17 runs
* **Abstained Runs (No Answer):** 17 runs (17.0%)
* **Execution Errors:** 0 runs (0.0%)

---

## 2. Granular Review of Residual Non-Exact Runs

| Question ID | Seed | RAIR Answer | Gold Answer | F1 | Stop Reason |
| :--- | :---: | :--- | :--- | :---: | :--- |
| `5adce4f6...` | 42 | "Centers for Medicare & Medicaid Services" | "Centers for Medicare and Medicaid Services" | 0.91 | `all_gaps_resolved` |
| `5adce4f6...` | 43 | "[abstained]" | "Centers for Medicare and Medicaid Services" | 0.00 | `budget_exhausted` |
| `5a77aa86...` | 42 | "[abstained]" | "Emilia Fox" | 0.00 | `budget_exhausted` |
| `5a839c8b...` | 42 | "Attorney General" | "Lord Chancellor of England" | 0.00 | `all_gaps_resolved` |
| `5a839c8b...` | 43 | "Attorney General" | "Lord Chancellor of England" | 0.00 | `all_gaps_resolved` |
| `5ab2e3a3...` | 42 | "having a simple iron boar crest" | "A simple iron boar crest" | 0.89 | `all_gaps_resolved` |
| `5ade0a27...` | 42 | "Flatbush Zombies" | "Flatbush section of Brooklyn, New York City" | 0.22 | `all_gaps_resolved` |
| `5ade0a27...` | 43 | "Flatbush Zombies" | "Flatbush section of Brooklyn, New York City" | 0.22 | `all_gaps_resolved` |
| `5a721a76...` | 43 | "Jennifer Ventimilia" | "Christopher Rich" | 0.00 | `all_gaps_resolved` |
| `5adce88b...` | 42 | "[abstained]" | "320 years" | 0.00 | `budget_exhausted` |
| `5a7a11c8...` | 42 | "Woon Swee Oan's novel series" | ""The Four Great Constables"" | 0.00 | `all_gaps_resolved` |
| `5a7a11c8...` | 43 | "Si Da Ming Bu" | ""The Four Great Constables"" | 0.00 | `all_gaps_resolved` |
| `5a81d051...` | 42 | "Flamingo Las Vegas" | "Las Vegas Strip in Paradise, Nevada" | 0.44 | `all_gaps_resolved` |
| `5a81d051...` | 43 | "Paradise, Nevada" | "Las Vegas Strip in Paradise, Nevada" | 0.50 | `all_gaps_resolved` |
| `5a872088...` | 42 | "Siwi" | "Berber" | 0.00 | `budget_exhausted` |
| `5a872088...` | 43 | "Siwi" | "Berber" | 0.00 | `all_gaps_resolved` |
| `5a7bacf2...` | 42 | "[abstained]" | "North Carolina" | 0.00 | `budget_exhausted` |
| `5a7bacf2...` | 43 | "[abstained]" | "North Carolina" | 0.00 | `budget_exhausted` |
| `5a7e2365...` | 42 | "[abstained]" | "566" | 0.00 | `all_gaps_resolved` |
| `5a7e2365...` | 43 | "[abstained]" | "566" | 0.00 | `all_gaps_resolved` |
| `5a8a3919...` | 42 | "eBay" | "eBay Inc." | 0.67 | `all_gaps_resolved` |
| `5a8a3919...` | 43 | "eBay" | "eBay Inc." | 0.67 | `all_gaps_resolved` |
| `5ac15de5...` | 42 | "[abstained]" | "no" | 0.00 | `budget_exhausted` |
| `5a8c6bd5...` | 42 | "African" | "Afro-Russian" | 0.00 | `all_gaps_resolved` |
| `5ade908b...` | 42 | "the DTM and its successor — the International Touring Car Championship" | "DTM" | 0.20 | `all_gaps_resolved` |
| `5ade908b...` | 43 | "touring cars" | "DTM" | 0.00 | `all_gaps_resolved` |
| `5a71166d...` | 42 | "The Battle of Manila" | "Battle of Guam" | 0.67 | `all_gaps_resolved` |
| `5a71166d...` | 43 | "The Battle of Manila" | "Battle of Guam" | 0.67 | `all_gaps_resolved` |
| `5a847e80...` | 42 | "[abstained]" | "Skipton Castle" | 0.00 | `budget_exhausted` |
| `5a7136e2...` | 42 | "Bosco Wong" | "Bosco Wong Chung-chak" | 0.80 | `all_gaps_resolved` |
| `5a7136e2...` | 43 | "Bosco Wong" | "Bosco Wong Chung-chak" | 0.80 | `all_gaps_resolved` |
| `5ae50c34...` | 42 | "Bambi, a Life in the Woods" | "Bambi: Eine Lebensgeschichte aus dem Walde" | 0.20 | `all_gaps_resolved` |
| `5ae50c34...` | 43 | "Bambi, a Life in the Woods" | "Bambi: Eine Lebensgeschichte aus dem Walde" | 0.20 | `all_gaps_resolved` |
| `5abbc967...` | 42 | "[abstained]" | "three million copies worldwide" | 0.00 | `budget_exhausted` |
| `5abbc967...` | 43 | "[abstained]" | "three million copies worldwide" | 0.00 | `budget_exhausted` |
| `5a835a26...` | 42 | "film" | "theater and film" | 0.50 | `all_gaps_resolved` |
| `5a835a26...` | 43 | "film" | "theater and film" | 0.50 | `all_gaps_resolved` |
| `5a80a1b2...` | 43 | "[abstained]" | "no" | 0.00 | `budget_exhausted` |
| `5a8ec320...` | 42 | "[abstained]" | "yes" | 0.00 | `budget_exhausted` |
| `5a8ec320...` | 43 | "[abstained]" | "yes" | 0.00 | `budget_exhausted` |
| `5ab416a2...` | 43 | "Danish West Indies" | "Caribbean" | 0.00 | `all_gaps_resolved` |
| `5ab52a25...` | 42 | "[abstained]" | "Sochi, Russia" | 0.00 | `budget_exhausted` |
| `5ab52a25...` | 43 | "[abstained]" | "Sochi, Russia" | 0.00 | `budget_exhausted` |
| `5ae14658...` | 43 | "[abstained]" | "New York Yankees" | 0.00 | `budget_exhausted` |
