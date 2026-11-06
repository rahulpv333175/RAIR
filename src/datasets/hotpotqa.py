"""Load original HotpotQA JSON, separating model inputs from gold labels."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.retrieval.document_store import Document


@dataclass(frozen=True)
class QuestionInput:
    question_id: str
    question: str
    documents: tuple[Document, ...]


@dataclass(frozen=True)
class GoldLabels:
    answer: str
    supporting_facts: tuple[tuple[str, int], ...]
    question_type: str | None
    level: str | None


@dataclass(frozen=True)
class HotpotExample:
    task: QuestionInput
    gold: GoldLabels


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string.")
    return value  # Preserve the original value, including whitespace.


def parse_hotpotqa_record(record: Any) -> HotpotExample:
    if not isinstance(record, dict):
        raise ValueError("Each HotpotQA record must be an object.")
    question_id = _text(record.get("_id"), "_id")
    question = _text(record.get("question"), "question")
    context = record.get("context")
    if not isinstance(context, list) or not context:
        raise ValueError("context must be a nonempty list of paragraphs.")

    documents = []
    for index, paragraph in enumerate(context):
        if not isinstance(paragraph, list) or len(paragraph) != 2:
            raise ValueError(f"context[{index}] must be [title, sentences].")
        title, sentences = paragraph
        if not isinstance(sentences, list) or any(
            not isinstance(sentence, str) for sentence in sentences
        ):
            raise ValueError(f"context[{index}] sentences must be a list of strings.")
        documents.append(Document(
            document_id=f"{question_id}:D{index + 1}",
            question_id=question_id,
            title=_text(title, f"context[{index}] title"),
            sentences=tuple(sentences),
        ))

    support = record.get("supporting_facts")
    if not isinstance(support, list):
        raise ValueError("supporting_facts must be a list; use labeled dev data.")
    references = []
    for index, reference in enumerate(support):
        if not isinstance(reference, list) or len(reference) != 2:
            raise ValueError(f"supporting_facts[{index}] must be [title, sent_id].")
        title, sentence_id = reference
        if type(sentence_id) is not int:
            raise ValueError("Supporting sentence IDs must be integers.")
        # Preserve references exactly. The check script audits their validity.
        references.append((_text(title, "supporting title"), sentence_id))

    return HotpotExample(
        task=QuestionInput(question_id, question, tuple(documents)),
        gold=GoldLabels(
            answer=_text(record.get("answer"), "answer"),
            supporting_facts=tuple(references),
            question_type=_text(record["type"], "type") if "type" in record else None,
            level=_text(record["level"], "level") if "level" in record else None,
        ),
    )


def load_hotpotqa(path: str | Path) -> list[HotpotExample]:
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            records = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {path}. Check for an incomplete download or HTML page."
        ) from exc
    if not isinstance(records, list) or not records:
        raise ValueError("Expected a nonempty JSON array in original HotpotQA format.")

    examples = []
    seen = set()
    for index, record in enumerate(records):
        try:
            example = parse_hotpotqa_record(record)
            if example.task.question_id in seen:
                raise ValueError(f"Duplicate question ID: {example.task.question_id}")
        except ValueError as exc:
            raise ValueError(f"HotpotQA record {index}: {exc}") from exc
        seen.add(example.task.question_id)
        examples.append(example)
    return examples