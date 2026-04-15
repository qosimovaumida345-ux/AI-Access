# ============================================================
# SHADOWFORGE OS — ARENA.AI BROWSER SCRAPER
# Last resort fallback: uses Playwright to automate
# arena.ai in a headless browser and extract AI responses.
# No API key needed. Slower but always available.
# ============================================================

import time
import logging
import threading
from typing import Dict, List, Optional, Any, Generator
from pathlib import Path

from core.logger import get_logger

logger = get_logger("AI.ArenaScraper")

ARENA_URL = "https://arena.ai"

# Models available on Arena.ai (as of 2025)
ARENA_MODELS = [
    "claude-3.5-sonnet",
    "gpt-4o",
    "gemini-1.5-pro",
    "llama-3.1-405b",
    "mistral-large",
]


class ArenaScraper:
    """
    Browser automation fallback for Arena.ai.

    Uses Playwright to:
    1. Open arena.ai in headless browser
    2. Select the best available model
    3. Type the prompt
    4. Wait for and extract the response

    This is the LAST RESORT fallback — much slower than API calls.
    Only activates if all API providers fail.
    """

    def __init__(
        self,
        headless:     bool = True,
        timeout:      int  = 120,
        model:        str  = ARENA_MODELS[0],
    ):
        self._headless       = headless
        self._timeout        = timeout
        self._model          = model
        self._playwright     = None
        self._browser        = None
        self._page           = None
        self._initialized    = False
        self._lock           = threading.Lock()
        self._call_count     = 0
        self._init_error: Optional[str] = None

        logger.info("ArenaScraper initialized (lazy — browser starts on first call)")

    # ── LAZY INIT ─────────────────────────────────────────
    def _ensure_browser(self) -> bool:
        """Initialize Playwright browser if not already running."""
        if self._initialized:
            return True

        with self._lock:
            if self._initialized:
                return True

            try:
                from playwright.sync_api import sync_playwright
                self._pw_context = sync_playwright().__enter__()
                self._browser    = self._pw_context.chromium.launch(
                    headless = self._headless,
                    args     = [
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                self._page = self._browser.new_page(
                    user_agent = (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                self._initialized = True
                logger.info("Playwright browser started for Arena.ai scraping.")
                return True

            except ImportError:
                self._init_error = (
                    "Playwright not installed. "
                    "Run: pip install playwright && playwright install chromium"
                )
                logger.warning(self._init_error)
                return False

            except Exception as e:
                self._init_error = str(e)
                logger.error(f"Browser init failed: {e}")
                return False

    # ── NAVIGATE TO ARENA ─────────────────────────────────
    def _navigate_to_arena(self) -> bool:
        """Open Arena.ai and wait for chat interface."""
        try:
            self._page.goto(ARENA_URL, wait_until="networkidle", timeout=30000)
            time.sleep(2)

            # Wait for chat input
            chat_input = self._page.locator(
                "textarea, input[type='text'], [contenteditable='true']"
            ).first

            if chat_input:
                logger.debug("Arena.ai chat interface found.")
                return True

            logger.warning("Could not find Arena.ai chat input.")
            return False

        except Exception as e:
            logger.error(f"Arena navigation error: {e}")
            return False

    # ── TYPE AND GET RESPONSE ─────────────────────────────
    def _send_message(self, prompt: str) -> Optional[str]:
        """Type a message and wait for AI response."""
        try:
            page = self._page

            # Find and click input
            input_el = page.locator(
                "textarea[placeholder*='message' i], "
                "textarea[placeholder*='type' i], "
                "textarea[placeholder*='ask' i], "
                "div[contenteditable='true']"
            ).first

            if not input_el:
                logger.warning("No input field found on Arena.ai")
                return None

            input_el.click()
            input_el.fill("")

            # Type prompt (split for long prompts)
            chunk_size = 500
            for i in range(0, len(prompt), chunk_size):
                chunk = prompt[i:i+chunk_size]
                input_el.type(chunk, delay=20)

            # Submit
            page.keyboard.press("Enter")
            logger.debug("Prompt submitted to Arena.ai")

            # Wait for response
            start_wait = time.time()
            last_content = ""
            stable_count = 0

            while time.time() - start_wait < self._timeout:
                time.sleep(2)

                # Try to get response text
                response_el = page.locator(
                    "[data-message-author-role='assistant'], "
                    ".assistant-message, "
                    ".response-content, "
                    "[class*='assistant'] p"
                ).last

                if response_el:
                    try:
                        current = response_el.inner_text()
                        if current and current == last_content:
                            stable_count += 1
                            if stable_count >= 3:
                                # Response stable for 6 seconds = done
                                logger.debug(f"Arena response stable. Length: {len(current)}")
                                return current.strip()
                        else:
                            last_content  = current
                            stable_count  = 0
                    except Exception:
                        pass

            logger.warning("Arena.ai response timeout.")
            return last_content.strip() if last_content else None

        except Exception as e:
            logger.error(f"Arena send_message error: {e}")
            return None

    # ── COMPLETE ──────────────────────────────────────────
    def complete(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int   = 4096,
        temperature: float = 0.7,
        timeout:     int   = 120,
        model:       Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get AI response via Arena.ai browser automation.
        This is the last-resort fallback.
        """
        if not self._ensure_browser():
            raise Exception(
                f"Arena scraper unavailable: {self._init_error}"
            )

        # Build prompt from messages
        prompt_parts = []
        for msg in messages:
            role    = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        full_prompt = "\n\n".join(prompt_parts)
        if not full_prompt:
            raise Exception("Empty prompt")

        start_time = time.perf_counter()

        # Navigate if needed
        if not self._initialized or \
           ARENA_URL not in (self._page.url or ""):
            if not self._navigate_to_arena():
                raise Exception("Could not navigate to Arena.ai")

        # Send and get response
        response = self._send_message(full_prompt)

        if not response:
            raise Exception("Arena.ai returned empty response")

        latency_ms = (time.perf_counter() - start_time) * 1000
        self._call_count += 1

        logger.info(
            f"Arena.ai response received. "
            f"Length: {len(response)} | Latency: {latency_ms:.0f}ms"
        )

        return {
            "content":    response,
            "model":      f"arena/{model or self._model}",
            "tokens":     len(response.split()),
            "latency_ms": latency_ms,
        }

    def stream(
        self,
        messages:    List[Dict[str, str]],
        max_tokens:  int   = 4096,
        temperature: float = 0.7,
        model:       Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Arena doesn't support real streaming — complete and yield."""
        try:
            result = self.complete(messages, max_tokens, temperature, model=model)
            yield result.get("content", "")
        except Exception as e:
            yield f"[ERROR] Arena: {str(e)[:100]}"

    def take_screenshot(self, path: Path) -> bool:
        """Take a screenshot of current browser state (for debugging)."""
        if not self._page:
            return False
        try:
            self._page.screenshot(path=str(path))
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close the browser gracefully."""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
            self._initialized = False
            logger.info("Arena browser closed.")
        except Exception as e:
            logger.debug(f"Browser close error: {e}")

    def __del__(self):
        self.close()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "provider":     "arena",
            "model":        self._model,
            "total_calls":  self._call_count,
            "initialized":  self._initialized,
            "headless":     self._headless,
        }