# RAIR: Role-Aware Information Routing for Multi-Hop Question Answering

[![Tests](https://img.shields.io/badge/Tests-246%20Passing-brightgreen.svg)](#running-the-test-suite)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Model](https://img.shields.io/badge/LLM-Local%20Ollama%20(Qwen%204B)-orange.svg)](https://ollama.ai/)
[![Benchmark](https://img.shields.io/badge/Benchmark-HotpotQA-purple.svg)](https://hotpotqa.github.io/)
[![Zero External Dependencies](https://img.shields.io/badge/Server-Zero%20Dependency%20HTTP-success.svg)](#1-open-the-interactive-web-dashboard-recommended)

> **Role-Aware Information Routing (RAIR)** is a local, reproducible research framework comparing structured, role-specialized multi-agent reasoning against competitive multi-agent debate (**KAIR**) on complex multi-hop question answering.

---

## Table of Contents
1. [What is this Project? (Explain Like I'm 5)](#what-is-this-project-explain-like-im-5)
2. [The Core Problem: Why Multi-Hop Questions Break Standard AI](#the-core-problem-why-multi-hop-questions-break-standard-ai)
3. [How RAIR Works: The 5-Specialist Assembly Line](#how-rair-works-the-5-specialist-assembly-line)
4. [RAIR vs. Competitive KAIR: Key Results](#rair-vs-competitive-kair-key-results)
5. [What is Inside the Project? (Project Tour)](#what-is-inside-the-project-project-tour)
6. [How to Run the Project (Quickstart Guide)](#how-to-run-the-project-quickstart-guide)
   - [Prerequisites](#prerequisites)
   - [1. Launch the Interactive Web Dashboard](#1-launch-the-interactive-web-dashboard-recommended)
   - [2. Run Automated Tests](#2-run-the-automated-test-suite)
   - [3. Run Head-to-Head Terminal Comparisons](#3-run-head-to-head-terminal-comparisons)
7. [What to See in the Interactive Dashboard](#what-to-see-in-the-interactive-dashboard)
8. [Research Deliverables & Report](#research-deliverables--report)
9. [Authors & Academic Affiliation](#authors--academic-affiliation)

---

## What is this Project? (Explain Like I'm 5)

Imagine you ask a computer this riddle:
> *"What year was the author of the novel 'The Glass Orchard' born?"*

- **A standard AI search** will look for `"What year was the author born"` and fail, because it does not even know who wrote the book yet!
- To solve this riddle, the AI needs to take **two steps (two "hops")**:
  1. **Step 1:** Discover who wrote *The Glass Orchard* (Answer: *Mira Solen*).
  2. **Step 2:** Search for when *Mira Solen* was born (Answer: *1958*).

### How other systems try to solve it (Competitive Debate / KAIR)
Standard multi-agent systems launch two separate AI agents that compete and debate each other. They each take separate private notes, make duplicate searches, argue back and forth, and often hallucinate plausible-sounding guesses or freeze in unhandled communication crashes.

### How RAIR solves it (Assembly Line of Specialists)
Instead of letting agents argue chaotically, **RAIR** organizes the task into an assembly line of **5 specialized roles** working together on a single, shared, verified blackboard:
1. **The Decomposer:** Breaks down the big riddle into ordered sub-questions (Information Gaps).
2. **The Search Planner:** Writes smart, laser-targeted search queries (avoiding repeated searches).
3. **The Document Retriever:** Finds the top matching source paragraphs using local BM25 ranking.
4. **The Fact Extractor:** Finds candidate facts and links them to exact sentence numbers.
5. **The Verifier Checkpoint:** A strict truth gatekeeper. It tests every fact against a 5-point contract. Only 100% verified facts are allowed onto the shared blackboard!
6. **The Synthesizer:** Reads only the verified facts and writes the final, grounded answer with citations.

---

## The Core Problem: Why Multi-Hop Questions Break Standard AI

In scientific multi-hop question answering, competitive debate architectures suffer from **four fatal failure modes**:

```
Competitive Debate Pathologies (KAIR):
[User Question]
       │
   ┌───┴───┐
   ▼       ▼
[Agent 1] [Agent 2]  <- Private scratchpads: duplicate queries, wasted tokens
   │       │
   └───┬───┘
       ▼
 [Voting / Debate]    <- Ungrounded consensus hallucinations, 10 fatal agent crashes!
```

1. **Bridge Entity Disconnection:** Competing agents find the author (*Mira Solen*), but stop early and forget to search for her birth year.
2. **Query Collisions & Wasted Budgets:** Both agents independently make identical search queries, burning through the token limit without discovering new evidence.
3. **Hallucination Consensus:** If neither agent finds the second fact, they agree on a fluent, made-up guess.
4. **Communication Crashes:** Asynchronous turn-taking and proposal conflicts cause fatal software exceptions (10 crashes observed in KAIR).

---

## How RAIR Works: The 5-Specialist Assembly Line

RAIR replaces chaotic debate with deterministic, role-specialized coordination:

```
[User Multi-Hop Question Q]
            │
            ▼
   1. Role: Decomposer           <-- Maps question into a dependency graph of sub-gaps
            │
            ▼
   2. Role: Search Planner        <-- Formulates targeted queries with negative constraints
            │
            ▼
   Local BM25 Retriever          <-- Fetches top-3 matching documents from local pool
            │
            ▼
   3. Role: Fact Extractor       <-- Extracts candidate facts with exact sentence IDs
            │
            ▼
   4. Role: Verifier Checkpoint   <-- Strict 5-Point Boolean Gate:
            │                        (1) Supported by evidence? (2) Relevant to gap?
            │                        (3) Correct type? (4) No placeholders? (5) Resolves gap?
            ├── [FAILED ANY POINT] --> Re-plan search query
            └── [PASSED ALL 5]   --> Admit to Shared Verified State (K)
            │
            ▼
   5. Role: Synthesizer          <-- Chronological & single-span rules generate final answer
            │
            ▼
   [Final Grounded Answer & Verifiable Sentence Citations]
```

---

## RAIR vs. Competitive KAIR: Key Results

Both systems were rigorously evaluated across **640 system runs (320 matched pairs)** on the official **HotpotQA** benchmark under **identical budget limits**: exactly 4 document retrievals and 18 LLM calls per run (`RunBudget(4, 18)`).

### 1. Fresh Held-Out Test Evaluation (50 Questions / 100 Matched Pairs / 200 Runs)
Evaluated on completely quarantined, untouched questions using local `qwen3.5:4b` on an NVIDIA RTX 4060 GPU:

| Performance Dimension | RAIR (This Project) | Competitive KAIR | Advantage of RAIR |
| :--- | :---: | :---: | :--- |
| **Exact Match (EM)** | **56.0%** | 54.0% | **+2.0 pp Accuracy Victory** |
| **Answer F1 Score** | **65.1%** | 63.5% | **+1.6 pp Superior Lexical Overlap** |
| **Gold Retrieval Recall** | **89.0%** | 80.0% | **+9.0 pp Massive Evidence Discovery Lead** |
| **Citation Precision** | **73.2%** | 70.1% | **+3.1 pp Higher Grounded Factuality** |
| **Citation F1 Score** | **58.7%** | 56.1% | **+2.6 pp Better Sentence Attribution** |
| **Software Crashes** | **0 (0.0%)** | 5 (5.0%) | **100% Stability vs. 5 Fatal KAIR Crashes** |
| **Execution Latency** | **15.0s** | 15.5s | **3.4% Faster Execution** |
| **Completion Tokens** | **680.8** | 724.2 | **Fewer Wasted Generation Tokens** |

### 2. Grand Pooled Longitudinal Trajectory (All 640 System Runs)
Across all 5 evaluation cohorts over the project lifecycle:
- **Retrieval Recall:** RAIR achieved **87.8% vs. 81.4% (+6.41 pp lead)**, leading in every cohort without exception.
- **Engine Stability:** RAIR had **0 crashes** (100% completion rate), while KAIR suffered **10 fatal crashes**.
- **Execution Speed:** RAIR completed **6.8% faster** by eliminating redundant parallel queries.

---

## What is Inside the Project? (Project Tour)

```
RAIR/
├── config/                 # Frozen experiment configurations, manifests & exclusions
├── dashboard/              # Interactive Web Research Dashboard
│   ├── server.py           # Multi-threaded HTTP server (Zero external dependencies!)
│   ├── ablations.py        # Benchmark and cohort loaders
│   └── static/             # Frontend UI (HTML, CSS, JS with real-time polling)
├── data/                   # HotpotQA evaluation datasets
├── deliverables/           # Packaged academic & presentation materials
│   ├── report_latex/       # Complete LaTeX documentation source code & college emblem
│   ├── rair_test/          # Held-out test findings, failure review, and outcome census CSV
│   ├── rair_scale/         # 200-run scale benchmark deliverables
│   ├── step7/              # Formal 12-page report (DOCX & PDF), 12-slide PPTX, 30 Viva Q&As
│   └── step9/              # Component ablation findings and presentation
├── docs/                   # Detailed technical documentation and architectural specs
├── src/                    # Core Python Source Code
│   ├── rair/               # The RAIR Architecture (Decomposer, Planner, Verifier, etc.)
│   ├── kair/               # The Competitive KAIR Baseline (Dual-agent debate)
│   ├── retrieval/          # Deterministic local BM25 ranking engine
│   ├── evaluation/         # Budget caps (RunBudget) and paired bootstrap scoring
│   └── llm/                # Local Ollama client and prompt schemas
├── tests/                  # Complete Test Suite (246 unit & integration tests)
├── tools/                  # Automation, analysis scripts, and deliverables builders
├── README.md               # This beginner-friendly master guide
├── requirements.txt        # Python dependencies (PyYAML)
└── start_dashboard.cmd     # One-click Windows launch script
```

---

## How to Run the Project (Quickstart Guide)

### Prerequisites
1. **Python 3.10+** installed on your system.
2. **Git** installed on your system.
3. **Ollama** installed and running locally ([Download Ollama](https://ollama.ai/)).
   Pull the model used for local experiments:
   ```bash
   ollama pull qwen2.5:3b
   # or the 4B parameter model:
   ollama pull qwen3.5:4b
   ```

### 1. Launch the Interactive Web Dashboard (Recommended!)

The easiest and coolest way to explore RAIR is through its interactive dashboard.

1. Open your terminal in the project root:
   ```powershell
   # If on Windows, simply double-click start_dashboard.cmd or run:
   .\start_dashboard.cmd

   # Or run via Python directly:
   python -m dashboard.server
   ```
2. Open your web browser and navigate to:
   ```
   http://127.0.0.1:8765
   ```
3. Click **"Run comparison"** on any preloaded question or enter your own custom question and supporting sentences. You will see both RAIR and KAIR execute in real time side by side!

---

### 2. Run the Automated Test Suite

Ensure everything is functioning properly by executing the 246 unit and integration tests (takes ~18 seconds, runs offline without Ollama):

```powershell
python -m unittest discover -s tests
```
*Expected output:* `Ran 246 tests in 18s ... OK`

---

### 3. Run Head-to-Head Terminal Comparisons

You can also run experiments directly from the command line:

```powershell
# Run RAIR on sample questions
python -m src.experiments.check_rair_pipeline

# Run competitive KAIR on sample questions
python -m src.experiments.check_kair_pipeline

# Analyze Grand Pooled stats across all 640 runs
python tools/analyze_grand_pooled.py
```

---

## What to See in the Interactive Dashboard

When you open `http://127.0.0.1:8765`, the dashboard provides five rich research views:
1. **Live Head-to-Head Execution:** Enter a multi-hop question and watch RAIR decompose the question, plan queries, retrieve documents, verify facts, and synthesize answers live.
2. **Stage Progression Timelines:** Inspect the exact query sent to BM25, the extracted triples, and the 5-point verifier decisions ($v_1 \dots v_5$).
3. **Controlled Benchmark Explorer:** Search and filter through all matched question pairs across evaluation cohorts.
4. **Token & Latency Diagnostics:** Inspect actual prompt tokens, completion tokens, and execution time per question.
5. **JSON Export:** Download full execution traces and verified candidate state in standard JSON format with a single click.

---

## Research Deliverables & Report

All formal academic deliverables are neatly organized in the `deliverables/` folder:
- **`deliverables/report_latex/`:** Complete, compilable LaTeX project documentation report with title page, bonafide certificate, TikZ flowcharts, and academic references.
- **`deliverables/step7/`:**
  - `RAIR_KAIR_Final_Report.docx` & `.pdf`: Formal 12-page research compendium.
  - `RAIR_KAIR_Presentation_Final.pptx` & `.pdf`: 12-slide presentation with speaker notes.
  - `RAIR_KAIR_Viva_Questions.docx` & `.pdf`: 30 Viva examination questions and answers.
  - `RAIR_KAIR_Demo_Script.docx` & `.pdf`: Live classroom demonstration guide.
- **`deliverables/rair_test/`:** Granular census CSV, bootstrap confidence intervals, and residual error audits.

---

## Authors & Academic Affiliation

- **Project:** Role-Aware Information Routing (RAIR) vs. Competitive Multi-Agent Systems in Multi-Hop Reasoning
- **Students:** C.B. Dheeraj, A. Saketh Vamshee, V.V. Rohit Reddy
- **Guide:** Mr. P. Narsaiah (Assistant Professor, Dept. of CSE)
- **Institution:** Department of Computer Science & Engineering, Vasavi College of Engineering (Autonomous), Hyderabad, Telangana, India.
