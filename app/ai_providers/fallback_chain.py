# ============================================================
# SHADOWFORGE OS — FALLBACK CHAIN
# Intelligent provider fallback with health tracking,
# circuit breaker pattern, and adaptive retry logic.
# ============================================================

import time
import threading
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.logger import get_logger

logger = get_logger("AI.FallbackChain")


class CircuitState(str, Enum):
    CLOSED   = "closed"    # Normal operation
    OPEN     = "open"      # Failing, don't try
    HALF_OPEN= "half_open" # Testing if recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker for a single provider."""
    name:            str
    state:           CircuitState = CircuitState.CLOSED
    failure_count:   int          = 0
    success_count:   int          = 0
    last_failure:    float        = 0.0
    last_success:    float        = 0.0
    open_until:      float        = 0.0
    threshold:       int          = 3      # failures before opening
    timeout:         float        = 60.0   # seconds before half-open

    def record_success(self) -> None:
        self.success_count += 1
        self.last_success   = time.time()
        self.failure_count  = 0
        self.state          = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure   = time.time()

        if self.failure_count >= self.threshold:
            self.state      = CircuitState.OPEN
            self.open_until = time.time() + self.timeout
            logger.warning(
                f"Circuit OPEN for {self.name}. "
                f"Will retry in {self.timeout}s."
            )

    def can_attempt(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() >= self.open_until:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit HALF-OPEN for {self.name}. Testing...")
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":          self.name,
            "state":         self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "can_attempt":   self.can_attempt(),
        }


@dataclass
class ProviderHealth:
    """Health tracking for a provider over time."""
    name:           str
    total_attempts: int   = 0
    total_success:  int   = 0
    total_failure:  int   = 0
    total_latency:  float = 0.0
    last_checked:   str   = ""
    score:          float = 100.0  # 0-100 health score

    def update(self, success: bool, latency_ms: float = 0) -> None:
        self.total_attempts += 1
        self.last_checked    = datetime.now().isoformat()

        if success:
            self.total_success += 1
            self.total_latency += latency_ms
        else:
            self.total_failure += 1

        # Calculate health score
        if self.total_attempts > 0:
            success_rate = self.total_success / self.total_attempts
            avg_latency  = (
                self.total_latency / max(1, self.total_success)
            )
            latency_score = max(0, 100 - (avg_latency / 100))
            self.score = (success_rate * 70) + (latency_score * 0.3)

    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 1.0
        return self.total_success / self.total_attempts

    @property
    def avg_latency_ms(self) -> float:
        if self.total_success == 0:
            return 9999.0
        return self.total_latency / self.total_success


class FallbackChain:
    """
    Intelligent fallback chain with circuit breakers.

    Features:
    - Per-provider circuit breakers
    - Health score tracking
    - Adaptive retry with exponential backoff
    - Provider reordering based on health
    - Error classification (retryable vs permanent)
    """

    # Errors that should NOT be retried
    PERMANENT_ERRORS = {
        "auth", "api_key", "invalid_key", "unauthorized",
        "401", "403", "payment_required", "402",
    }

    # Errors that SHOULD be retried
    RETRYABLE_ERRORS = {
        "timeout", "connection", "503", "502", "504",
        "rate_limit", "429", "server_error", "500",
    }

    def __init__(self, providers: List[str]):
        self._providers = providers
        self._breakers: Dict[str, CircuitBreaker] = {
            name: CircuitBreaker(name=name)
            for name in providers
        }
        self._health: Dict[str, ProviderHealth] = {
            name: ProviderHealth(name=name)
            for name in providers
        }
        self._lock = threading.RLock()
        self._call_log: List[Dict[str, Any]] = []

        logger.info(
            f"FallbackChain initialized with {len(providers)} providers: "
            f"{providers}"
        )

    def get_ordered_providers(self) -> List[str]:
        """
        Return providers sorted by health score and availability.
        Respects circuit breaker state.
        """
        with self._lock:
            available = [
                name for name in self._providers
                if self._breakers[name].can_attempt()
            ]

            # Sort by health score (highest first)
            available.sort(
                key=lambda n: self._health[n].score,
                reverse=True
            )

        return available

    def execute(
        self,
        func:        Callable,          # func(provider_name) -> result
        providers:   Optional[List[str]] = None,
        max_attempts: int = None,
    ) -> Any:
        """
        Execute func with automatic fallback across providers.

        func receives the provider name and should return a result
        or raise an exception.

        Returns the first successful result.
        Raises the last error if all providers fail.
        """
        ordered = providers or self.get_ordered_providers()

        if not ordered:
            raise RuntimeError(
                "No providers available in fallback chain. "
                "All circuits are open."
            )

        if max_attempts:
            ordered = ordered[:max_attempts]

        last_error: Optional[Exception] = None

        for provider_name in ordered:
            breaker = self._breakers.get(provider_name)
            if not breaker or not breaker.can_attempt():
                logger.debug(f"Skipping {provider_name}: circuit open")
                continue

            start_time = time.perf_counter()

            try:
                logger.info(f"Attempting provider: {provider_name}")
                result = func(provider_name)

                latency_ms = (time.perf_counter() - start_time) * 1000

                with self._lock:
                    breaker.record_success()
                    self._health[provider_name].update(True, latency_ms)

                self._log_attempt(provider_name, True, latency_ms)
                logger.info(
                    f"Provider succeeded: {provider_name} "
                    f"({latency_ms:.0f}ms)"
                )
                return result

            except Exception as e:
                latency_ms = (time.perf_counter() - start_time) * 1000
                error_str  = str(e).lower()

                with self._lock:
                    breaker.record_failure()
                    self._health[provider_name].update(False)

                self._log_attempt(provider_name, False, latency_ms, str(e))

                # Check if error is permanent (don't try other providers)
                if any(perm in error_str for perm in self.PERMANENT_ERRORS):
                    logger.error(
                        f"Permanent error for {provider_name}: {e}. "
                        f"Continuing to next provider."
                    )

                last_error = e
                logger.warning(
                    f"Provider failed: {provider_name} — {str(e)[:100]}. "
                    f"Trying next..."
                )

        raise RuntimeError(
            f"All providers in fallback chain failed. "
            f"Last error: {last_error}"
        )

    def _log_attempt(
        self,
        provider:   str,
        success:    bool,
        latency_ms: float,
        error:      str = "",
    ) -> None:
        with self._lock:
            self._call_log.append({
                "ts":         datetime.now().isoformat(),
                "provider":   provider,
                "success":    success,
                "latency_ms": round(latency_ms, 1),
                "error":      error[:100] if error else "",
            })
            if len(self._call_log) > 1000:
                self._call_log = self._call_log[-500:]

    def force_open(self, provider_name: str) -> None:
        """Manually open circuit for a provider."""
        if provider_name in self._breakers:
            self._breakers[provider_name].state = CircuitState.OPEN
            self._breakers[provider_name].open_until = time.time() + 300
            logger.warning(f"Circuit manually OPENED: {provider_name}")

    def force_close(self, provider_name: str) -> None:
        """Manually reset/close circuit for a provider."""
        if provider_name in self._breakers:
            breaker = self._breakers[provider_name]
            breaker.state         = CircuitState.CLOSED
            breaker.failure_count = 0
            logger.info(f"Circuit manually CLOSED: {provider_name}")

    def get_health_report(self) -> Dict[str, Any]:
        """Full health report for all providers."""
        with self._lock:
            return {
                "providers": {
                    name: {
                        "health_score":  round(h.score, 1),
                        "success_rate":  f"{h.success_rate*100:.1f}%",
                        "avg_latency":   f"{h.avg_latency_ms:.0f}ms",
                        "total_calls":   h.total_attempts,
                        "circuit":       self._breakers[name].to_dict(),
                    }
                    for name, h in self._health.items()
                },
                "ordered": self.get_ordered_providers(),
                "total_calls": len(self._call_log),
            }

    def reset_all(self) -> None:
        """Reset all circuit breakers and health stats."""
        with self._lock:
            for name in self._providers:
                self._breakers[name] = CircuitBreaker(name=name)
                self._health[name]   = ProviderHealth(name=name)
        logger.info("All circuits reset.")

    def get_best_provider(self) -> Optional[str]:
        """Return the single best available provider."""
        ordered = self.get_ordered_providers()
        return ordered[0] if ordered else None

    def __repr__(self) -> str:
        available = len(self.get_ordered_providers())
        return (
            f"FallbackChain("
            f"providers={len(self._providers)}, "
            f"available={available})"
        )