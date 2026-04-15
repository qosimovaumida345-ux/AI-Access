# ============================================================
# SHADOWFORGE OS — HUGGINGFACE INFERENCE CLIENT
# HuggingFace: Free inference API for open models.
# Good fallback. Rate limited but always free.
# API docs: https://huggingface.co/docs/api-inference
# ============================================================

import time
import json
from typing import Dict, List, Optional, Any, Generator

import httpx

from core.logger import get_logger
from ai_providers.provider_manager import (
    RateLimitError, ProviderAuthError, ProviderTimeoutError
)

logger = get_logger("AI.HuggingFace")

HF_BASE_URL     = "https://api-inference.huggingface.co"
HF_CHAT_URL     = "https://huggingface.co/api/inference-proxy/together"

# Models with good free inference
HF_FREE_MODELS = [
    "mistralai/Mistral-7B-Instruct-v0.3",
    "HuggingFaceH4/zephyr-7b-beta",
    "microsoft/Phi-3-mini-4k-instruct",
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.2-3B-Instruct",
]

# Models with OpenAI-compatible chat endpoint
HF_CHAT_MODELS = [
    "meta-llama/Llama-3.1-70B-Instruct",
    "meta-llama/Llama-3.2-11B-Vision-Instruct",
    "Qwen/Qwen2.5-72B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
]


class HuggingFaceClient:
    """
    HuggingFace Inference API client.
    Uses both the standard inference API and the
    OpenAI-compatible chat endpoint where available.
    """

    def __init__(
        self,
        api_key:  str,
        model:    Optional[str] = None,
        timeout:  int = 60,
    ):
        if not api_key or not api_key.strip():
            raise ProviderAuthError("HuggingFace API key is empty.")

        self._api_key    = api_key.strip()
        self._model      = model or HF_FREE_MODELS[0]
        self._timeout    = timeout
        self._call_count = 0
        self._token_count= 0
        self._error_count= 0

        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type":  "application/json",
            "User-Agent":    "ShadowForge-OS/2.5",
        }

        self._client = httpx.Client(
            headers = self._headers,
            timeout = httpx.Timeout(connect=10.0, read=float(timeout), write=10.0, pool=5.0),
        )

        logger.info(f"HuggingFaceClient initialized. Model: {self._model}")

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert chat messages to a single prompt string for HF."""
        parts = []
        for msg in messages:
            role    = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"<|system|>\n{content}</s>")
            elif role == "user":
                parts.append(f"<|user|>\n{content}</s>")
            elif role == "assistant":
                parts.append(f"<|assistant|>\n{content}</s>")
        parts.append("<|assistant|>")
        return "\n".join(parts)

    def complete(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int   = 2048,
        temperature: float = 0.7,
        timeout:     int   = 60,
        model:       Optional[str] = None,
    ) -> Dict[str, Any]:

        use_model  = model or self._model
        start_time = time.perf_counter()

        # Try OpenAI-compatible chat endpoint first
        if use_model in HF_CHAT_MODELS:
            try:
                return self._chat_complete(
                    messages, max_tokens, temperature, timeout, use_model
                )
            except Exception as e:
                logger.warning(
                    f"HF chat endpoint failed for {use_model}: {e}. "
                    f"Falling back to inference API."
                )

        # Try standard inference API
        models_to_try = [use_model] + [
            m for m in HF_FREE_MODELS if m != use_model
        ]

        last_error = None

        for current_model in models_to_try[:3]:  # Limit to 3 tries
            prompt = self._messages_to_prompt(messages)
            url    = f"{HF_BASE_URL}/models/{current_model}"

            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens":  min(max_tokens, 2048),
                    "temperature":     max(0.01, temperature),
                    "do_sample":       temperature > 0,
                    "return_full_text":False,
                },
                "options": {
                    "wait_for_model": True,
                    "use_cache":      False,
                },
            }

            try:
                response = self._client.post(
                    url, json=payload, timeout=timeout
                )

                latency_ms = (time.perf_counter() - start_time) * 1000

                if response.status_code == 401:
                    raise ProviderAuthError(
                        "Invalid HuggingFace token. "
                        "Check HUGGINGFACE_API_KEY in .env"
                    )
                if response.status_code == 429:
                    raise RateLimitError("HuggingFace rate limit hit.")
                if response.status_code == 503:
                    logger.warning(f"HF model {current_model} loading, skip")
                    last_error = Exception(f"Model loading: {current_model}")
                    continue
                if response.status_code != 200:
                    last_error = Exception(
                        f"HF {response.status_code}: {response.text[:200]}"
                    )
                    continue

                data = response.json()

                if isinstance(data, list) and data:
                    content = data[0].get("generated_text", "")
                elif isinstance(data, dict):
                    content = data.get("generated_text", "")
                else:
                    content = str(data)

                content = content.strip()

                self._call_count += 1

                logger.debug(
                    f"HuggingFace OK: {current_model} | "
                    f"latency={latency_ms:.0f}ms"
                )

                return {
                    "content":    content,
                    "model":      current_model,
                    "tokens":     len(content.split()),  # Approximate
                    "latency_ms": latency_ms,
                }

            except (ProviderAuthError, RateLimitError):
                raise
            except httpx.TimeoutException:
                last_error = ProviderTimeoutError(f"HF timeout: {current_model}")
                continue
            except Exception as e:
                last_error = e
                self._error_count += 1
                logger.warning(f"HF error ({current_model}): {e}")
                continue

        raise last_error or Exception("HuggingFace: all models failed")

    def _chat_complete(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int,
        temperature: float,
        timeout:     int,
        model:       str,
    ) -> Dict[str, Any]:
        """Use HuggingFace OpenAI-compatible chat endpoint."""
        url     = f"https://api-inference.huggingface.co/models/{model}/v1/chat/completions"
        payload = {
            "model":       model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "stream":      False,
        }

        response = self._client.post(url, json=payload, timeout=timeout)

        if response.status_code == 401:
            raise ProviderAuthError("Invalid HuggingFace token.")
        if response.status_code != 200:
            raise Exception(f"HF chat {response.status_code}: {response.text[:200]}")

        data    = response.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        tokens  = data.get("usage", {}).get("total_tokens", 0)

        self._call_count  += 1
        self._token_count += tokens

        return {
            "content": content,
            "model":   model,
            "tokens":  tokens,
        }

    def stream(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int   = 2048,
        temperature: float = 0.7,
        model:       Optional[str] = None,
    ) -> Generator[str, None, None]:
        """HuggingFace doesn't support true streaming in basic API.
        Fall back to complete and yield all at once."""
        try:
            result = self.complete(messages, max_tokens, temperature, model=model)
            yield result.get("content", "")
        except Exception as e:
            yield f"[ERROR] HuggingFace: {str(e)[:100]}"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "provider":     "huggingface",
            "model":        self._model,
            "total_calls":  self._call_count,
            "total_tokens": self._token_count,
        }

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass