"""LLM-backed question decomposer for RAIR."""

from typing import Any

from src.llm.ollama_client import OllamaClient
from src.llm.prompts import (
    RAIR_DECOMPOSER_SCHEMA,
    RAIR_DECOMPOSER_SYSTEM_PROMPT,
)
from src.rair.state import Gap, RAIRState


class DecompositionError(ValueError):
    """Raised when a proposed decomposition is structurally invalid."""


class RAIRDecomposer:
    def __init__(
        self,
        client: OllamaClient,
    ) -> None:
        self.client = client

    def decompose(
        self,
        state: RAIRState,
    ) -> list[Gap]:
        """Generate, validate, and install gaps into an empty RAIR state."""

        if state.gaps:
            raise DecompositionError(
                "State already contains gaps."
            )

        response = self.client.chat(
            RAIR_DECOMPOSER_SYSTEM_PROMPT,
            (
                "Original question:\n"
                f"{state.question}\n\n"
                "Identify only the information gaps "
                "required to answer it."
            ),
            schema=RAIR_DECOMPOSER_SCHEMA,
            temperature=0.0,
        )

        payload = response.json_object()

        gaps = self.parse_payload(
            payload
        )

        for gap in gaps:
            state.add_gap(gap)

        return gaps

    @staticmethod
    def parse_payload(
        payload: dict[str, Any],
    ) -> list[Gap]:
        """Validate an LLM decomposition independently of Ollama."""

        if set(payload) != {"gaps"}:
            raise DecompositionError(
                "Decomposition must contain exactly "
                "the 'gaps' field."
            )

        raw_gaps = payload["gaps"]

        if not isinstance(raw_gaps, list):
            raise DecompositionError(
                "'gaps' must be a list."
            )

        if not 1 <= len(raw_gaps) <= 6:
            raise DecompositionError(
                "Decomposition must contain "
                "between 1 and 6 gaps."
            )

        gaps: list[Gap] = []
        seen_ids: set[str] = set()

        for index, raw in enumerate(
            raw_gaps,
            start=1,
        ):
            if not isinstance(raw, dict):
                raise DecompositionError(
                    f"Gap {index} must be an object."
                )

            expected_fields = {
                "gap_id",
                "description",
                "priority",
                "depends_on",
            }

            if set(raw) != expected_fields:
                raise DecompositionError(
                    f"Gap {index} has invalid fields."
                )

            expected_id = f"G{index}"

            if raw["gap_id"] != expected_id:
                raise DecompositionError(
                    f"Expected gap ID {expected_id}, "
                    f"got {raw['gap_id']!r}."
                )

            depends_on = raw["depends_on"]

            if not isinstance(
                depends_on,
                list,
            ):
                raise DecompositionError(
                    f"{expected_id}.depends_on "
                    "must be a list."
                )

            if len(depends_on) != len(
                set(depends_on)
            ):
                raise DecompositionError(
                    f"{expected_id} contains "
                    "duplicate dependencies."
                )

            for dependency in depends_on:
                if not isinstance(
                    dependency,
                    str,
                ):
                    raise DecompositionError(
                        f"{expected_id} dependency "
                        "IDs must be strings."
                    )

                if dependency not in seen_ids:
                    raise DecompositionError(
                        f"{expected_id} depends on "
                        f"unknown or future gap "
                        f"{dependency!r}."
                    )

            try:
                gap = Gap(
                    gap_id=raw["gap_id"],
                    description=raw["description"],
                    priority=raw["priority"],
                    depends_on=tuple(
                        depends_on
                    ),
                )
            except (
                TypeError,
                AttributeError,
                ValueError,
            ) as exc:
                raise DecompositionError(
                    f"Invalid {expected_id}: {exc}"
                ) from exc

            gaps.append(gap)
            seen_ids.add(
                gap.gap_id
            )

        RAIRDecomposer._validate_dependency_graph(
            gaps
        )

        return gaps

    @staticmethod
    def _validate_dependency_graph(
        gaps: list[Gap],
    ) -> None:
        """Defensive cycle check for the dependency graph."""

        dependencies = {
            gap.gap_id: set(
                gap.depends_on
            )
            for gap in gaps
        }

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(
            gap_id: str,
        ) -> None:
            if gap_id in visiting:
                raise DecompositionError(
                    "Gap dependency cycle detected."
                )

            if gap_id in visited:
                return

            visiting.add(gap_id)

            for dependency in dependencies[
                gap_id
            ]:
                visit(dependency)

            visiting.remove(gap_id)
            visited.add(gap_id)

        for gap in gaps:
            visit(
                gap.gap_id
            )