# ============================================================
# SHADOWFORGE OS — GROQ AI CLIENT
# Groq is the FASTEST free AI provider (LLaMA 3.3 70B).
# Recommended as primary provider. 14,400 requests/day free.
# API docs: https://console.groq.com/docs
# ============================================================

import time
import json
import logging
from typing import Dict, List, Optional, Any, Generator

import httpx

from core.logger import get_logger
from core.constants import MODELS, PROVIDER_GROQ
from ai_providers.provider_manager import (
    RateLimitError, ProviderAuthError, ProviderTimeoutError
)

logger = get_logger("AI.Groq")

# Groq API endpoint
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Default models in priority order
GROQ_MODELS = [
    "llama-3.3-70b-versatile",   # Best for coding, 70B
    "llama-3.1-70b-versatile",   # Fallback 70B
    "mixtral-8x7b-32768",         # Long context
    "llama-3.1-8b-instant",       # Fast, lighter
    "gemma2-9b-it",               # Google's model via Groq
]


class GroqClient:
    """
    Groq AI API client.
    Uses OpenAI-compatible REST API.
    Supports: chat completion, streaming.
    Free tier: generous daily limits.
    """

    def __init__(
        self,
        api_key:     str,
        model:       Optional[str] = None,
        timeout:     int = 60,
        max_retries: int = 3,
    ):
        if not api_key or not api_key.strip():
            raise ProviderAuthError("Groq API key is empty.")

        self._api_key    = api_key.strip()
        self._model      = model or GROQ_MODELS[0]
        self._timeout    = timeout
        self._max_retries= max_retries
        self._base_url   = GROQ_BASE_URL

        # Stats
        self._call_count     = 0
        self._token_count    = 0
        self._error_count    = 0
        self._total_latency  = 0.0

        # HTTP client (persistent connection)
        self._client = httpx.Client(
            base_url = self._base_url,
            headers  = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type":  "application/json",
                "User-Agent":    "ShadowForge-OS/2.5",
            },
            timeout  = httpx.Timeout(
                connect = 10.0,
                read    = float(timeout),
                write   = 10.0,
                pool    = 5.0,
            ),
        )

        logger.info(f"GroqClient initialized. Model: {self._model}")

    # ── COMPLETE ──────────────────────────────────────────
    def complete(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int   = 4096,
        temperature: float = 0.7,
        timeout:     int   = 60,
        model:       Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to Groq.
        Returns normalized response dict.
        """
        use_model = model or self._model
        start_time = time.perf_counter()

        payload = {
            "model":       use_model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "stream":      False,
        }

        last_error = None

        for attempt in range(self._max_retries):
            try:
                response = self._client.post(
                    "/chat/completions",
                    json    = payload,
                    timeout = timeout,
                )

                latency_ms = (time.perf_counter() - start_time) * 1000

                # Handle HTTP errors
                if response.status_code == 401:
                    raise ProviderAuthError(
                        "Invalid Groq API key. "
                        "Check your GROQ_API_KEY in .env file."
                    )

                if response.status_code == 429:
                    retry_after = int(
                        response.headers.get("retry-after", "60")
                    )
                    raise RateLimitError(
                        f"Groq rate limit hit. Retry after {retry_after}s."
                    )

                if response.status_code == 503:
                    raise ProviderTimeoutError(
                        "Groq service unavailable (503)."
                    )

                if response.status_code != 200:
                    error_body = ""
                    try:
                        error_body = response.json().get("error", {}).get(
                            "message", response.text[:300]
                        )
                    except Exception:
                        error_body = response.text[:300]
                    raise Exception(
                        f"Groq HTTP {response.status_code}: {error_body}"
                    )

                # Parse response
                data = response.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )

                usage = data.get("usage", {})
                tokens_used = usage.get("total_tokens", 0)
                model_used  = data.get("model", use_model)

                # Update stats
                self._call_count    += 1
                self._token_count   += tokens_used
                self._total_latency += latency_ms

                logger.debug(
                    f"Groq OK: model={model_used} "
                    f"tokens={tokens_used} "
                    f"latency={latency_ms:.0f}ms"
                )

                return {
                    "content": content,
                    "model":   model_used,
                    "tokens":  tokens_used,
                    "latency_ms": latency_ms,
                }

            except (ProviderAuthError, RateLimitError):
                raise  # Don't retry these

            except httpx.TimeoutException:
                last_error = ProviderTimeoutError(
                    f"Groq timeout after {timeout}s"
                )
                logger.warning(
                    f"Groq timeout (attempt {attempt+1}/{self._max_retries})"
                )
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)

            except httpx.ConnectError as e:
                last_error = Exception(f"Groq connection error: {e}")
                logger.warning(f"Groq connect error: {e}")
                if attempt < self._max_retries - 1:
                    time.sleep(2)

            except Exception as e:
                last_error = e
                self._error_count += 1
                logger.warning(f"Groq error (attempt {attempt+1}): {e}")
                if attempt < self._max_retries - 1:
                    time.sleep(1)

        raise last_error or Exception("Groq: unknown error after retries")

    # ── STREAMING ─────────────────────────────────────────
    def stream(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int   = 4096,
        temperature: float = 0.7,
        model:       Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        Stream tokens from Groq using SSE.
        Yields individual text tokens as they arrive.
        """
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
                "POST",
                "/chat/completions",
                json    = payload,
                timeout = 120,
            ) as response:

                if response.status_code == 401:
                    yield "[ERROR] Invalid Groq API key."
                    return

                if response.status_code == 429:
                    yield "[ERROR] Groq rate limit exceeded."
                    return

                if response.status_code != 200:
                    yield f"[ERROR] Groq HTTP {response.status_code}"
                    return

                for line in response.iter_lines():
                    if not line:
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]

                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            delta = (
                                data.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                            )
                            if delta:
                                yield delta
                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException:
            yield "\n[ERROR] Groq stream timed out."
        except Exception as e:
            yield f"\n[ERROR] Groq stream error: {str(e)[:100]}"

    # ── MODEL SWITCHING ───────────────────────────────────
    def set_model(self, model: str) -> bool:
        """Switch to a different Groq model."""
        if model in GROQ_MODELS or model.startswith("llama") or \
           model.startswith("mixtral") or model.startswith("gemma"):
            self._model = model
            logger.info(f"Groq model switched to: {model}")
            return True
        logger.warning(f"Unknown Groq model: {model}")
        return False

    def list_models(self) -> List[str]:
        """Get list of available Groq models."""
        try:
            response = self._client.get("/models", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            logger.warning(f"Could not fetch Groq models: {e}")
        return GROQ_MODELS

    # ── STATS ─────────────────────────────────────────────
    def get_stats(self) -> Dict[str, Any]:
        avg_latency = (
            self._total_latency / self._call_count
            if self._call_count > 0 else 0
        )
        return {
            "provider":      "groq",
            "model":         self._model,
            "total_calls":   self._call_count,
            "total_tokens":  self._token_count,
            "error_count":   self._error_count,
            "avg_latency_ms": round(avg_latency, 1),
        }

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        return f"GroqClient(model={self._model}, calls={self._call_count})"