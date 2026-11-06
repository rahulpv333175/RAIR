"""Two synthetic evidence tests. This is not a benchmark or a verifier."""

import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from src.llm.ollama_client import OllamaClient, OllamaError
from src.llm.prompts import SMOKE_SCHEMA, SMOKE_SYSTEM_PROMPT
from src.settings import PROJECT_ROOT, load_settings


QUESTION = "In which city was the author of The Glass Orchard born?"
CASES = (
    (
        "supported_two_hop",
        "[D1] The Glass Orchard was written by Mira Solen.\n"
        "[D2] Mira Solen was born in the city of Nerava.",
        {"answer": "Nerava", "citations": ["D1", "D2"], "abstain": False},
    ),
    (
        "missing_evidence",
        "[D1] The Glass Orchard was written by Mira Solen.",
        {"answer": "", "citations": [], "abstain": True},
    ),
)


def validate(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    if set(actual) != {"answer", "citations", "abstain"}:
        raise ValueError("Response must contain exactly the three schema fields.")
    if not isinstance(actual["answer"], str) or type(actual["abstain"]) is not bool:
        raise ValueError("answer must be a string and abstain must be a boolean.")
    citations = actual["citations"]
    if not isinstance(citations, list) or any(
        not isinstance(item, str) for item in citations
    ):
        raise ValueError("citations must be a list of strings.")
    if (
        actual["answer"] != expected["answer"]
        or actual["abstain"] != expected["abstain"]
        or sorted(citations) != sorted(expected["citations"])
    ):
        raise ValueError(f"Unexpected result. Expected: {expected}; got: {actual}")


def main() -> int:
    output = PROJECT_ROOT / "results" / "phase2_llm_check.json"
    report: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": False,
        "tests": [],
    }
    try:
        settings = load_settings()
        report["settings"] = settings
        client = OllamaClient(settings)
        ready = client.check_ready()
        report["environment"] = ready
        print(f"[OK] Ollama server: {ready['server'].get('version', 'unknown')}")
        print(f"[OK] Installed model: {client.model}")
        print(f"[INFO] Model digest: {ready['model'].get('digest', 'unavailable')}")
        print("[INFO] Smoke-test temperature: 0.0; calls run sequentially")

        for name, evidence, expected in CASES:
            print(f"\n[RUN] {name}", flush=True)
            response = client.chat(
                SMOKE_SYSTEM_PROMPT,
                f"Question: {QUESTION}\n\nEvidence:\n{evidence}",
                schema=SMOKE_SCHEMA,
                temperature=0.0,
                seed=settings["project"]["seed"],
            )
            record = {"name": name, "passed": False, **asdict(response)}
            report["tests"].append(record)
            print(response.content)
            parsed = response.json_object()
            validate(parsed, expected)
            record["passed"] = True
            print(
                f"[PASS] {name} | {response.elapsed_seconds:.2f}s | "
                f"prompt tokens={response.raw.get('prompt_eval_count', 'unknown')} | "
                f"output tokens={response.raw.get('eval_count', 'unknown')}"
            )
        report["passed"] = True
    except (OllamaError, OSError, ValueError, KeyError, TypeError) as exc:
        report["error"] = str(exc)
        print(f"[FAIL] {exc}", file=sys.stderr)

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        print(f"[FAIL] Could not save diagnostic report: {exc}", file=sys.stderr)
        return 1
    print(f"\n[SAVED] {output}")
    if report["passed"]:
        print("PHASE 2 PASSED")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())