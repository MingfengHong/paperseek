from abc import ABC, abstractmethod
from typing import List, Dict
import os
import requests
import time


class LLMError(Exception):
    pass


def _llm_timeout_seconds() -> int:
    try:
        return max(30, int(os.environ.get("LLM_TIMEOUT_SECONDS", "180")))
    except (TypeError, ValueError):
        return 180


def _llm_max_tokens() -> int:
    try:
        return max(0, int(os.environ.get("LLM_MAX_TOKENS", "2048")))
    except (TypeError, ValueError):
        return 2048


DEFAULT_LLM_TIMEOUT_SECONDS = _llm_timeout_seconds()
DEFAULT_LLM_MAX_TOKENS = _llm_max_tokens()


class LLMClient(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        ...


def _auth_headers(api_key: str) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


MODELSCOPE_QUOTA_HEADERS = {
    "user_limit": "modelscope-ratelimit-requests-limit",
    "user_remaining": "modelscope-ratelimit-requests-remaining",
    "model_limit": "modelscope-ratelimit-model-requests-limit",
    "model_remaining": "modelscope-ratelimit-model-requests-remaining",
}


def extract_modelscope_quota(headers) -> Dict[str, str]:
    quota = {}
    for key, header_name in MODELSCOPE_QUOTA_HEADERS.items():
        value = headers.get(header_name) if headers else None
        if value is not None and str(value).strip():
            quota[key] = str(value).strip()
    return quota


def format_modelscope_quota(quota: Dict[str, str]) -> str:
    if not quota:
        return ""
    user_remaining = quota.get("user_remaining", "?")
    user_limit = quota.get("user_limit", "?")
    model_remaining = quota.get("model_remaining", "?")
    model_limit = quota.get("model_limit", "?")
    return f"user remaining {user_remaining}/{user_limit}; model remaining {model_remaining}/{model_limit}"


class OpenAIChatClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = "", max_tokens: int = DEFAULT_LLM_MAX_TOKENS):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/") if base_url else "https://api.openai.com/v1"
        self.max_tokens = max(0, int(max_tokens or 0))
        self.last_response_info = {}

    def chat(self, messages, temperature=0.3):
        url = f"{self.base_url}/chat/completions"
        started = time.perf_counter()
        body = {"model": self.model, "messages": messages, "temperature": temperature}
        if self.max_tokens:
            body["max_tokens"] = self.max_tokens
        try:
            resp = requests.post(
                url,
                headers=_auth_headers(self.api_key),
                json=body,
                timeout=DEFAULT_LLM_TIMEOUT_SECONDS,
            )
            self.last_response_info = {
                "method": "POST",
                "url": url,
                "status": resp.status_code,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "quota": extract_modelscope_quota(resp.headers),
            }
            resp.raise_for_status()
            return _extract_openai_chat_content(resp.json())
        except requests.Timeout:
            self.last_response_info = {
                "method": "POST",
                "url": url,
                "status": "timeout",
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }
            raise LLMError(f"LLM request timed out after {DEFAULT_LLM_TIMEOUT_SECONDS}s")
        except requests.HTTPError as e:
            detail = e.response.text if e.response is not None else str(e)
            quota_text = format_modelscope_quota((self.last_response_info or {}).get("quota", {}))
            quota_suffix = f" Quota: {quota_text}." if quota_text else ""
            status = e.response.status_code if e.response is not None else "unknown"
            raise LLMError(f"LLM API error ({status}): {detail}{quota_suffix}")
        except requests.RequestException as e:
            self.last_response_info = {
                "method": "POST",
                "url": url,
                "status": "request_error",
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }
            raise LLMError(f"LLM network error: {e}") from e
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise LLMError(f"LLM Chat Completions response did not contain message content: {e}") from e


class OpenAIResponsesClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = "", max_tokens: int = DEFAULT_LLM_MAX_TOKENS):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/") if base_url else "https://api.openai.com/v1"
        self.max_tokens = max(0, int(max_tokens or 0))
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
        if self.max_tokens:
            body["max_output_tokens"] = self.max_tokens
        if instructions:
            body["instructions"] = instructions
        try:
            resp = requests.post(
                url,
                headers=_auth_headers(self.api_key),
                json=body,
                timeout=DEFAULT_LLM_TIMEOUT_SECONDS,
            )
            self.last_response_info = {
                "method": "POST",
                "url": url,
                "status": resp.status_code,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "quota": extract_modelscope_quota(resp.headers),
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
            raise LLMError(f"LLM request timed out after {DEFAULT_LLM_TIMEOUT_SECONDS}s")
        except requests.HTTPError as e:
            detail = e.response.text if e.response is not None else str(e)
            quota_text = format_modelscope_quota((self.last_response_info or {}).get("quota", {}))
            quota_suffix = f" Quota: {quota_text}." if quota_text else ""
            status = e.response.status_code if e.response is not None else "unknown"
            raise LLMError(f"LLM API error ({status}): {detail}{quota_suffix}")
        except requests.RequestException as e:
            self.last_response_info = {
                "method": "POST",
                "url": url,
                "status": "request_error",
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }
            raise LLMError(f"LLM network error: {e}") from e

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
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307", base_url: str = "", max_tokens: int = DEFAULT_LLM_MAX_TOKENS):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/") if base_url else "https://api.anthropic.com"
        self.max_tokens = max(1, int(max_tokens or DEFAULT_LLM_MAX_TOKENS))
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
            "max_tokens": self.max_tokens,
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
                timeout=DEFAULT_LLM_TIMEOUT_SECONDS,
            )
            self.last_response_info = {
                "method": "POST",
                "url": url,
                "status": resp.status_code,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "quota": extract_modelscope_quota(resp.headers),
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
            raise LLMError(f"LLM request timed out after {DEFAULT_LLM_TIMEOUT_SECONDS}s")
        except requests.HTTPError as e:
            detail = e.response.text if e.response is not None else str(e)
            quota_text = format_modelscope_quota((self.last_response_info or {}).get("quota", {}))
            quota_suffix = f" Quota: {quota_text}." if quota_text else ""
            status = e.response.status_code if e.response is not None else "unknown"
            raise LLMError(f"LLM API error ({status}): {detail}{quota_suffix}")
        except requests.RequestException as e:
            self.last_response_info = {
                "method": "POST",
                "url": url,
                "status": "request_error",
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }
            raise LLMError(f"LLM network error: {e}") from e


def create_llm_client(config) -> LLMClient:
    api_type = (getattr(config, "llm_api_type", "") or "").lower()
    max_tokens = getattr(config, "llm_max_tokens", DEFAULT_LLM_MAX_TOKENS)
    if api_type == "anthropic_messages":
        return AnthropicClient(config.llm_api_key, config.llm_model, config.llm_base_url, max_tokens=max_tokens)
    if api_type == "openai_responses":
        return OpenAIResponsesClient(config.llm_api_key, config.llm_model, config.llm_base_url, max_tokens=max_tokens)
    return OpenAIChatClient(config.llm_api_key, config.llm_model, config.llm_base_url, max_tokens=max_tokens)


def _extract_openai_chat_content(payload) -> str:
    choice = (payload.get("choices") or [])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if content:
        return content
    reasoning = message.get("reasoning_content")
    if reasoning:
        return reasoning
    delta = choice.get("delta") or {}
    if delta.get("content"):
        return delta["content"]
    raise KeyError("choices[0].message.content")
