# ============================================================
# SHADOWFORGE OS — GOOGLE AI STUDIO CLIENT
# Google Gemini Flash: COMPLETELY FREE, fast, capable.
# 1 million tokens/day free on Gemini 1.5 Flash.
# API docs: https://ai.google.dev/docs
# ============================================================

import time
import json
from typing import Dict, List, Optional, Any, Generator

import httpx

from core.logger import get_logger
from ai_providers.provider_manager import (
    RateLimitError, ProviderAuthError, ProviderTimeoutError
)

logger = get_logger("AI.Google")

GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

GOOGLE_FREE_MODELS = [
    "gemini-1.5-flash",          # Fast, free, 1M tokens/day
    "gemini-1.5-flash-8b",       # Even faster, free
    "gemini-1.5-pro",            # Limited free tier
    "gemini-1.0-pro",            # Legacy, free
]


class GoogleClient:
    """
    Google AI Studio (Gemini) client.
    Uses REST API directly (no SDK dependency).
    Gemini 1.5 Flash is completely free with high limits.
    """

    def __init__(
        self,
        api_key: str,
        model:   Optional[str] = None,
        timeout: int = 60,
    ):
        if not api_key or not api_key.strip():
            raise ProviderAuthError("Google AI API key is empty.")

        self._api_key    = api_key.strip()
        self._model      = model or GOOGLE_FREE_MODELS[0]
        self._timeout    = timeout
        self._call_count = 0
        self._token_count= 0
        self._error_count= 0

        self._client = httpx.Client(
            base_url = GOOGLE_BASE_URL,
            timeout  = httpx.Timeout(connect=10.0, read=float(timeout), write=10.0, pool=5.0),
            headers  = {"User-Agent": "ShadowForge-OS/2.5"},
        )

        logger.info(f"GoogleClient initialized. Model: {self._model}")

    def _convert_messages(
        self, messages: List[Dict[str, str]]
    ) -> tuple[str, List[Dict]]:
        """
        Convert OpenAI-format messages to Google format.
        Returns (system_instruction, contents).
        """
        system_instruction = ""
        contents = []

        for msg in messages:
            role    = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_instruction = content
            elif role == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": content}],
                })
            elif role == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}],
                })

        # Ensure first message is from user
        if contents and contents[0]["role"] == "model":
            contents.insert(0, {
                "role": "user",
                "parts": [{"text": "Hello"}],
            })

        return system_instruction, contents

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

        system_instr, contents = self._convert_messages(messages)

        if not contents:
            contents = [{"role": "user", "parts": [{"text": "Hello"}]}]

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature":     temperature,
                "topP":            0.95,
                "topK":            40,
            },
            "safetySettings": [
                {
                    "category":  "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category":  "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category":  "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category":  "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE",
                },
            ],
        }

        if system_instr:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instr}]
            }

        # Try models in order
        models_to_try = [use_model] + [
            m for m in GOOGLE_FREE_MODELS if m != use_model
        ]

        last_error = None

        for current_model in models_to_try:
            url = (
                f"/models/{current_model}:generateContent"
                f"?key={self._api_key}"
            )

            try:
                response = self._client.post(
                    url,
                    json    = payload,
                    timeout = timeout,
                )

                latency_ms = (time.perf_counter() - start_time) * 1000

                if response.status_code == 400:
                    try:
                        err = response.json()
                        msg = err.get("error", {}).get("message", "")
                        if "API_KEY_INVALID" in msg or "invalid" in msg.lower():
                            raise ProviderAuthError(
                                "Invalid Google AI API key. "
                                "Check GOOGLE_AI_API_KEY in .env. "
                                "Get free key: aistudio.google.com/app/apikey"
                            )
                    except ProviderAuthError:
                        raise
                    except Exception:
                        pass
                    last_error = Exception(f"Google 400: {response.text[:200]}")
                    continue

                if response.status_code == 429:
                    raise RateLimitError("Google AI rate limit hit.")

                if response.status_code == 503:
                    last_error = ProviderTimeoutError(
                        f"Google model {current_model} unavailable"
                    )
                    continue

                if response.status_code != 200:
                    last_error = Exception(
                        f"Google {response.status_code}: {response.text[:200]}"
                    )
                    continue

                data = response.json()

                # Check for content filtering
                candidates = data.get("candidates", [])
                if not candidates:
                    finish_reason = data.get("promptFeedback", {}).get(
                        "blockReason", "UNKNOWN"
                    )
                    last_error = Exception(
                        f"Google blocked response: {finish_reason}"
                    )
                    logger.warning(f"Google blocked: {finish_reason}")
                    continue

                content = ""
                for part in candidates[0].get("content", {}).get("parts", []):
                    content += part.get("text", "")

                usage  = data.get("usageMetadata", {})
                tokens = usage.get("totalTokenCount", 0)

                self._call_count  += 1
                self._token_count += tokens

                logger.debug(
                    f"Google OK: {current_model} | "
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
                last_error = ProviderTimeoutError(f"Google timeout: {current_model}")
                logger.warning(f"Google timeout: {current_model}")
                continue
            except Exception as e:
                last_error = e
                self._error_count += 1
                logger.warning(f"Google error ({current_model}): {e}")
                continue

        raise last_error or Exception("Google AI: all models failed")

    def stream(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int   = 4096,
        temperature: float = 0.7,
        model:       Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Stream tokens from Google Gemini."""
        use_model = model or self._model
        system_instr, contents = self._convert_messages(messages)

        if not contents:
            contents = [{"role": "user", "parts": [{"text": "Hello"}]}]

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature":     temperature,
            },
        }
        if system_instr:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instr}]
            }

        url = (
            f"/models/{use_model}:streamGenerateContent"
            f"?alt=sse&key={self._api_key}"
        )

        try:
            with self._client.stream(
                "POST", url,
                json = payload, timeout = 120,
            ) as response:
                if response.status_code != 200:
                    yield f"[ERROR] Google HTTP {response.status_code}"
                    return

                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                text = part.get("text", "")
                                if text:
                                    yield text
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            yield f"\n[ERROR] Google stream: {str(e)[:100]}"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "provider":     "google",
            "model":        self._model,
            "total_calls":  self._call_count,
            "total_tokens": self._token_count,
        }

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass