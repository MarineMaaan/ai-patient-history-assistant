"""Rules demo and real local-only Ollama adapter; no hosted fallback or tools."""
import json
from typing import Protocol
from urllib.parse import urlparse

import httpx

from .models import Claim, Clarification, Draft
from .prompts import ANSWER_SYSTEM, CLARIFY_SYSTEM
from .retrieval import Search, supports_claim


class ProviderError(RuntimeError):
    pass


class Provider(Protocol):
    name: str
    model: str

    def answer(self, question: str, search: Search) -> Draft: ...
    def clarify(self, last: dict, asked: list[str]) -> Clarification: ...


class OfflineProvider:
    name = "Offline rules-based demo — no LLM running."
    model = "deterministic-rules-v1"

    def answer(self, question: str, search: Search) -> Draft:
        claims = [Claim(text=r["answer"], source_ids=[r["id"]]) for r in search.evidence
                  if r["answer_state"] in ("answered", "uncertain") and supports_claim(question, r)]
        return Draft(claims=claims, outcome="supported" if claims else "missing")

    def clarify(self, last: dict, asked: list[str]) -> Clarification:
        question = "What date or approximate period do you remember, if any?"
        if last["answer_state"] == "uncertain" and not last["event_wording"] and question not in asked:
            return Clarification(question=question)
        return Clarification()


class OllamaProvider:
    name = "Local Ollama (no hosted fallback)"

    def __init__(self, endpoint: str, model: str, timeout: float = 30, transport=None):
        url = urlparse(endpoint)
        if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"} or url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
            raise ProviderError("Only a plain HTTP loopback Ollama endpoint is allowed.")
        if not model or "cloud" in model.lower() or len(model) > 200:
            raise ProviderError("Configure an exact installed local model tag; cloud tags are refused.")
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.timeout = min(max(timeout, 1), 60)
        self.transport = transport

    def _request(self, method: str, path: str, payload=None):
        # No proxy environment, redirects, or credentials; one bounded retry.
        for attempt in range(2):
            try:
                with httpx.Client(timeout=self.timeout, trust_env=False, follow_redirects=False, transport=self.transport) as client:
                    with client.stream(method, self.endpoint + path, json=payload) as response:
                        response.raise_for_status()
                        chunks, size = [], 0
                        for chunk in response.iter_bytes():
                            size += len(chunk)
                            if size > 1_000_000:
                                raise ProviderError("Ollama response exceeded the byte limit.")
                            chunks.append(chunk)
                        data = json.loads(b"".join(chunks))
                        if not isinstance(data, dict):
                            raise ValueError("Expected a JSON object")
                        return data
            except (httpx.HTTPError, ValueError):
                if attempt:
                    # Do not include response bodies or prompts in error traces.
                    raise ProviderError("Ollama unavailable, timed out, or returned invalid JSON.") from None

    def confirm_local(self):
        tags = self._request("GET", "/api/tags")
        entry = next((m for m in tags.get("models", []) if m.get("name") == self.model), None)
        if not entry or not isinstance(entry.get("size"), int) or entry["size"] < 1_000_000:
            raise ProviderError("Selected model is not an installed local weight artifact.")
        details = self._request("POST", "/api/show", {"model": self.model})
        # Cloud aliases can live behind a loopback endpoint. Check metadata too.
        for data in (entry, details):
            if any(data.get(k) for k in ("remote_host", "remote_model", "remote")):
                raise ProviderError("Remote/cloud-backed model metadata refused.")
        if not details.get("model_info") or "completion" not in details.get("capabilities", []):
            raise ProviderError("Local completion-model metadata could not be confirmed.")

    def _generate(self, schema, system: str, data: dict):
        encoded = json.dumps(data, ensure_ascii=False)
        if len(encoded) > 60000:
            raise ProviderError("Model input exceeded the context limit; no silent truncation.")
        self.confirm_local()  # Recheck every generation; never auto-pull a model.
        result = self._request("POST", "/api/chat", {
            "model": self.model, "stream": False, "format": schema.model_json_schema(),
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": encoded}],
            "options": {"temperature": 0, "num_predict": 4096, "num_ctx": 32768},
            "keep_alive": "0",
        })
        try:
            if result.get("model") != self.model or not result.get("done"):
                raise ValueError("Incomplete or substituted model response")
            return schema.model_validate_json(result["message"]["content"])
        except (ValueError, KeyError, TypeError):
            raise ProviderError("Ollama structured output failed validation.") from None

    def answer(self, question: str, search: Search) -> Draft:
        return self._generate(Draft, ANSWER_SYSTEM, {"question": question, "original_records": search.evidence})

    def clarify(self, last: dict, asked: list[str]) -> Clarification:
        return self._generate(Clarification, CLARIFY_SYSTEM, {"last_original_record": last, "asked_questions": asked})
