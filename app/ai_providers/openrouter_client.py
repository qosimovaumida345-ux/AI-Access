# ============================================================
# SHADOWFORGE OS — OPENROUTER CLIENT
# OpenRouter aggregates 100+ AI models in one API.
# Many models are FREE. Best for model variety.
# API docs: https://openrouter.ai/docs
# ============================================================

import time
import json
import logging
from typing import Dict, List, Optional, Any, Generator

import httpx

from core.logger import get_logger
from core.constants import MODELS, PROVIDER_OPENROUTER
from ai_providers.provider_manager import (
    RateLimitError, ProviderAuthError, ProviderTimeoutError
)

logger = get_logger("AI.OpenRouter")

OPENROUTER_BASE_URL  = "https://openrouter.ai/api/v1"
OPENROUTER_SITE_URL  = "https://shadowforge.ai"
OPENROUTER_APP_NAME  = "ShadowForge OS"

# Free models on OpenRouter (no credit needed)
OPENROUTER_FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.1-70b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "google/gemma-2-9b-it:free",
    "openchat/openchat-7b:free",
    "huggingfaceh4/zephyr-7b-beta:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
]

# Paid models (require credits)
OPENROUTER_PAID_MODELS = [
    "anthropic/claude-3.5-sonnet",
    "openai/gpt-4o",
    "google/gemini-pro-1.5",
    "meta-llama/llama-3.1-405b-instruct",
]


class OpenRouterClient:
    """
    OpenRouter AI client.
    Supports all models via unified OpenAI-compatible API.
    Auto-falls back through free models if one fails.
    """

    def __init__(
        self,
        api_key:      str,
        model:        Optional[str] = None,
        prefer_free:  bool  = True,
        timeout:      int   = 90,
    ):
        if not api_key or not api_key.strip():
            raise ProviderAuthError("OpenRouter API key is empty.")

        self._api_key    = api_key.strip()
        self._prefer_free= prefer_free
        self._timeout    = timeout
        self._call_count = 0
        self._token_count= 0
        self._error_count= 0

        # Model selection
        if model:
            self._model = model
        elif prefer_free:
            self._model = OPENROUTER_FREE_MODELS[0]
        else:
            self._model = OPENROUTER_PAID_MODELS[0]

        self._client = httpx.Client(
            base_url = OPENROUTER_BASE_URL,
            headers  = {
                "Authorization":        f"Bearer {self._api_key}",
                "Content-Type":         "application/json",
                "HTTP-Referer":         OPENROUTER_SITE_URL,
                "X-Title":              OPENROUTER_APP_NAME,
                "User-Agent":           "ShadowForge-OS/2.5",
            },
            timeout = httpx.Timeout(
                connect = 10.0,
                read    = float(timeout),
                write   = 10.0,
                pool    = 5.0,
            ),
        )

        logger.info(
            f"OpenRouterClient initialized. "
            f"Model: {self._model} | Free: {prefer_free}"
        )

    # ── COMPLETE ──────────────────────────────────────────
    def complete(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int   = 4096,
        temperature: float = 0.7,
        timeout:     int   = 90,
        model:       Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Chat completion via OpenRouter.
        Auto-retries with next free model on failure.
        """
        models_to_try = []

        if model:
            models_to_try = [model]
        elif self._prefer_free:
            models_to_try = [self._model] + [
                m for m in OPENROUTER_FREE_MODELS
                if m != self._model
            ]
        else:
            models_to_try = [self._model]

        last_error = None

        for current_model in models_to_try:
            start_time = time.perf_counter()

            payload = {
                "model":       current_model,
                "messages":    messages,
                "max_tokens":  max_tokens,
                "temperature": temperature,
                "stream":      False,
                "transforms":  ["middle-out"],  # OpenRouter optimization
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
                        "Invalid OpenRouter API key. "
                        "Check OPENROUTER_API_KEY in .env"
                    )

                if response.status_code == 429:
                    raise RateLimitError("OpenRouter rate limit hit.")

                if response.status_code == 402:
                    # Payment required — try next free model
                    logger.warning(
                        f"OpenRouter: model {current_model} requires credits. "
                        f"Trying next free model..."
                    )
                    last_error = Exception(f"Credits required for {current_model}")
                    continue

                if response.status_code == 503:
                    logger.warning(f"OpenRouter: model {current_model} unavailable.")
                    last_error = ProviderTimeoutError(f"Model {current_model} unavailable")
                    continue

                if response.status_code != 200:
                    try:
                        err = response.json()
                        msg = err.get("error", {}).get("message", response.text[:200])
                    except Exception:
                        msg = response.text[:200]
                    last_error = Exception(f"OpenRouter {response.status_code}: {msg}")
                    logger.warning(f"OpenRouter error with {current_model}: {msg}")
                    continue

                # Parse
                data    = response.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                usage  = data.get("usage", {})
                tokens = usage.get("total_tokens", 0)
                model_returned = data.get("model", current_model)

                self._call_count  += 1
                self._token_count += tokens

                logger.debug(
                    f"OpenRouter OK: {model_returned} | "
                    f"tokens={tokens} | latency={latency_ms:.0f}ms"
                )

                return {
                    "content":    content,
                    "model":      model_returned,
                    "tokens":     tokens,
                    "latency_ms": latency_ms,
                }

            except (ProviderAuthError, RateLimitError):
                raise
            except httpx.TimeoutException:
                last_error = ProviderTimeoutError(
                    f"OpenRouter timeout with {current_model}"
                )
                logger.warning(f"OpenRouter timeout: {current_model}")
                continue
            except Exception as e:
                last_error = e
                self._error_count += 1
                logger.warning(f"OpenRouter error ({current_model}): {e}")
                continue

        raise last_error or Exception("OpenRouter: all models failed")

    # ── STREAMING ─────────────────────────────────────────
    def stream(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int   = 4096,
        temperature: float = 0.7,
        model:       Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Stream tokens from OpenRouter."""
        use_model = model or self._model

        payload = {
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
                    yield f"[ERROR] OpenRouter HTTP {response.status_code}"
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
            yield f"\n[ERROR] OpenRouter stream: {str(e)[:100]}"

    # ── FREE MODEL DISCOVERY ──────────────────────────────
    def get_free_models(self) -> List[Dict[str, Any]]:
        """
        Fetch current list of free models from OpenRouter API.
        """
        try:
            response = self._client.get("/models", timeout=15)
            if response.status_code != 200:
                return []

            all_models = response.json().get("data", [])
            free_models = []

            for model in all_models:
                pricing = model.get("pricing", {})
                prompt_price  = float(pricing.get("prompt", "1") or "1")
                completion_price = float(
                    pricing.get("completion", "1") or "1"
                )
                if prompt_price == 0 and completion_price == 0:
                    free_models.append({
                        "id":          model.get("id"),
                        "name":        model.get("name"),
                        "context":     model.get("context_length", 0),
                        "description": model.get("description", "")[:100],
                    })

            logger.info(f"OpenRouter free models found: {len(free_models)}")
            return free_models

        except Exception as e:
            logger.warning(f"Could not fetch OpenRouter models: {e}")
            return []

    def set_model(self, model: str) -> None:
        self._model = model

    def get_stats(self) -> Dict[str, Any]:
        return {
            "provider":     "openrouter",
            "model":        self._model,
            "total_calls":  self._call_count,
            "total_tokens": self._token_count,
            "error_count":  self._error_count,
        }

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass