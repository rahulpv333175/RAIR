"""Immutable source documents and a separate document pool per question."""

from collections.abc import Iterable
from dataclasses import dataclass


def normalize_whitespace(text: str) -> str:
    """For search text only. Never overwrite the original evidence."""
    return " ".join(text.split())


@dataclass(frozen=True)
class Document:
    document_id: str
    question_id: str
    title: str
    sentences: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("document_id", "question_id", "title"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Document.{name} must be a nonempty string.")
        if not isinstance(self.sentences, tuple) or any(
            not isinstance(sentence, str) for sentence in self.sentences
        ):
            raise ValueError("Document.sentences must be a tuple of strings.")

    @property
    def text(self) -> str:
        """A display view; individual source sentences remain unchanged."""
        return "\n".join(self.sentences)

    @property
    def search_text(self) -> str:
        """Title plus paragraph, with whitespace normalized for retrieval."""
        return normalize_whitespace(f"{self.title}\n{self.text}")

    def sentence(self, index: int) -> str:
        # Explicitly reject negative indices rather than indexing from the end.
        if type(index) is not int or not 0 <= index < len(self.sentences):
            raise IndexError(f"Invalid sentence index {index!r}: {self.document_id}")
        return self.sentences[index]


class DocumentStore:
    def __init__(self, question_id: str, documents: Iterable[Document]) -> None:
        if not isinstance(question_id, str) or not question_id.strip():
            raise ValueError("question_id must be a nonempty string.")
        self.question_id = question_id
        self._documents: dict[str, Document] = {}
        for document in documents:
            if document.question_id != question_id:
                raise ValueError("Cannot mix documents from different questions.")
            if document.document_id in self._documents:
                raise ValueError(f"Duplicate document ID: {document.document_id}")
            self._documents[document.document_id] = document
        if not self._documents:
            raise ValueError("A question's document pool cannot be empty.")

    def __len__(self) -> int:
        return len(self._documents)

    def all_documents(self) -> tuple[Document, ...]:
        """Return the original pool order, without ranking or filtering."""
        return tuple(self._documents.values())

    def get(self, document_id: str) -> Document:
        try:
            return self._documents[document_id]
        except KeyError as exc:
            raise KeyError(
                f"Unknown document {document_id!r} for {self.question_id}"
            ) from exc