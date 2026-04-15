# ============================================================
# SHADOWFORGE OS — TOGETHER AI CLIENT
# Together AI: Fast inference, generous free tier.
# LLaMA 3.3 70B Turbo Free available.
# API docs: https://docs.together.ai
# ============================================================

import time
import json
from typing import Dict, List, Optional, Any, Generator

import httpx

from core.logger import get_logger
from ai_providers.provider_manager import (
    RateLimitError, ProviderAuthError, ProviderTimeoutError
)

logger = get_logger("AI.Together")

TOGETHER_BASE_URL = "https://api.together.xyz/v1"

TOGETHER_FREE_MODELS = [
    "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    "meta-llama/Llama-Vision-Free",
    "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
]

TOGETHER_MODELS = [
    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    "mistralai/Mixtral-8x22B-Instruct-v0.1",
    "Qwen/Qwen2.5-72B-Instruct-Turbo",
] + TOGETHER_FREE_MODELS


class TogetherClient:
    """
    Together AI client.
    OpenAI-compatible API.
    Includes free models with no credit required.
    """

    def __init__(
        self,
        api_key:  str,
        model:    Optional[str] = None,
        timeout:  int = 60,
    ):
        if not api_key or not api_key.strip():
            raise ProviderAuthError("Together AI API key is empty.")

        self._api_key    = api_key.strip()
        self._model      = model or TOGETHER_FREE_MODELS[0]
        self._timeout    = timeout
        self._call_count = 0
        self._token_count= 0
        self._error_count= 0

        self._client = httpx.Client(
            base_url = TOGETHER_BASE_URL,
            headers  = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type":  "application/json",
                "User-Agent":    "ShadowForge-OS/2.5",
            },
            timeout = httpx.Timeout(connect=10.0, read=float(timeout), write=10.0, pool=5.0),
        )

        logger.info(f"TogetherClient initialized. Model: {self._model}")

    def complete(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int   = 4096,
        temperature: float = 0.7,
        timeout:     int   = 60,
        model:       Optional[str] = None,
    ) -> Dict[str, Any]:

        use_model  = model or self._model
        start_time = time.perf_counter()

        # Try free models first, then paid
        models_to_try = [use_model]
        if use_model not in TOGETHER_FREE_MODELS:
            models_to_try += TOGETHER_FREE_MODELS
        else:
            other_free = [m for m in TOGETHER_FREE_MODELS if m != use_model]
            models_to_try += other_free

        last_error = None

        for current_model in models_to_try:
            payload = {
                "model":       current_model,
                "messages":    messages,
                "max_tokens":  max_tokens,
                "temperature": temperature,
                "stream":      False,
            }

            try:
                response = self._client.post(
                    "/chat/completions",
                    json    = payload,
                    timeout = timeout,
                )

                latency_ms = (time.perf_counter() - start_time) * 1000

                if response.status_code == 401:
                    raise ProviderAuthError(
                        "Invalid Together AI key. Check TOGETHER_API_KEY in .env"
                    )
                if response.status_code == 429:
                    raise RateLimitError("Together AI rate limit hit.")
                if response.status_code == 402:
                    logger.warning(f"Together: {current_model} requires payment. Trying free model...")
                    last_error = Exception(f"Payment required: {current_model}")
                    continue
                if response.status_code != 200:
                    try:
                        msg = response.json().get("error", {}).get("message", "")
                    except Exception:
                        msg = response.text[:200]
                    last_error = Exception(f"Together {response.status_code}: {msg}")
                    logger.warning(f"Together error ({current_model}): {msg}")
                    continue

                data    = response.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                usage  = data.get("usage", {})
                tokens = usage.get("total_tokens", 0)

                self._call_count  += 1
                self._token_count += tokens

                logger.debug(
                    f"Together OK: {current_model} | "
                    f"tokens={tokens} | latency={latency_ms:.0f}ms"
                )

                return {
                    "content":    content,
                    "model":      current_model,
                    "tokens":     tokens,
                    "latency_ms": latency_ms,
                }

            except (ProviderAuthError, RateLimitError):
                raise
            except httpx.TimeoutException:
                last_error = ProviderTimeoutError(f"Together timeout: {current_model}")
                logger.warning(f"Together timeout: {current_model}")
                continue
            except Exception as e:
                last_error = e
                self._error_count += 1
                logger.warning(f"Together error ({current_model}): {e}")
                continue

        raise last_error or Exception("Together AI: all models failed")

    def stream(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int   = 4096,
        temperature: float = 0.7,
        model:       Optional[str] = None,
    ) -> Generator[str, None, None]:
        use_model = model or self._model
        payload   = {
            "model":       use_model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "stream":      True,
        }

        try:
            with self._client.stream(
                "POST", "/chat/completions",
                json = payload, timeout = 120,
            ) as response:
                if response.status_code != 200:
                    yield f"[ERROR] Together HTTP {response.status_code}"
                    return

                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data  = json.loads(data_str)
                        delta = (
                            data.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if delta:
                            yield delta
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            yield f"\n[ERROR] Together stream: {str(e)[:100]}"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "provider":     "together",
            "model":        self._model,
            "total_calls":  self._call_count,
            "total_tokens": self._token_count,
        }

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass