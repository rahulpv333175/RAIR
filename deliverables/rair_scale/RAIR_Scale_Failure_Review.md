# RAIR Scale Benchmark Failure Review & Residual Error Census

**Date:** 3 November 2026  
**Total Evaluated Runs:** 100 RAIR runs across 50 untouched questions  

---

## 1. Residual Outcome Breakdown

* **Exact Match (EM = 1.0):** 37/100 (37.0%)
* **Answered with Partial/Lexical Miss (0.0 < F1 < 1.0):** 21 runs
* **Abstained Runs (No Answer):** 25 runs (25.0%)
* **Execution Errors:** 0 runs (0.0%)

---

## 2. Granular Review of Residual Non-Exact Runs

| Question ID | Seed | RAIR Answer | Gold Answer | F1 | Stop Reason |
| :--- | :---: | :--- | :--- | :---: | :--- |
| `5a7b2208...` | 42 | "Save America's Treasures" | "historic buildings, arts, and published works" | 0.00 | `all_gaps_resolved` |
| `5a7b2208...` | 43 | "Save America's Treasures" | "historic buildings, arts, and published works" | 0.00 | `all_gaps_resolved` |
| `5ae4f967...` | 42 | "1828" | "1787" | 0.00 | `budget_exhausted` |
| `5ae4f967...` | 43 | "[abstained]" | "1787" | 0.00 | `budget_exhausted` |
| `5ade66f0...` | 42 | "[abstained]" | "Humberside Airport" | 0.00 | `budget_exhausted` |
| `5ade66f0...` | 43 | "[abstained]" | "Humberside Airport" | 0.00 | `budget_exhausted` |
| `5a7ca98f...` | 42 | "[abstained]" | "Christian" | 0.00 | `budget_exhausted` |
| `5a7ca98f...` | 43 | "Christianity" | "Christian" | 0.00 | `budget_exhausted` |
| `5ac2eec5...` | 42 | "Red" | "October 22, 2012" | 0.00 | `all_gaps_resolved` |
| `5ac2eec5...` | 43 | "2012" | "October 22, 2012" | 0.50 | `all_gaps_resolved` |
| `5ab30104...` | 42 | "[abstained]" | "director" | 0.00 | `budget_exhausted` |
| `5ab30104...` | 43 | "[abstained]" | "director" | 0.00 | `budget_exhausted` |
| `5ac3b40a...` | 42 | "[abstained]" | "Zenne" | 0.00 | `budget_exhausted` |
| `5ac3b40a...` | 43 | "Zenne valley" | "Zenne" | 0.67 | `all_gaps_resolved` |
| `5ac56023...` | 42 | "filmmaker" | "director" | 0.00 | `all_gaps_resolved` |
| `5ac56023...` | 43 | "filmmaker" | "director" | 0.00 | `all_gaps_resolved` |
| `5a7e04b0...` | 42 | "[abstained]" | "Vanarama" | 0.00 | `all_gaps_resolved` |
| `5a7e04b0...` | 43 | "[abstained]" | "Vanarama" | 0.00 | `all_gaps_resolved` |
| `5ab439f0...` | 42 | "Albany International Airport" | "Dane County Regional Airport" | 0.29 | `all_gaps_resolved` |
| `5ab439f0...` | 43 | "Albany International Airport" | "Dane County Regional Airport" | 0.29 | `budget_exhausted` |
| `5add596f...` | 42 | "the archetypal Gestapo Officer Herr Otto Flick" | "Captain Hans Geering" | 0.00 | `all_gaps_resolved` |
| `5add596f...` | 43 | "Herr Otto Flick" | "Captain Hans Geering" | 0.00 | `all_gaps_resolved` |
| `5ae1e9fd...` | 42 | "John F. Kelly" | "John Francis Kelly" | 0.67 | `all_gaps_resolved` |
| `5ae1e9fd...` | 43 | "John F. Kelly" | "John Francis Kelly" | 0.67 | `all_gaps_resolved` |
| `5ae28058...` | 42 | "[abstained]" | "1958" | 0.00 | `all_gaps_resolved` |
| `5ae28058...` | 43 | "[abstained]" | "1958" | 0.00 | `all_gaps_resolved` |
| `5ab6c637...` | 42 | "Germany" | "German" | 0.00 | `all_gaps_resolved` |
| `5ae4818f...` | 42 | "[abstained]" | "Piper" | 0.00 | `all_gaps_resolved` |
| `5ae4818f...` | 43 | "Pippa" | "Piper" | 0.00 | `all_gaps_resolved` |
| `5a8a43eb...` | 42 | "Marion" | "Marion, South Australia" | 0.50 | `all_gaps_resolved` |
| `5a8a43eb...` | 43 | "Marion" | "Marion, South Australia" | 0.50 | `all_gaps_resolved` |
| `5a7f5466...` | 42 | "[abstained]" | "Bow River and the Elbow River" | 0.00 | `budget_exhausted` |
| `5a7f5466...` | 43 | "[abstained]" | "Bow River and the Elbow River" | 0.00 | `budget_exhausted` |
| `5a7e0563...` | 42 | "[abstained]" | "January 2016" | 0.00 | `budget_exhausted` |
| `5a7e0563...` | 43 | "[abstained]" | "January 2016" | 0.00 | `all_gaps_resolved` |
| `5a732056...` | 42 | "Jerry Glanville" | "Keith Bostic" | 0.00 | `all_gaps_resolved` |
| `5a732056...` | 43 | "Jerry Glanville" | "Keith Bostic" | 0.00 | `all_gaps_resolved` |
| `5a89fa26...` | 43 | "[abstained]" | "yes" | 0.00 | `budget_exhausted` |
| `5a865d11...` | 42 | "Fort Snelling" | "Fort Saint Anthony" | 0.40 | `all_gaps_resolved` |
| `5a865d11...` | 43 | "[abstained]" | "Fort Saint Anthony" | 0.00 | `budget_exhausted` |
| `5a8bf083...` | 42 | "Scrappy" | "northern mockingbird" | 0.00 | `all_gaps_resolved` |
| `5a8bf083...` | 43 | "mockingbird" | "northern mockingbird" | 0.67 | `all_gaps_resolved` |
| `5a74d4f3...` | 42 | "Charles J. Guiteau" | "Charles Guiteau" | 0.80 | `all_gaps_resolved` |
| `5a74d4f3...` | 43 | "[abstained]" | "Charles Guiteau" | 0.00 | `all_gaps_resolved` |
| `5ae62249...` | 42 | "Comedy Central sketch-comedy" | "Comedy" | 0.50 | `all_gaps_resolved` |
| `5a76394c...` | 43 | "[abstained]" | "1968" | 0.00 | `all_gaps_resolved` |
| `5ab8627f...` | 42 | "Michael Schumacher" | "Corinna and seven-time Formula One World Champion Michael Schumacher" | 0.36 | `budget_exhausted` |
| `5ab8627f...` | 43 | "Michael Schumacher" | "Corinna and seven-time Formula One World Champion Michael Schumacher" | 0.36 | `all_gaps_resolved` |
| `5abf8cc3...` | 42 | "21 August 1986" | "born 21 August 1986" | 0.86 | `all_gaps_resolved` |
| `5abf8cc3...` | 43 | "[abstained]" | "born 21 August 1986" | 0.00 | `budget_exhausted` |
| `5a7f669a...` | 42 | "[abstained]" | "James Stenbeck" | 0.00 | `repeated_query` |
| `5ae7281c...` | 42 | "[abstained]" | "spiritual" | 0.00 | `all_gaps_resolved` |
| `5ae7281c...` | 43 | "The Simpsons' seventh season contains an episode titled "Bart Sells His Soul"." | "spiritual" | 0.00 | `all_gaps_resolved` |
| `5abecdf4...` | 42 | "Polk County" | "Polk" | 0.67 | `all_gaps_resolved` |
| `5abecdf4...` | 43 | "Polk County" | "Polk" | 0.67 | `budget_exhausted` |
| `5a8f791c...` | 42 | "touring" | "death metal band" | 0.00 | `budget_exhausted` |
| `5a8f791c...` | 43 | "touring" | "death metal band" | 0.00 | `all_gaps_resolved` |
| `5a79ea43...` | 42 | "J. Edward Snyder" | "Rear Adm. J. Edward Snyder" | 0.75 | `all_gaps_resolved` |
| `5a79ea43...` | 43 | "J. Edward Snyder" | "Rear Adm. J. Edward Snyder" | 0.75 | `all_gaps_resolved` |
| `5ab9d021...` | 42 | "Subway restaurants" | "Subway" | 0.67 | `all_gaps_resolved` |
| `5ab9d021...` | 43 | "Subway restaurants" | "Subway" | 0.67 | `all_gaps_resolved` |
| `5ae13c51...` | 42 | "[abstained]" | "Norwegian Cruise Line Holdings Ltd." | 0.00 | `budget_exhausted` |
| `5ae13c51...` | 43 | "[abstained]" | "Norwegian Cruise Line Holdings Ltd." | 0.00 | `budget_exhausted` |
