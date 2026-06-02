from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import requests
import time


class LLMError(Exception):
    pass


class LLMClient(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        ...


def _auth_headers(api_key: str) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


class OpenAIChatClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = ""):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/") if base_url else "https://api.openai.com/v1"
        self.last_response_info = {}

    def chat(self, messages, temperature=0.3):
        url = f"{self.base_url}/chat/completions"
        started = time.perf_counter()
        try:
            resp = requests.post(
                url,
                headers=_auth_headers(self.api_key),
                json={"model": self.model, "messages": messages, "temperature": temperature},
                timeout=120,
            )
            self.last_response_info = {
                "method": "POST",
                "url": url,
                "status": resp.status_code,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.Timeout:
            self.last_response_info = {
                "method": "POST",
                "url": url,
                "status": "timeout",
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }
            raise LLMError("LLM request timed out after 120s")
        except requests.HTTPError as e:
            detail = e.response.text if e.response is not None else str(e)
            raise LLMError(f"LLM API error ({e.response.status_code}): {detail}")


class OpenAIResponsesClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = ""):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/") if base_url else "https://api.openai.com/v1"
        self.last_response_info = {}

    def chat(self, messages, temperature=0.3):
        url = f"{self.base_url}/responses"
        started = time.perf_counter()
        instructions = "\n\n".join(m.get("content", "") for m in messages if m.get("role") == "system")
        input_messages = [m for m in messages if m.get("role") != "system"]
        body = {
            "model": self.model,
            "input": input_messages,
            "temperature": temperature,
        }
        if instructions:
            body["instructions"] = instructions
        try:
            resp = requests.post(
                url,
                headers=_auth_headers(self.api_key),
                json=body,
                timeout=120,
            )
            self.last_response_info = {
                "method": "POST",
                "url": url,
                "status": resp.status_code,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }
            resp.raise_for_status()
            return self._extract_text(resp.json())
        except requests.Timeout:
            self.last_response_info = {
                "method": "POST",
                "url": url,
                "status": "timeout",
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }
            raise LLMError("LLM request timed out after 120s")
        except requests.HTTPError as e:
            detail = e.response.text if e.response is not None else str(e)
            raise LLMError(f"LLM API error ({e.response.status_code}): {detail}")

    @staticmethod
    def _extract_text(payload) -> str:
        if payload.get("output_text"):
            return payload["output_text"]
        texts = []
        for item in payload.get("output", []) or []:
            for content in item.get("content", []) or []:
                if content.get("type") in ("output_text", "text") and content.get("text"):
                    texts.append(content["text"])
        if texts:
            return "\n".join(texts)
        raise LLMError("LLM Responses API returned no output text")


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307", base_url: str = ""):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/") if base_url else "https://api.anthropic.com"
        self.last_response_info = {}

    def chat(self, messages, temperature=0.3):
        system_msg = ""
        user_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                user_messages.append(m)

        body = {
            "model": self.model,
            "messages": user_messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }
        if system_msg:
            body["system"] = system_msg

        url = f"{self.base_url}/v1/messages"
        started = time.perf_counter()
        try:
            resp = requests.post(
                url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=120,
            )
            self.last_response_info = {
                "method": "POST",
                "url": url,
                "status": resp.status_code,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        except requests.Timeout:
            self.last_response_info = {
                "method": "POST",
                "url": url,
                "status": "timeout",
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }
            raise LLMError("LLM request timed out after 120s")
        except requests.HTTPError as e:
            detail = e.response.text if e.response is not None else str(e)
            raise LLMError(f"LLM API error ({e.response.status_code}): {detail}")


def create_llm_client(config) -> LLMClient:
    api_type = (getattr(config, "llm_api_type", "") or "").lower()
    if api_type == "anthropic_messages":
        return AnthropicClient(config.llm_api_key, config.llm_model, config.llm_base_url)
    if api_type == "openai_responses":
        return OpenAIResponsesClient(config.llm_api_key, config.llm_model, config.llm_base_url)
    return OpenAIChatClient(config.llm_api_key, config.llm_model, config.llm_base_url)
