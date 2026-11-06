"""Synthetic tests; no downloaded data, network, or Ollama required."""

import copy
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from src.datasets.hotpotqa import load_hotpotqa, parse_hotpotqa_record
from src.retrieval.document_store import DocumentStore


def sample_record() -> dict:
    return {
        "_id": "toy-1",
        "question": "In which city was the author of The Glass Orchard born?",
        "answer": "Nerava",
        "type": "bridge",
        "level": "hard",
        "context": [
            ["The Glass Orchard", ["The Glass Orchard was written by Mira Solen."]],
            ["Mira Solen", ["", "  Mira Solen was born in Nerava.\t"]],
            ["Weather", ["Rain is precipitation."]],
        ],
        "supporting_facts": [["The Glass Orchard", 0], ["Mira Solen", 1]],
    }


class DatasetTests(unittest.TestCase):
    def test_original_sentences_and_indices_are_preserved(self):
        document = parse_hotpotqa_record(sample_record()).task.documents[1]
        self.assertEqual(document.sentences, ("", "  Mira Solen was born in Nerava.\t"))
        self.assertEqual(document.sentence(1), "  Mira Solen was born in Nerava.\t")
        self.assertEqual(document.search_text, "Mira Solen Mira Solen was born in Nerava.")
        with self.assertRaises(IndexError):
            document.sentence(-1)

    def test_gold_changes_do_not_change_inputs(self):
        original = sample_record()
        changed = copy.deepcopy(original)
        changed.update(answer="Different", supporting_facts=[], type="comparison", level="easy")
        first = parse_hotpotqa_record(original)
        second = parse_hotpotqa_record(changed)
        self.assertEqual(first.task, second.task)
        self.assertNotEqual(first.gold, second.gold)
        self.assertEqual(set(asdict(first.task)), {"question_id", "question", "documents"})

    def test_store_lookup_and_order(self):
        task = parse_hotpotqa_record(sample_record()).task
        store = DocumentStore(task.question_id, task.documents)
        self.assertEqual(len(store), 3)
        self.assertEqual(store.all_documents(), task.documents)
        self.assertEqual(store.get("toy-1:D2").title, "Mira Solen")
        with self.assertRaises(KeyError):
            store.get("other-question:D2")

    def test_cross_question_and_duplicate_documents_are_rejected(self):
        task = parse_hotpotqa_record(sample_record()).task
        with self.assertRaises(ValueError):
            DocumentStore("other-question", task.documents)
        with self.assertRaises(ValueError):
            DocumentStore(task.question_id, [task.documents[0], task.documents[0]])

    def test_loader_handles_utf8_bom_and_duplicate_question_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.json"
            row = sample_record()
            path.write_text(json.dumps([row]), encoding="utf-8-sig")
            self.assertEqual(len(load_hotpotqa(path)), 1)
            path.write_text(json.dumps([row, row]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate question ID"):
                load_hotpotqa(path)

    def test_invalid_context_is_rejected(self):
        row = sample_record()
        row["context"] = [["Title", "This should have been a list."]]
        with self.assertRaises(ValueError):
            parse_hotpotqa_record(row)

    def test_invalid_gold_reference_is_preserved_for_audit(self):
        row = sample_record()
        row["supporting_facts"] = [["Missing title", 999]]
        example = parse_hotpotqa_record(row)
        self.assertEqual(example.gold.supporting_facts, (("Missing title", 999),))
        self.assertEqual(len(example.task.documents), 3)


if __name__ == "__main__":
    unittest.main()