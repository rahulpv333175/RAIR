"""Frozen, paired evaluation protocol and gold-only post-inference scoring."""

import copy
import hashlib
import json
import math
import random
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from src.datasets.hotpotqa import HotpotExample, load_hotpotqa
from src.evaluation.budget import RunBudget
from src.evaluation.metrics import answer_f1, exact_match, retrieval_metrics
from src.evaluation.uncertainty import paired_bootstrap
from src.kair.controller import KAIRController
from src.llm.ollama_client import OllamaClient
from src.rair.controller import RAIRController
from src.rair.reference import ReferenceRAIRController
from src.rair.ablations import NoVerificationRAIRController, NoDecompositionRAIRController
from src.settings import PROJECT_ROOT, project_path


CONTROLLERS = {"RAIR": RAIRController, "KAIR": KAIRController, "RAIR_REFERENCE": ReferenceRAIRController}
ABLATIONS = ('RAIR_NO_VERIFICATION', 'RAIR_NO_DECOMPOSITION')
CONTROLLERS.update(zip(ABLATIONS, (NoVerificationRAIRController, NoDecompositionRAIRController)))
METRICS = ("exact_match", "answer_f1", "citation_precision", "citation_recall", "citation_f1",
           "retrieval_precision", "retrieval_recall", "retrieval_f1")


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def source_hashes() -> dict[str, str]:
    paths = sorted((PROJECT_ROOT / "src").rglob("*.py")) + [PROJECT_ROOT / "requirements.txt"]
    return {path.relative_to(PROJECT_ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


def system_names(config: dict) -> list[str]:
    return ["RAIR", "KAIR"] + (list(ABLATIONS) if config.get('ablations') is True else
                               ["RAIR_REFERENCE"] if "reference_rair" in config else [])


def schedule(questions: list[dict], seeds: list[int], *, reference: bool = False, ablations: bool = False) -> list[dict]:
    entries = []
    for q_index, question in enumerate(questions):
        for s_index, seed in enumerate(seeds):
            order = ["RAIR", "KAIR"] if (q_index + s_index) % 2 == 0 else ["KAIR", "RAIR"]
            if reference:
                base = ["RAIR", "KAIR", "RAIR_REFERENCE"]
                offset = q_index % 3
                order = base[offset:] + base[:offset]
                if s_index % 2:
                    order.reverse()
            if ablations:
                base = ['RAIR', 'KAIR', *ABLATIONS]
                offset = (q_index + s_index) % 4
                order = base[offset:] + base[:offset]
            primary_order = [system for system in order if system in ('RAIR', 'KAIR')]
            for position, system in enumerate(order):
                entry = {"question_id": question["question_id"], "seed": seed,
                         "system": system, "position_in_pair": primary_order.index(system) if system in primary_order else None}
                if reference or ablations:
                    entry["position_in_block"] = position
                entries.append(entry)
    return entries


def prepare_manifest(settings: dict) -> dict:
    settings = copy.deepcopy(settings)
    config = settings["evaluation"]
    if ('ablations' in config and type(config['ablations']) is not bool) or (config.get('ablations') and 'reference_rair' in config):
        raise ValueError('Ablations must be boolean and cannot be combined with the archived reference arm.')
    for name in ("name", "purpose"):
        if name in config and (not isinstance(config[name], str) or not config[name].strip()):
            raise ValueError(f"evaluation.{name} must be a nonempty string.")
    for name in ("sample_size", "sample_seed", "exclude_first_n"):
        value = config[name]
        if type(value) is not int or value < (1 if name == "sample_size" else 0):
            raise ValueError(f"Invalid evaluation.{name}.")
    seeds = config["seeds"]
    if (not isinstance(seeds, list) or not seeds or
            any(type(seed) is not int or seed < 0 for seed in seeds) or len(set(seeds)) != len(seeds)):
        raise ValueError("Evaluation seeds must be unique nonnegative integers.")
    temperature = config["temperature"]
    if type(temperature) not in (int, float) or not math.isfinite(temperature) or temperature < 0.7:
        raise ValueError("Common retrieval-stage temperature must be finite and >= 0.7.")
    budget = RunBudget(config["max_retrieval_calls"], config["max_llm_calls"])
    if (settings["retrieval"]["method"] != "bm25"
            or settings["retrieval"]["corpus_scope"] != "per_question"
            or settings["retrieval"]["web_enabled"] is not False):
        raise ValueError("The paired protocol requires local per-question BM25 retrieval.")
    # Native ceilings must not secretly constrain one arm below the common caps.
    for name in system_names(config):
        controller_type = CONTROLLERS[name]
        policy = controller_type(settings, OllamaClient(settings)).policy
        for resource in ("max_retrieval_calls", "max_llm_calls"):
            if getattr(budget, resource) > policy[resource]:
                raise ValueError(f"Common {resource} exceeds a system's native ceiling.")
    dataset = project_path(settings["dataset"]["path"])
    examples = load_hotpotqa(dataset)
    explicit = config.get("exclude_question_ids", [])
    if (not isinstance(explicit, list) or any(not isinstance(qid, str) or not qid.strip() for qid in explicit)
            or len(set(explicit)) != len(explicit)
            or not set(explicit) <= {e.task.question_id for e in examples}):
        raise ValueError("Explicit exclusions must be unique question IDs present in the dataset.")
    if "bootstrap_resamples" in config or "bootstrap_seed" in config:
        if (type(config.get("bootstrap_resamples")) is not int or config["bootstrap_resamples"] < 1000
                or type(config.get("bootstrap_seed")) is not int or config["bootstrap_seed"] < 0
                or config["sample_size"] < 2):
            raise ValueError("Question bootstrap requires >= 1000 resamples, a nonnegative seed and >= 2 questions.")
    excluded = [e.task.question_id for e in examples[:config["exclude_first_n"]]]
    excluded += [qid for qid in explicit if qid not in excluded]
    excluded_set = set(excluded)
    pool = sorted((e for e in examples if e.task.question_id not in excluded_set), key=lambda e: e.task.question_id)
    if len(pool) < config["sample_size"]:
        raise ValueError("Not enough questions remain after development exclusions.")
    selected = random.Random(config["sample_seed"]).sample(pool, config["sample_size"])
    questions = [{"question_id": e.task.question_id, "input_sha256": fingerprint(asdict(e.task))}
                 for e in selected]
    return {
        "schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": config.get("purpose", "Step 3 paired integration pilot; not a final research benchmark."),
        "settings": settings, "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "source_sha256": source_hashes(), "excluded_question_ids": excluded,
        "questions": questions, "schedule": schedule(questions, seeds, reference="reference_rair" in config,
                                                     ablations=config.get('ablations', False)),
        "sampling_policy": {"non_final_temperature": temperature, "final_temperature": 0.0,
                            "kair_agent_seed_offsets": list(range(settings["kair"]["num_agents"]))},
    }


def load_manifest_examples(manifest: dict) -> dict[str, HotpotExample]:
    if manifest.get("schema_version") != 1 or manifest["source_sha256"] != source_hashes():
        raise ValueError("Protocol source changed; prepare a new manifest instead of mixing versions.")
    settings = manifest["settings"]
    config = settings["evaluation"]
    questions = manifest["questions"]
    ids = [q["question_id"] for q in questions]
    if (len(ids) != config["sample_size"] or len(set(ids)) != len(ids)
            or set(ids) & set(manifest["excluded_question_ids"])
            or manifest["schedule"] != schedule(questions, config["seeds"], reference="reference_rair" in config,
                                                 ablations=config.get('ablations', False))):
        raise ValueError("Invalid question manifest or counterbalanced execution schedule.")
    dataset = project_path(settings["dataset"]["path"])
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != manifest["dataset_sha256"]:
        raise ValueError("Dataset changed since the manifest was prepared.")
    expected = prepare_manifest(settings)
    if any(manifest.get(key) != value for key, value in expected.items() if key != "created_at_utc"):
        raise ValueError("Manifest differs from the declared sampling and control policy.")
    examples = {e.task.question_id: e for e in load_hotpotqa(dataset) if e.task.question_id in ids}
    for question in questions:
        example = examples.get(question["question_id"])
        if example is None or fingerprint(asdict(example.task)) != question["input_sha256"]:
            raise ValueError("A selected question or document pool changed.")
    return examples


def score_result(result: dict, example: HotpotExample) -> dict:
    """Consult gold only here, after the controller has returned its prediction."""
    answer = result["prediction"]["answer"] if result["status"] == "answered" else ""
    documents = {doc.document_id: doc for doc in example.task.documents}
    issues = []
    for title, index in example.gold.supporting_facts:
        if not any(doc.title == title and 0 <= index < len(doc.sentences) for doc in documents.values()):
            issues.append({"title": title, "sentence_index": index, "reason": "Invalid gold source reference."})
    if not example.gold.supporting_facts:
        issues.append({"reason": "No gold supporting facts available."})
    cited = set()
    invalid = 0
    if result["status"] == "answered":
        for source in result["sources"]:
            document = documents.get(source["document_id"])
            index = source["sentence_index"]
            valid = (document is not None and type(index) is int and 0 <= index < len(document.sentences)
                     and source["title"] == document.title and source["text"] == document.sentence(index))
            if valid:
                cited.add(json.dumps([document.title, index]))
            else:
                invalid += 1
                cited.add(f"__invalid_citation_{invalid}__")
    gold_citations = {json.dumps([title, index]) for title, index in example.gold.supporting_facts}
    # Retrieval effectiveness counts every paid attempt, including losing agents' searches.
    histories = (result["state"]["query_history"] if "state" in result else
                 [q for agent in result["agents"] for q in agent["query_history"]])
    retrieved = {documents[doc_id].title if doc_id in documents else f"__invalid_doc__:{doc_id}"
                 for query in histories for doc_id in query["retrieved_document_ids"]}
    gold_titles = {title for title, _ in example.gold.supporting_facts}
    metrics = {"exact_match": exact_match(answer, example.gold.answer),
               "answer_f1": answer_f1(answer, example.gold.answer),
               "invalid_citations": invalid, "annotation_issues": issues}
    for prefix, prediction, gold in (("citation", cited, gold_citations),
                                     ("retrieval", retrieved, gold_titles)):
        values = retrieval_metrics(prediction, gold)
        for metric in ("precision", "recall", "f1"):
            metrics[f"{prefix}_{metric}"] = getattr(values, metric) if not issues else None
    return metrics


def audit_result(result: dict, task, budget: RunBudget, config: dict, seed: int, system: str) -> None:
    calls = result["llm_calls"]
    if result["question_id"] != task.question_id or result["question"] != task.question:
        raise ValueError("Controller returned a different question.")
    if (len(calls) != budget.llm_calls or result["usage"]["llm_calls"] != budget.llm_calls
            or result["usage"]["retrieval_calls"] != budget.retrieval_calls
            or sum(call["final_answer"] for call in calls) != budget.final_calls
            or (result["status"] != "error" and budget.final_calls != 1)
            or budget.llm_calls > budget.max_llm_calls or budget.retrieval_calls > budget.max_retrieval_calls):
        raise ValueError("Common budget accounting does not match actual execution.")
    for call in calls:
        request = call["request"]
        final = call["final_answer"]
        expected_seed = seed if final or system != 'KAIR' else seed + int(call["agent_id"][1:]) - 1
        options = request["options"]
        if (request["model"] != config["llm"]["model"] or options["seed"] != expected_seed
                or options["temperature"] != (0.0 if final else config["evaluation"]["temperature"])
                or options["num_ctx"] != config["llm"]["num_ctx"]
                or options["num_predict"] != config["llm"]["num_predict"]):
            raise ValueError("Actual generation settings violate the frozen common protocol.")


def aggregate(manifest: dict, records: list[dict]) -> dict:
    expected = {(e["question_id"], e["seed"], e["system"]) for e in manifest["schedule"]}
    indexed = {(r["question_id"], r["seed"], r["system"]): r for r in records}
    if len(indexed) != len(records) or set(indexed) != expected:
        raise ValueError("Summary requires exactly one result for every planned system/question/seed.")
    systems = {}
    for system in system_names(manifest["settings"]["evaluation"]):
        rows = [r for r in records if r["system"] == system]
        n = len(rows)
        values = {metric: [r["evaluation"][metric] for r in rows if r["evaluation"][metric] is not None]
                  for metric in METRICS}
        systems[system] = {
            "num_runs": n, "unique_questions": len(manifest["questions"]),
            **{status: sum(r["result"]["status"] == status for r in rows)
               for status in ("answered", "abstained", "error")},
            "coverage": sum(r["result"]["status"] == "answered" for r in rows) / n,
            "metrics": {metric: sum(v) / len(v) if v else None for metric, v in values.items()},
            "metric_denominators": {metric: len(v) for metric, v in values.items()},
            "agent_errors": sum(len(r["result"].get("agent_errors", [])) for r in rows),
            "budget_stops": sum(r["result"]["stop_reason"] == "budget_exhausted" for r in rows),
            "runs_with_incomplete_token_counts": sum(not r["result"]["usage"]["token_counts_complete"] for r in rows),
            "annotation_issue_runs": sum(bool(r["evaluation"]["annotation_issues"]) for r in rows),
            "mean_usage": {key: sum(r["result"]["usage"][key] for r in rows) / n
                           for key in ("llm_calls", "retrieval_calls", "prompt_tokens", "completion_tokens", "elapsed_seconds")},
        }
    pairs = []
    wins = {"RAIR": 0, "KAIR": 0, "ties": 0}
    for question in manifest["questions"]:
        for seed in manifest["settings"]["evaluation"]["seeds"]:
            left = indexed[(question["question_id"], seed, "RAIR")]
            right = indexed[(question["question_id"], seed, "KAIR")]
            delta = right["evaluation"]["exact_match"] - left["evaluation"]["exact_match"]
            wins["KAIR" if delta > 0 else "RAIR" if delta < 0 else "ties"] += 1
            pairs.append({"question_id": question["question_id"], "seed": seed,
                          "predictions": {s: indexed[(question["question_id"], seed, s)]["result"]["prediction"]
                                          for s in systems},
                          "KAIR_minus_RAIR": {metric: right["evaluation"][metric] - left["evaluation"][metric]
                                              for metric in ("exact_match", "answer_f1")}})
    summary = {"completed": True, "num_pairs": len(pairs), "systems": systems, "pairs": pairs,
            "paired_exact_match_counts": wins,
            "KAIR_minus_RAIR": {metric: systems["KAIR"]["metrics"][metric] - systems["RAIR"]["metrics"][metric]
                                for metric in ("exact_match", "answer_f1")},
            "interpretation": "Small paired development pilot; repeated seeds are not independent questions. No superiority or significance claim."}
    if "bootstrap_resamples" in manifest["settings"]["evaluation"]:
        summary["uncertainty"] = paired_bootstrap(manifest, records)
        summary["interpretation"] = (
            "Prospectively frozen, previously unexecuted question sample. Interpret paired question-cluster "
            "confidence intervals; repeated seeds are not independent questions. Results apply to this local protocol."
        )
        if "RAIR_REFERENCE" in systems:
            comparison = paired_bootstrap(manifest, [
                {**row, "system": "RAIR" if row["system"] == "RAIR_REFERENCE" else "KAIR"}
                for row in records if row["system"] in {"RAIR", "RAIR_REFERENCE"}])
            summary["uncertainty"]["primary_endpoint"] = "RAIR_minus_REFERENCE.exact_match"
            summary["RAIR_minus_REFERENCE"] = {
                "contrast": "updated RAIR minus Step 4 RAIR core, with the same current final-answer policy",
                "metrics": comparison["KAIR_minus_RAIR"],
                "method": comparison["method"], "num_questions": comparison["num_questions"],
                "resamples": comparison["resamples"], "seed": comparison["seed"]}
        if manifest['settings']['evaluation'].get('ablations'):
            summary['ablation_contrasts'] = {}
            for variant in ABLATIONS:
                contrast = paired_bootstrap(manifest, [
                    {**row, 'system': 'RAIR' if row['system'] == variant else 'KAIR'}
                    for row in records if row['system'] in ('RAIR', variant)], confidence_level=.975)
                summary['ablation_contrasts']['RAIR_minus_'+variant] = contrast['KAIR_minus_RAIR']
            summary['uncertainty']['primary_endpoint'] = 'Two full-RAIR minus component-removal EM contrasts'
            summary['interpretation'] = ('Exploratory component study. Two prespecified EM contrasts use 97.5% '
                'pointwise question-cluster intervals (Bonferroni 95% family coverage, approximately). '
                'Other metrics and RAIR versus KAIR are secondary; small-sample bootstrap limits apply. '
                'Removing a component also changes call counts and stopping behavior; no equal-compute causal claim.')
    return summary


def render_report(manifest: dict, summary: dict) -> str:
    config = manifest["settings"]["evaluation"]
    lines = [f"# {config.get('name', 'Step 3 paired evaluation pilot')}", "",
             f"{len(manifest['questions'])} questions, {len(config['seeds'])} base seeds, "
             f"{summary['num_pairs']} matched pairs. Manifest SHA-256: `{fingerprint(manifest)}`.", "",
             f"Each system: at most {config['max_retrieval_calls']} retrievals and {config['max_llm_calls']} LLM calls, "
             "including one reserved final-answer call. Identical model, document pools, BM25, context/output limits "
             "and final-answer policy. Retrieval-stage temperature is matched; KAIR retains independent agent seeds.", "",
             "| System | Exact match | Answer F1 | Coverage | Errors | Budget stops | Mean LLM calls | Mean retrievals | Mean seconds |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for system, values in summary["systems"].items():
        metrics, usage = values["metrics"], values["mean_usage"]
        lines.append(f"| {system} | {metrics['exact_match']:.1%} | {metrics['answer_f1']:.1%} | "
                     f"{values['coverage']:.1%} | {values['error']} | {values['budget_stops']} | "
                     f"{usage['llm_calls']:.2f} | {usage['retrieval_calls']:.2f} | {usage['elapsed_seconds']:.2f} |")
    lines += ["", "All planned runs contribute to answer scores; abstentions and errors are empty predictions.",
              "Equal resource ceilings do not imply equal actual token use or computation. Runtime is serial local timing, "
              "with a question-free warm-up and counterbalanced system order; it does not reproduce asynchronous KAIR.", "",
              "| System | Source-sentence citation F1 | Cumulative retrieval document recall | Mean prompt tokens | Mean output tokens | Agent errors |",
              "| --- | --- | --- | --- | --- | --- |"]
    for system, v in summary["systems"].items():
        pct = lambda x: "unavailable" if x is None else f"{x:.1%}"
        lines.append(f"| {system} | {pct(v['metrics']['citation_f1'])} | {pct(v['metrics']['retrieval_recall'])} | "
                     f"{v['mean_usage']['prompt_tokens']:.1f} | {v['mean_usage']['completion_tokens']:.1f} | {v['agent_errors']} |")
    lines += ["", "Citation scores measure overlap with annotated source sentences, not semantic entailment. Retrieval recall "
              "uses the union of every paid retrieval, including losing agents. Invalid gold references are flagged and "
              "excluded only from source/retrieval metric denominators, never from answer scoring.", "",
              "Token totals include known counts only. Runs with incomplete token counts: "
              + ", ".join(f"{system}={v['runs_with_incomplete_token_counts']}" for system, v in summary["systems"].items())
              + ".", "",
              ]
    if "uncertainty" in summary:
        uncertainty = summary["uncertainty"]
        lines += ["## Uncertainty across questions", "",
                  f"95% paired question-cluster bootstrap intervals, {uncertainty['resamples']} resamples, "
                  f"analysis seed {uncertainty['seed']}. Seeds stay together when resampling each question. "
                  + ('Primary endpoints: the two component-removal EM contrasts below; this RAIR/KAIR table is secondary.'
                     if 'ablation_contrasts' in summary else "Primary endpoint: updated RAIR minus reference RAIR exact match; other intervals are secondary."
                     if "RAIR_minus_REFERENCE" in summary else "Primary endpoint: KAIR minus RAIR exact match; answer F1 is secondary."), "",
                  "| Endpoint | Estimate | 95% interval |", "| --- | --- | --- |"]
        for system, metrics in {**uncertainty["systems"], "KAIR_minus_RAIR": uncertainty["KAIR_minus_RAIR"]}.items():
            for metric, values in metrics.items():
                low, high = values["ci95"]
                lines.append(f"| {system} {metric} | {values['estimate']:.1%} | [{low:.1%}, {high:.1%}] |")
        lines += ["", uncertainty["interpretation"], ""]
    if "RAIR_minus_REFERENCE" in summary:
        lines += ["## RAIR changes on the same questions", "", summary["RAIR_minus_REFERENCE"]["contrast"], "",
                  "| Updated RAIR minus reference | Estimate | 95% question-cluster interval |",
                  "| --- | --- | --- |"]
        for metric, values in summary["RAIR_minus_REFERENCE"]["metrics"].items():
            low, high = values["ci95"]
            lines.append(f"| {metric} | {values['estimate']:.1%} | [{low:.1%}, {high:.1%}] |")
        lines += ["", "All arms use the same final-answer policy. The reference retains the old decomposition, "
                  "retrieval scheduling, filtering, extraction and verification core.", ""]
    if 'ablation_contrasts' in summary:
        lines += ['## Component removals', '',
                  'Full RAIR minus each removal; 97.5% pointwise question-cluster intervals. '
                  'Two prespecified EM contrasts; F1 is exploratory. Unchecked admissions are not verified facts.', '',
                  '| Contrast | Endpoint | Estimate | 97.5% interval |', '| --- | --- | --- | --- |']
        for contrast, metrics in summary['ablation_contrasts'].items():
            for metric, value in metrics.items():
                low, high = value['ci97_5']
                lines.append(f"| {contrast} | {metric} | {value['estimate']:.1%} | [{low:.1%}, {high:.1%}] |")
        lines += ['', 'The no-gate arm admits all structurally valid candidates and resolves a gap after a nonempty admission. '
                  'The no-decomposition arm replaces generated subquestions with one whole-question gap. '
                  'Source validation and the final synthesis prompt remain common. Removing a component also removes its calls '
                  'and can alter stopping; equal ceilings are not equal computation.', '',
                  '| Question | Seed | Full RAIR | KAIR | No gate | No decomposition |', '| --- | --- | --- | --- | --- | --- |']
        for pair in summary['pairs']:
            predictions = [(pair['predictions'][s]['answer'] or '[empty]').replace('|','\\|').replace('\n',' ')
                           for s in ('RAIR','KAIR',*ABLATIONS)]
            lines.append(f"| {pair['question_id']} | {pair['seed']} | " + ' | '.join(predictions) + ' |')
    lines += ["## Paired predictions", "", "| Question ID | Base seed | RAIR | KAIR | KAIR − RAIR exact match |",
              "| --- | --- | --- | --- | --- |"]
    for pair in summary["pairs"]:
        def label(system):
            prediction = pair["predictions"][system]
            return (prediction["answer"] or "[empty]").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {pair['question_id']} | {pair['seed']} | {label('RAIR')} | {label('KAIR')} | "
                     f"{pair['KAIR_minus_RAIR']['exact_match']:+.0f} |")
    lines += ["", summary["interpretation"], "",
              "Keep these evaluated question IDs outside any future untouched evaluation split.", ""]
    return "\n".join(lines)
