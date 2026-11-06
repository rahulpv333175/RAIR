"""Deterministic answer and retrieval evaluation metrics."""

import re
import string
from collections import Counter
from dataclasses import dataclass
from typing import Iterable


SPECIAL_ANSWERS = {"yes", "no", "noanswer"}


def normalize_answer(text: str) -> str:
    """Normalize an answer using HotpotQA-style rules."""
    if not isinstance(text, str):
        raise TypeError("Answer must be a string.")

    def remove_articles(value: str) -> str:
        return re.sub(r"\b(a|an|the)\b", " ", value)

    def remove_punctuation(value: str) -> str:
        return "".join(
            character
            for character in value
            if character not in string.punctuation
        )

    def normalize_whitespace(value: str) -> str:
        return " ".join(value.split())

    value = text.lower()
    value = remove_punctuation(value)
    value = remove_articles(value)
    value = normalize_whitespace(value)

    return value


def exact_match(prediction: str, gold: str) -> float:
    """Return 1.0 when normalized answers match exactly."""
    return float(
        normalize_answer(prediction)
        == normalize_answer(gold)
    )


def answer_f1(prediction: str, gold: str) -> float:
    """Return token-level F1 between prediction and gold answer."""
    normalized_prediction = normalize_answer(prediction)
    normalized_gold = normalize_answer(gold)

    # HotpotQA-style handling of special answers.
    # For example, "yes indeed" must not receive partial
    # credit against a gold answer of "yes".
    if (
        normalized_prediction in SPECIAL_ANSWERS
        or normalized_gold in SPECIAL_ANSWERS
    ):
        return float(
            normalized_prediction == normalized_gold
        )

    prediction_tokens = normalized_prediction.split()
    gold_tokens = normalized_gold.split()

    if not prediction_tokens or not gold_tokens:
        return float(
            prediction_tokens == gold_tokens
        )

    common = (
        Counter(prediction_tokens)
        & Counter(gold_tokens)
    )

    num_same = sum(common.values())

    if num_same == 0:
        return 0.0

    precision = (
        num_same / len(prediction_tokens)
    )

    recall = (
        num_same / len(gold_tokens)
    )

    return (
        2.0
        * precision
        * recall
        / (precision + recall)
    )


@dataclass(frozen=True)
class RetrievalMetrics:
    precision: float
    recall: float
    f1: float


def retrieval_metrics(
    retrieved_ids: Iterable[str],
    gold_ids: Iterable[str],
) -> RetrievalMetrics:
    """Calculate set-based document retrieval precision/recall/F1.

    Duplicate document IDs do not receive additional credit.
    """
    retrieved = set(retrieved_ids)
    gold = set(gold_ids)

    if not retrieved and not gold:
        return RetrievalMetrics(
            precision=1.0,
            recall=1.0,
            f1=1.0,
        )

    if not retrieved or not gold:
        return RetrievalMetrics(
            precision=0.0,
            recall=0.0,
            f1=0.0,
        )

    true_positives = len(
        retrieved.intersection(gold)
    )

    precision = (
        true_positives / len(retrieved)
    )

    recall = (
        true_positives / len(gold)
    )

    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = (
            2.0
            * precision
            * recall
            / (precision + recall)
        )

    return RetrievalMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
    )