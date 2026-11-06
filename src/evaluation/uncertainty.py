"""Paired percentile bootstrap, resampling questions with all their seeds together."""

import random
from statistics import fmean


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def paired_bootstrap(manifest: dict, records: list[dict], *, confidence_level: float = .95) -> dict:
    if not .5 < confidence_level < 1:
        raise ValueError('Invalid bootstrap confidence level.')
    low_probability, high_probability = (.025, .975) if confidence_level == .95 else ((1-confidence_level)/2, (1+confidence_level)/2)
    interval_key = 'ci95' if confidence_level == .95 else 'ci97_5'
    config = manifest["settings"]["evaluation"]
    ids = [q["question_id"] for q in manifest["questions"]]
    seeds = config["seeds"]
    indexed = {(r["question_id"], r["seed"], r["system"]): r["evaluation"] for r in records}
    metrics = ("exact_match", "answer_f1")
    scores = {(system, metric): [fmean(indexed[(qid, seed, system)][metric] for seed in seeds) for qid in ids]
              for system in ("RAIR", "KAIR") for metric in metrics}
    scores.update({("KAIR_minus_RAIR", metric): [right - left for left, right in
                   zip(scores[("RAIR", metric)], scores[("KAIR", metric)])] for metric in metrics})
    samples = {key: [] for key in scores}
    rng = random.Random(config["bootstrap_seed"])
    for _ in range(config["bootstrap_resamples"]):
        draw = [rng.randrange(len(ids)) for _ in ids]
        for key, values in scores.items():
            samples[key].append(fmean(values[i] for i in draw))
    intervals = {key: {"estimate": fmean(values),
                       interval_key: [percentile(samples[key], low_probability), percentile(samples[key], high_probability)]}
                 for key, values in scores.items()}
    return {
        "method": "paired question-cluster percentile bootstrap; average seeds within each question",
        "confidence_level": confidence_level, "num_questions": len(ids), "seeds_per_question": len(seeds),
        "resamples": config["bootstrap_resamples"], "seed": config["bootstrap_seed"],
        "primary_endpoint": "KAIR_minus_RAIR.exact_match",
        "systems": {system: {metric: intervals[(system, metric)] for metric in metrics}
                    for system in ("RAIR", "KAIR")},
        "KAIR_minus_RAIR": {metric: intervals[("KAIR_minus_RAIR", metric)] for metric in metrics},
        "interpretation": "Pointwise approximate intervals across sampled questions; seeds are not independent observations. F1 is secondary; no multiple-comparison adjustment.",
    }
