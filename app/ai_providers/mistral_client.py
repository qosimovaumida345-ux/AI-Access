# ============================================================
# SHADOWFORGE OS — MISTRAL AI CLIENT
# Mistral AI: Strong coding models, free tier available.
# Mistral Small and open-mistral-nemo are free.
# API docs: https://docs.mistral.ai
# ============================================================

import time
import json
from typing import Dict, List, Optional, Any, Generator

import httpx

from core.logger import get_logger
from ai_providers.provider_manager import (
    RateLimitError, ProviderAuthError, ProviderTimeoutError
)

logger = get_logger("AI.Mistral")

MISTRAL_BASE_URL = "https://api.mistral.ai/v1"

MISTRAL_FREE_MODELS = [
    "open-mistral-nemo",       # 12B, free
    "open-mistral-7b",         # 7B, free
    "open-mixtral-8x7b",       # MoE, free
]

MISTRAL_PAID_MODELS = [
    "mistral-small-latest",    # Best quality/price
    "mistral-medium-latest",
    "mistral-large-latest",    # Most capable
    "codestral-latest",        # Code specialist
]


class MistralClient:
    """
    Mistral AI client.
    Excellent for code generation. Has free open models.
    """

    def __init__(
        self,
        api_key:     str,
        model:       Optional[str] = None,
        prefer_free: bool = True,
        timeout:     int  = 60,
    ):
        if not api_key or not api_key.strip():
            raise ProviderAuthError("Mistral API key is empty.")

        self._api_key    = api_key.strip()
        self._prefer_free= prefer_free
        self._timeout    = timeout
        self._call_count = 0
        self._token_count= 0
        self._error_count= 0

        self._model = model or (
            MISTRAL_FREE_MODELS[0] if prefer_free
            else MISTRAL_PAID_MODELS[0]
        )

        self._client = httpx.Client(
            base_url = MISTRAL_BASE_URL,
            headers  = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type":  "application/json",
                "Accept":        "application/json",
                "User-Agent":    "ShadowForge-OS/2.5",
            },
            timeout  = httpx.Timeout(connect=10.0, read=float(timeout), write=10.0, pool=5.0),
        )

        logger.info(f"MistralClient initialized. Model: {self._model}")

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

        models_to_try = [use_model]
        if self._prefer_free and use_model not in MISTRAL_FREE_MODELS:
            models_to_try += MISTRAL_FREE_MODELS
        elif use_model in MISTRAL_FREE_MODELS:
            others = [m for m in MISTRAL_FREE_MODELS if m != use_model]
            models_to_try += others

        last_error = None

        for current_model in models_to_try:
            payload = {
                "model":       current_model,
                "messages":    messages,
                "max_tokens":  max_tokens,
                "temperature": temperature,
                "stream":      False,
                "safe_prompt": False,
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
                        "Invalid Mistral key. Check MISTRAL_API_KEY in .env"
                    )
                if response.status_code == 429:
                    raise RateLimitError("Mistral rate limit hit.")
                if response.status_code == 422:
                    try:
                        detail = response.json().get("detail", "")
                    except Exception:
                        detail = response.text[:200]
                    last_error = Exception(f"Mistral validation error: {detail}")
                    continue
                if response.status_code != 200:
                    try:
                        msg = response.json().get("message", response.text[:200])
                    except Exception:
                        msg = response.text[:200]
                    last_error = Exception(f"Mistral {response.status_code}: {msg}")
                    logger.warning(f"Mistral error ({current_model}): {msg}")
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
                    f"Mistral OK: {current_model} | "
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
                last_error = ProviderTimeoutError(f"Mistral timeout: {current_model}")
                logger.warning(f"Mistral timeout: {current_model}")
                continue
            except Exception as e:
                last_error = e
                self._error_count += 1
                logger.warning(f"Mistral error ({current_model}): {e}")
                continue

        raise last_error or Exception("Mistral: all models failed")

    def stream(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int   = 4096,
        temperature: float = 0.7,
        model:       Optional[str] = None,
    ) -> Generator[str, None, None]:
        use_model = model or self._model

        payload = {
            "model":       use_model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "stream":      True,
            "safe_prompt": False,
        }

        try:
            with self._client.stream(
                "POST", "/chat/completions",
                json = payload, timeout = 120,
            ) as response:
                if response.status_code != 200:
                    yield f"[ERROR] Mistral HTTP {response.status_code}"
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
            yield f"\n[ERROR] Mistral stream: {str(e)[:100]}"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "provider":     "mistral",
            "model":        self._model,
            "total_calls":  self._call_count,
            "total_tokens": self._token_count,
        }

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass