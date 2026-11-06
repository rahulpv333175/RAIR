"""Held-out exclusions and paired uncertainty must be fixed before inference."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.evaluation.paired import METRICS, aggregate, load_manifest_examples, prepare_manifest, render_report
from src.evaluation.uncertainty import paired_bootstrap, percentile
from src.settings import load_settings


class HeldOutTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "data.json"
        self.rows = [{"_id": f"q{i}", "question": f"Question {i}?", "answer": "yes",
                      "context": [["Source", ["Original evidence."]]], "supporting_facts": [["Source", 0]]}
                     for i in range(4)]
        self.path.write_text(json.dumps(self.rows), encoding="utf-8")
        self.settings = load_settings()
        self.settings["dataset"]["path"] = str(self.path)
        self.settings["evaluation"].update(sample_size=2, exclude_first_n=1,
                                            exclude_question_ids=["q3"], bootstrap_resamples=1000,
                                            bootstrap_seed=17, purpose="Untouched benchmark")

    def test_prefix_and_explicit_exclusions_are_applied_before_sampling(self):
        manifest = prepare_manifest(self.settings)
        self.assertEqual(manifest["excluded_question_ids"], ["q0", "q3"])
        self.assertEqual({q["question_id"] for q in manifest["questions"]}, {"q1", "q2"})
        self.assertEqual(manifest["purpose"], "Untouched benchmark")
        self.assertEqual(set(load_manifest_examples(manifest)), {"q1", "q2"})

    def test_invalid_or_unknown_exclusions_fail_before_sampling(self):
        for excluded in (["missing"], ["q3", "q3"], [3], "q3", [""]):
            settings = copy.deepcopy(self.settings)
            settings["evaluation"]["exclude_question_ids"] = excluded
            with self.subTest(excluded=excluded), self.assertRaises(ValueError):
                prepare_manifest(settings)

    def test_overlapping_prefix_exclusion_is_deduplicated(self):
        self.settings["evaluation"]["exclude_question_ids"] = ["q0", "q3"]
        self.assertEqual(prepare_manifest(self.settings)["excluded_question_ids"], ["q0", "q3"])

    def test_too_many_exclusions_or_invalid_analysis_config_fail(self):
        for key, value in (("exclude_question_ids", ["q1", "q2", "q3"]),
                           ("bootstrap_resamples", 999), ("bootstrap_resamples", True),
                           ("bootstrap_seed", -1), ("sample_size", 1)):
            settings = copy.deepcopy(self.settings)
            settings["evaluation"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                prepare_manifest(settings)

    def test_gold_mutation_leaves_selected_inputs_unchanged(self):
        first = prepare_manifest(self.settings)
        for row in self.rows:
            row["answer"] = "__UNSEEN_GOLD__"
            row["supporting_facts"] = [["__UNSEEN_SUPPORT__", 99]]
        self.path.write_text(json.dumps(self.rows), encoding="utf-8")
        changed = prepare_manifest(self.settings)
        self.assertEqual(first["questions"], changed["questions"])
        self.assertEqual(first["schedule"], changed["schedule"])
        self.assertNotEqual(first["dataset_sha256"], changed["dataset_sha256"])

    def test_complete_summary_and_report_include_prespecified_uncertainty(self):
        self.settings["evaluation"]["name"] = "Held-out test"
        manifest = prepare_manifest(self.settings)
        rows = [{**entry, "evaluation": {**dict.fromkeys(METRICS, 1.0), "annotation_issues": []},
                 "result": {"status": "answered", "stop_reason": "complete",
                            "prediction": {"answer": "yes", "citations": [], "abstain": False},
                            "usage": {"token_counts_complete": True,
                                      **dict.fromkeys(("llm_calls", "retrieval_calls", "prompt_tokens",
                                                       "completion_tokens", "elapsed_seconds"), 1)}}}
                for entry in manifest["schedule"]]
        summary = aggregate(manifest, rows)
        self.assertEqual(summary["uncertainty"]["num_questions"], 2)
        self.assertEqual(summary["uncertainty"]["KAIR_minus_RAIR"]["exact_match"]["ci95"], [0, 0])
        report = render_report(manifest, summary)
        self.assertTrue(report.startswith("# Held-out test"))
        self.assertIn("95% paired question-cluster bootstrap intervals", report)
        with self.assertRaisesRegex(ValueError, "exactly one result"):
            aggregate(manifest, rows[:-1])


class UncertaintyTests(unittest.TestCase):
    def bootstrap(self, left, right):
        manifest = {"questions": [{"question_id": f"q{i}"} for i in range(len(left))],
                    "settings": {"evaluation": {"seeds": [42, 43], "bootstrap_resamples": 1000,
                                                "bootstrap_seed": 17}}}
        records = [{"question_id": f"q{i}", "seed": seed, "system": system,
                    "evaluation": {"exact_match": values[i][j], "answer_f1": values[i][j]}}
                   for i in range(len(left)) for j, seed in enumerate((42, 43))
                   for system, values in (("RAIR", left), ("KAIR", right))]
        return paired_bootstrap(manifest, records)

    def test_percentile_interpolates_and_handles_constant_values(self):
        self.assertEqual(percentile([0, 10], 0.25), 2.5)
        self.assertEqual(percentile([1, 1, 1], 0.975), 1)

    def test_pairing_retains_correlation_and_seed_clusters(self):
        result = self.bootstrap([[0, 0], [1, 1]], [[0, 0], [1, 1]])
        self.assertEqual(result["num_questions"], 2)
        self.assertEqual(result["seeds_per_question"], 2)
        self.assertEqual(result["systems"]["RAIR"]["exact_match"]["ci95"], [0, 1])
        self.assertEqual(result["KAIR_minus_RAIR"]["exact_match"], {"estimate": 0, "ci95": [0, 0]})

    def test_seed_averages_are_resampled_together(self):
        result = self.bootstrap([[0, 1], [1, 0]], [[1, 1], [1, 1]])
        self.assertEqual(result["systems"]["RAIR"]["exact_match"], {"estimate": 0.5, "ci95": [0.5, 0.5]})
        self.assertEqual(result["KAIR_minus_RAIR"]["exact_match"], {"estimate": 0.5, "ci95": [0.5, 0.5]})

    def test_fixed_seed_reproduces_intervals_and_sign(self):
        left, right = [[1, 1], [0, 1], [1, 0]], [[0, 0], [1, 1], [1, 1]]
        first = self.bootstrap(left, right)
        self.assertEqual(first, self.bootstrap(left, right))
        self.assertAlmostEqual(first["KAIR_minus_RAIR"]["exact_match"]["estimate"], 0)


if __name__ == "__main__":
    unittest.main()
