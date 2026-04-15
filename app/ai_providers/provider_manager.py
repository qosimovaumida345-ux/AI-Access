# ============================================================
# SHADOWFORGE OS — AI PROVIDER MANAGER
# Central hub for all AI provider integrations.
# Auto-selects best available provider, handles fallback chain,
# rate limiting, retry logic, and response normalization.
# ============================================================

import time
import json
import logging
import threading
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Generator, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from core.logger import get_logger, Timer
from core.constants import (
    PROVIDER_PRIORITY, ALL_PROVIDERS,
    PROVIDER_GROQ, PROVIDER_OPENROUTER,
    PROVIDER_TOGETHER, PROVIDER_MISTRAL,
    PROVIDER_GOOGLE, PROVIDER_COHERE,
    PROVIDER_HUGGINGFACE, PROVIDER_ARENA,
    AGENT_MAX_RETRIES, AGENT_RETRY_DELAY,
    MODELS,
)

logger = get_logger("AI.ProviderManager")


# ── PROVIDER STATUS ───────────────────────────────────────
class ProviderStatus(str, Enum):
    ONLINE      = "online"
    OFFLINE     = "offline"
    RATE_LIMITED= "rate_limited"
    NO_KEY      = "no_key"
    ERROR       = "error"
    UNTESTED    = "untested"


# ── PROVIDER STATS ────────────────────────────────────────
@dataclass
class ProviderStats:
    name:           str
    status:         ProviderStatus = ProviderStatus.UNTESTED
    total_calls:    int = 0
    success_calls:  int = 0
    failed_calls:   int = 0
    total_tokens:   int = 0
    avg_latency_ms: float = 0.0
    last_used:      Optional[str] = None
    last_error:     str = ""
    rate_limit_until: Optional[float] = None

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.success_calls / self.total_calls * 100

    @property
    def is_available(self) -> bool:
        if self.status == ProviderStatus.NO_KEY:
            return False
        if self.status == ProviderStatus.RATE_LIMITED:
            if self.rate_limit_until and time.time() < self.rate_limit_until:
                return False
            # Rate limit expired
            self.status = ProviderStatus.ONLINE
        return self.status != ProviderStatus.OFFLINE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":          self.name,
            "status":        self.status.value,
            "total_calls":   self.total_calls,
            "success_rate":  f"{self.success_rate:.1f}%",
            "avg_latency":   f"{self.avg_latency_ms:.0f}ms",
            "total_tokens":  self.total_tokens,
            "last_used":     self.last_used,
            "last_error":    self.last_error[:100] if self.last_error else "",
        }


# ── COMPLETION RESULT ─────────────────────────────────────
@dataclass
class CompletionResult:
    content:      str
    provider:     str
    model:        str
    tokens:       int = 0
    latency_ms:   float = 0.0
    cached:       bool = False
    error:        Optional[str] = None
    success:      bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content":    self.content,
            "provider":   self.provider,
            "model":      self.model,
            "tokens":     self.tokens,
            "latency_ms": self.latency_ms,
            "cached":     self.cached,
        }


# ── RESPONSE CACHE ────────────────────────────────────────
class ResponseCache:
    """Simple in-memory LRU cache for AI responses."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, messages: List[Dict], model: str) -> str:
        content = json.dumps(messages, sort_keys=True) + model
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, messages: List[Dict], model: str) -> Optional[str]:
        key = self._make_key(messages, model)
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    self._hits += 1
                    return value
                else:
                    del self._cache[key]
            self._misses += 1
            return None

    def set(self, messages: List[Dict], model: str, response: str) -> None:
        key = self._make_key(messages, model)
        with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self._max_size:
                oldest = min(self._cache, key=lambda k: self._cache[k][1])
                del self._cache[oldest]
            self._cache[key] = (response, time.time())

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "size":   len(self._cache),
            "hits":   self._hits,
            "misses": self._misses,
            "hit_rate": int(
                self._hits / max(1, self._hits + self._misses) * 100
            ),
        }


# ── MAIN PROVIDER MANAGER ─────────────────────────────────
class ProviderManager:
    """
    Central AI provider orchestrator.

    Features:
    - Auto-selects best available provider
    - Fallback chain on failure
    - Rate limit handling
    - Response caching (optional)
    - Per-provider stats tracking
    - Streaming support
    - Model selection per provider
    """

    def __init__(self, config, enable_cache: bool = True):
        self.config = config
        self._clients: Dict[str, Any] = {}
        self._stats:   Dict[str, ProviderStats] = {}
        self._lock     = threading.RLock()
        self._cache    = ResponseCache() if enable_cache else None
        self._priority = list(PROVIDER_PRIORITY)

        # Initialize stats for all providers
        for provider_name in ALL_PROVIDERS:
            self._stats[provider_name] = ProviderStats(name=provider_name)

        # Initialize available clients
        self._init_clients()

        logger.info(
            f"ProviderManager ready. "
            f"Available: {self._count_available()} providers."
        )

    # ── CLIENT INITIALIZATION ─────────────────────────────
    def _init_clients(self) -> None:
        """Initialize all provider clients that have API keys."""

        client_map = {
            PROVIDER_GROQ:        self._init_groq,
            PROVIDER_OPENROUTER:  self._init_openrouter,
            PROVIDER_TOGETHER:    self._init_together,
            PROVIDER_MISTRAL:     self._init_mistral,
            PROVIDER_GOOGLE:      self._init_google,
            PROVIDER_COHERE:      self._init_cohere,
            PROVIDER_HUGGINGFACE: self._init_huggingface,
            PROVIDER_ARENA:       self._init_arena,
        }

        for provider_name, init_fn in client_map.items():
            try:
                client = init_fn()
                if client is not None:
                    self._clients[provider_name] = client
                    self._stats[provider_name].status = ProviderStatus.ONLINE
                    logger.info(f"Provider ready: {provider_name}")
                else:
                    self._stats[provider_name].status = ProviderStatus.NO_KEY
                    logger.debug(f"Provider skipped (no key): {provider_name}")
            except Exception as e:
                self._stats[provider_name].status = ProviderStatus.ERROR
                self._stats[provider_name].last_error = str(e)
                logger.warning(f"Provider init failed: {provider_name} — {e}")

    def _init_groq(self, override_key: Optional[str] = None):
        key = override_key or self.config.get("GROQ_API_KEY")
        if not key:
            return None
        from ai_providers.groq_client import GroqClient
        return GroqClient(api_key=key)

    def _init_openrouter(self):
        key = self.config.get("OPENROUTER_API_KEY")
        if not key:
            return None
        from ai_providers.openrouter_client import OpenRouterClient
        return OpenRouterClient(api_key=key)

    def _init_together(self):
        key = self.config.get("TOGETHER_API_KEY")
        if not key:
            return None
        from ai_providers.together_client import TogetherClient
        return TogetherClient(api_key=key)

    def _init_mistral(self):
        key = self.config.get("MISTRAL_API_KEY")
        if not key:
            return None
        from ai_providers.mistral_client import MistralClient
        return MistralClient(api_key=key)

    def _init_google(self):
        key = self.config.get("GOOGLE_AI_API_KEY")
        if not key:
            return None
        from ai_providers.google_client import GoogleClient
        return GoogleClient(api_key=key)

    def _init_cohere(self):
        key = self.config.get("COHERE_API_KEY")
        if not key:
            return None
        from ai_providers.cohere_client import CohereClient
        return CohereClient(api_key=key)

    def _init_huggingface(self):
        key = self.config.get("HUGGINGFACE_API_KEY")
        if not key:
            return None
        from ai_providers.huggingface_client import HuggingFaceClient
        return HuggingFaceClient(api_key=key)

    def _init_arena(self):
        # Arena doesn't need an API key — uses browser automation
        try:
            from ai_providers.arena_scraper import ArenaScraper
            return ArenaScraper()
        except ImportError:
            return None

    # ── PROVIDER SELECTION ────────────────────────────────
    def _get_ordered_providers(self) -> List[str]:
        """Return providers in priority order, filtering unavailable ones."""
        available = []
        for provider_name in self._priority:
            if provider_name not in self._clients:
                continue
            stats = self._stats.get(provider_name)
            if stats and stats.is_available:
                available.append(provider_name)

        # Add any providers not in priority list
        for provider_name, client in self._clients.items():
            if provider_name not in available:
                stats = self._stats.get(provider_name)
                if stats and stats.is_available:
                    available.append(provider_name)

        return available

    def _count_available(self) -> int:
        return len(self._get_ordered_providers())

    # ── MAIN COMPLETE METHOD ──────────────────────────────
    def complete(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int   = 4096,
        temperature: float = 0.7,
        timeout:     int   = 60,
        prefer:      Optional[str] = None,
        use_cache:   bool  = True,
        api_keys:    Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Send messages to the best available provider.
        Returns normalized response dict.
        Automatically falls back through providers on failure.
        """
        # Check cache
        if use_cache and self._cache:
            cached = self._cache.get(messages, prefer or "auto")
            if cached:
                logger.debug("Cache hit — returning cached response.")
                return {
                    "content":  cached,
                    "provider": "cache",
                    "model":    "cached",
                    "tokens":   0,
                    "cached":   True,
                }

        # Get ordered provider list
        ordered = self._get_ordered_providers()

        if prefer and prefer in ordered:
            # Move preferred to front
            ordered.remove(prefer)
            ordered.insert(0, prefer)

        if not ordered:
            raise RuntimeError(
                "No AI providers available. "
                "Please add at least one API key to your .env file. "
                "Groq is free: https://console.groq.com/keys"
            )

        last_error = None

        # Try each provider in order
        for provider_name in ordered:
            client = self._clients.get(provider_name)
            if not client:
                continue

            logger.info(f"Trying provider: {provider_name}")
            stats = self._stats[provider_name]
            start_time = time.perf_counter()

            for attempt in range(AGENT_MAX_RETRIES):
                try:
                    # If dynamic keys are provided, we may need to create a temporary client
                    # or override the key. For simplicity, we'll check if the client supports key override.
                    current_api_key = api_keys.get(f"{provider_name.upper()}_API_KEY") if api_keys else None
                    
                    if current_api_key:
                        # Initialize a temporary client with the provided key
                        temp_client = self._get_temp_client(provider_name, current_api_key)
                        if temp_client:
                            result = temp_client.complete(
                                messages    = messages,
                                max_tokens  = max_tokens,
                                temperature = temperature,
                                timeout     = timeout,
                            )
                        else:
                            continue # Skip if couldn't create temp client
                    else:
                        # Use default client
                        result = client.complete(
                            messages    = messages,
                            max_tokens  = max_tokens,
                            temperature = temperature,
                            timeout     = timeout,
                        )

                    # Success handling
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    self._record_success(
                        provider_name, latency_ms,
                        result.get("tokens", 0)
                    )

                    response_content = result.get("content", "")

                    # Cache the response
                    if use_cache and self._cache and response_content:
                        self._cache.set(messages, provider_name, response_content)

                    logger.info(
                        f"Success: {provider_name} | "
                        f"model={result.get('model', 'unknown')} | "
                        f"tokens={result.get('tokens', 0)} | "
                        f"latency={latency_ms:.0f}ms"
                    )

                    return {
                        "content":    response_content,
                        "provider":   provider_name,
                        "model":      result.get("model", "unknown"),
                        "tokens":     result.get("tokens", 0),
                        "latency_ms": latency_ms,
                        "cached":     False,
                    }

                except RateLimitError as e:
                    logger.warning(f"{provider_name} rate limited: {e}")
                    stats.status = ProviderStatus.RATE_LIMITED
                    stats.rate_limit_until = time.time() + 60
                    last_error = e
                    break  # Don't retry rate limits, move to next provider

                except ProviderAuthError as e:
                    logger.error(f"{provider_name} auth failed: {e}")
                    stats.status = ProviderStatus.NO_KEY
                    self._record_failure(provider_name, str(e))
                    last_error = e
                    break  # Don't retry auth errors

                except ProviderTimeoutError as e:
                    logger.warning(
                        f"{provider_name} timeout (attempt {attempt+1}/{AGENT_MAX_RETRIES})"
                    )
                    last_error = e
                    if attempt < AGENT_MAX_RETRIES - 1:
                        time.sleep(AGENT_RETRY_DELAY * (attempt + 1))

                except Exception as e:
                    logger.warning(
                        f"{provider_name} error (attempt {attempt+1}): {e}"
                    )
                    last_error = e
                    self._record_failure(provider_name, str(e))
                    if attempt < AGENT_MAX_RETRIES - 1:
                        time.sleep(AGENT_RETRY_DELAY)

            logger.warning(f"Provider exhausted: {provider_name}. Trying next...")

        # All providers failed
        raise AllProvidersFailedError(
            f"All {len(ordered)} providers failed. Last error: {last_error}"
        )

    # ── STREAMING ─────────────────────────────────────────
    def stream(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int   = 4096,
        temperature: float = 0.7,
        prefer:      Optional[str] = None,
        api_keys:    Optional[Dict[str, str]] = None,
    ) -> Generator[str, None, None]:
        """
        Stream tokens from the best available provider.
        Falls back to non-streaming if provider doesn't support it.
        """
        ordered = self._get_ordered_providers()
        if prefer and prefer in ordered:
            ordered.remove(prefer)
            ordered.insert(0, prefer)

        if not ordered:
            yield "[ERROR] No providers available."
            return

        for provider_name in ordered:
            client = self._clients.get(provider_name)
            if not client:
                continue

            try:
                if hasattr(client, "stream"):
                    logger.info(f"Streaming from: {provider_name}")
                    yield from client.stream(
                        messages    = messages,
                        max_tokens  = max_tokens,
                        temperature = temperature,
                    )
                    self._record_success(provider_name, 0, 0)
                    return
                else:
                    # Fallback: complete and yield all at once
                    result = client.complete(
                        messages    = messages,
                        max_tokens  = max_tokens,
                        temperature = temperature,
                    )
                    yield result.get("content", "")
                    return

            except RateLimitError:
                self._stats[provider_name].status = ProviderStatus.RATE_LIMITED
                continue
            except Exception as e:
                logger.warning(f"Stream failed for {provider_name}: {e}")
                continue

        yield "[ERROR] All providers failed during streaming."

    # ── STATS RECORDING ───────────────────────────────────
    def _record_success(
        self,
        provider_name: str,
        latency_ms:    float,
        tokens:        int,
    ) -> None:
        with self._lock:
            stats = self._stats.get(provider_name)
            if not stats:
                return
            stats.total_calls   += 1
            stats.success_calls += 1
            stats.total_tokens  += tokens
            stats.last_used      = datetime.now().isoformat()
            stats.status         = ProviderStatus.ONLINE

            # Running average latency
            if stats.avg_latency_ms == 0:
                stats.avg_latency_ms = latency_ms
            else:
                stats.avg_latency_ms = (
                    stats.avg_latency_ms * 0.8 + latency_ms * 0.2
                )

    def _record_failure(self, provider_name: str, error: str) -> None:
        with self._lock:
            stats = self._stats.get(provider_name)
            if not stats:
                return
            stats.total_calls  += 1
            stats.failed_calls += 1
            stats.last_error    = error[:200]
            if stats.failed_calls >= 3:
                stats.status = ProviderStatus.ERROR

    # ── PUBLIC METHODS ────────────────────────────────────
    def get_best_provider(self) -> Optional[str]:
        """Get the name of the currently best available provider."""
        ordered = self._get_ordered_providers()
        return ordered[0] if ordered else None

    def get_all_stats(self) -> List[Dict[str, Any]]:
        """Get stats for all providers."""
        return [s.to_dict() for s in self._stats.values()]

    def get_available_providers(self) -> List[str]:
        return self._get_ordered_providers()

    def set_priority(self, priority: List[str]) -> None:
        """Override the provider priority order."""
        self._priority = priority
        logger.info(f"Provider priority updated: {priority}")

    def mark_provider_offline(self, provider_name: str) -> None:
        """Manually mark a provider as offline."""
        if provider_name in self._stats:
            self._stats[provider_name].status = ProviderStatus.OFFLINE
            logger.warning(f"Provider manually marked offline: {provider_name}")

    def health_check(self) -> Dict[str, bool]:
        """Quick health check on all providers."""
        results = {}
        test_messages = [
            {"role": "user", "content": "Reply with: OK"}
        ]
        for provider_name, client in self._clients.items():
            try:
                result = client.complete(
                    messages   = test_messages,
                    max_tokens = 10,
                    temperature= 0,
                    timeout    = 10,
                )
                results[provider_name] = bool(result.get("content"))
                self._stats[provider_name].status = ProviderStatus.ONLINE
            except Exception as e:
                results[provider_name] = False
                self._stats[provider_name].status = ProviderStatus.ERROR
                self._stats[provider_name].last_error = str(e)
        return results

    def get_cache_stats(self) -> Dict[str, int]:
        if self._cache:
            return self._cache.stats
        return {}

    def clear_cache(self) -> None:
        if self._cache:
            self._cache.clear()

    def _get_temp_client(self, provider_name: str, api_key: str) -> Any:
        """Create a temporary client for a specific request with a given key."""
        init_map = {
            PROVIDER_GROQ:        lambda k: self._init_groq(k),
            PROVIDER_OPENROUTER:  lambda k: self._init_openrouter_all(k),
            PROVIDER_TOGETHER:    lambda k: self._init_together_all(k),
            # Add others as needed
        }
        fn = init_map.get(provider_name)
        return fn(api_key) if fn else None

    def _init_openrouter_all(self, key: str):
        from ai_providers.openrouter_client import OpenRouterClient
        return OpenRouterClient(api_key=key)

    def _init_together_all(self, key: str):
        from ai_providers.together_client import TogetherClient
        return TogetherClient(api_key=key)

    def __repr__(self) -> str:
        return (
            f"ProviderManager("
            f"available={self._count_available()}, "
            f"clients={list(self._clients.keys())})"
        )


# ── CUSTOM EXCEPTIONS ─────────────────────────────────────
class ProviderError(Exception):
    """Base provider error."""
    pass

class RateLimitError(ProviderError):
    """Provider rate limit hit."""
    pass

class ProviderAuthError(ProviderError):
    """Authentication/API key error."""
    pass

class ProviderTimeoutError(ProviderError):
    """Provider request timed out."""
    pass

class AllProvidersFailedError(ProviderError):
    """All providers in the chain failed."""
    pass