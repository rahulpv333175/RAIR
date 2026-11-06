"""Small synchronous Ollama client shared by RAIR and KAIR."""

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener

from src.evaluation.budget import RunBudget


class OllamaError(RuntimeError):
    """Connection, server, or incomplete-generation error."""


def summarize_calls(calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Shared accounting, including failed generation attempts and missing counts."""
    responses = [call["raw"] or {} for call in calls]
    return {
        "llm_calls": len(calls),
        "prompt_tokens": sum(raw.get("prompt_eval_count", 0) for raw in responses),
        "completion_tokens": sum(raw.get("eval_count", 0) for raw in responses),
        "token_counts_complete": all(
            "prompt_eval_count" in raw and "eval_count" in raw for raw in responses
        ),
        "llm_elapsed_seconds": sum(call["elapsed_seconds"] for call in calls),
    }


@dataclass
class LLMResponse:
    content: str
    elapsed_seconds: float
    request: dict[str, Any]
    raw: dict[str, Any]

    def json_object(self) -> dict[str, Any]:
        """Parse without repair. Schema/semantic validation belongs to the caller."""
        try:
            value = json.loads(self.content)
        except json.JSONDecodeError as exc:
            raise OllamaError(
                f"Response is not valid JSON: {self.content[:300]!r}"
            ) from exc
        if not isinstance(value, dict):
            raise OllamaError("Expected a JSON object, not an array or scalar.")
        return value


class OllamaClient:
    def __init__(self, settings: dict[str, Any]) -> None:
        self.config = dict(settings["llm"])
        self.model = self.config["model"]
        self.base_url = self.config["base_url"].rstrip("/")
        self.timeout = float(self.config["timeout_seconds"])
        self.seed = int(settings["project"]["seed"])
        self.calls: list[dict[str, Any]] = []
        self.budget: RunBudget | None = None
        self.generation_temperature: float | None = None

        url = urlparse(self.base_url)
        if url.scheme != "http" or url.hostname not in {
            "localhost", "127.0.0.1", "::1"
        }:
            raise ValueError("This client requires a local HTTP Ollama URL.")
        if self.config["provider"] != "ollama":
            raise ValueError("llm.provider must be 'ollama'.")
        if self.config["max_concurrent_requests"] != 1:
            raise ValueError("Initial experiments require sequential requests.")
        if type(self.config["think"]) is not bool:
            raise ValueError("llm.think must be true or false, without quotes.")
        if self.timeout <= 0:
            raise ValueError("timeout_seconds must be positive.")

        # Do not route localhost requests through system/corporate proxies.
        self._http = build_opener(ProxyHandler({}))

    def _request(
        self, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST" if payload is not None else "GET",
        )
        try:
            with self._http.open(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise OllamaError(f"HTTP {exc.code} on {path}: {detail}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise OllamaError(
                f"Ollama request failed at {self.base_url}: {exc}"
            ) from exc
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise OllamaError("Ollama returned an invalid JSON response.") from exc

        if not isinstance(result, dict):
            raise OllamaError("Ollama API response must be a JSON object.")
        if result.get("error"):
            raise OllamaError(str(result["error"]))
        return result

    def check_ready(self) -> dict[str, Any]:
        """Check the server and exact installed model; never auto-download."""
        server = self._request("/api/version")
        models = self._request("/api/tags").get("models", [])
        for model in models:
            if self.model in (model.get("name"), model.get("model")):
                return {"server": server, "model": model}
        raise OllamaError(
            f"Model {self.model!r} is not installed. "
            f"Run: ollama pull {self.model}"
        )

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        schema: dict[str, Any] | None = None,
        temperature: float | None = None,
        seed: int | None = None,
        num_predict: int | None = None,
        final_answer: bool = False,
    ) -> LLMResponse:
        """One independent call. No chat history, retries, or JSON repair."""
        options = {
            "num_ctx": int(self.config["num_ctx"]),
            "num_predict": int(
                self.config["num_predict"] if num_predict is None else num_predict
            ),
            "temperature": float(
                self.config["temperature"] if temperature is None else temperature
            ),
            "seed": self.seed if seed is None else int(seed),
        }
        if not final_answer and self.generation_temperature is not None:
            options["temperature"] = self.generation_temperature
        if not 0 < options["num_predict"] < options["num_ctx"]:
            raise ValueError("Require 0 < num_predict < num_ctx.")

        if schema is not None:
            system_prompt += "\nJSON schema:\n" + json.dumps(schema)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "think": self.config["think"],
            "keep_alive": self.config["keep_alive"],
            "options": options,
        }
        if schema is not None:
            payload["format"] = schema

        if self.budget is not None:
            self.budget.consume_llm(final_answer=final_answer)
        call: dict[str, Any] = {"request": payload, "raw": None, "error": None,
                                "final_answer": final_answer}
        self.calls.append(call)
        start = time.perf_counter()
        try:
            raw = self._request("/api/chat", payload)
            call["raw"] = raw
            if raw.get("done") is not True:
                raise OllamaError("Ollama did not return a completed response.")
            if raw.get("done_reason") == "length":
                raise OllamaError(
                    "Generation hit its token limit; response not accepted. "
                    f"num_predict={options['num_predict']}"
                )
            message = raw.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, str) or not content.strip():
                raise OllamaError("Empty final answer; thinking is not an answer.")
            return LLMResponse(content.strip(), time.perf_counter() - start, payload, raw)
        except OllamaError as exc:
            call["error"] = str(exc)
            raise
        finally:
            call["elapsed_seconds"] = time.perf_counter() - start
