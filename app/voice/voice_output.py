# ============================================================
# SHADOWFORGE OS — VOICE OUTPUT / TTS SYSTEM
# Text-to-speech with multiple engine support.
# Supports: pyttsx3 (offline), gTTS (online), ElevenLabs API.
# Dark, dramatic voice persona for ShadowForge.
# ============================================================

import io
import os
import time
import queue
import logging
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from core.logger import get_logger

logger = get_logger("Voice.Output")


class TTSEngine(str, Enum):
    PYTTSX3    = "pyttsx3"    # Offline, fast, built-in voices
    GTTS       = "gtts"       # Google TTS (online, good quality)
    ELEVENLABS = "elevenlabs" # ElevenLabs API (best quality, paid)
    SYSTEM     = "system"     # OS-native TTS (say on macOS, etc.)


@dataclass
class SpeakRequest:
    text:     str
    priority: int   = 0    # Higher = speaks first
    speed:    float = 1.0
    volume:   float = 1.0
    blocking: bool  = False


class VoiceOutput:
    """
    Handles text-to-speech output for ShadowForge OS.

    Features:
    - Multiple TTS engine support
    - Non-blocking async speech queue
    - Priority queue for urgent messages
    - Speech rate and volume control
    - Dark persona voice customization
    - Interrupt capability
    """

    # ShadowForge voice persona settings
    PERSONA_SETTINGS = {
        "pyttsx3": {
            "rate":   160,    # Words per minute (slower = more dramatic)
            "volume": 0.95,
            "voice_preference": ["david", "daniel", "alex"],  # Male voices
        }
    }

    # Phrases the AI speaks dramatically
    DRAMATIC_PREFIXES = [
        "◈ ", "» ", "⚡ ",
    ]

    def __init__(
        self,
        engine:           TTSEngine = TTSEngine.PYTTSX3,
        on_speak_start:   Optional[Callable] = None,
        on_speak_end:     Optional[Callable] = None,
        auto_start_queue: bool = True,
    ):
        self.engine         = engine
        self.on_speak_start = on_speak_start
        self.on_speak_end   = on_speak_end

        self._tts_engine     = None
        self._is_available   = False
        self._is_speaking    = False
        self._should_stop    = False
        self._lock           = threading.Lock()

        # Priority queue: (-priority, sequence, request)
        self._queue:    queue.PriorityQueue = queue.PriorityQueue()
        self._sequence: int = 0
        self._worker:   Optional[threading.Thread] = None

        self._total_spoken = 0
        self._total_chars  = 0

        self._initialize()

        if auto_start_queue and self._is_available:
            self._start_worker()

    # ── INITIALIZATION ────────────────────────────────────
    def _initialize(self) -> None:
        """Initialize TTS engine."""
        try:
            if self.engine == TTSEngine.PYTTSX3:
                self._init_pyttsx3()
            elif self.engine == TTSEngine.GTTS:
                self._init_gtts()
            elif self.engine == TTSEngine.SYSTEM:
                self._init_system()
            else:
                self._init_pyttsx3()  # Default fallback
        except Exception as e:
            logger.warning(f"TTS initialization failed: {e}")
            self._is_available = False

    def _init_pyttsx3(self) -> None:
        """Initialize pyttsx3 offline TTS."""
        import pyttsx3
        engine = pyttsx3.init()

        # Apply persona settings
        settings = self.PERSONA_SETTINGS.get("pyttsx3", {})
        engine.setProperty("rate",   settings.get("rate",   160))
        engine.setProperty("volume", settings.get("volume", 0.95))

        # Try to set preferred voice (male, deep)
        voices = engine.getProperty("voices")
        preferred = settings.get("voice_preference", [])

        for pref in preferred:
            for voice in voices:
                if pref.lower() in voice.name.lower():
                    engine.setProperty("voice", voice.id)
                    logger.debug(f"Voice selected: {voice.name}")
                    break

        self._tts_engine  = engine
        self._is_available = True
        logger.info("pyttsx3 TTS initialized.")

    def _init_gtts(self) -> None:
        """Initialize Google TTS (online)."""
        import gtts
        self._gtts         = gtts
        self._is_available = True
        logger.info("gTTS initialized (online mode).")

    def _init_system(self) -> None:
        """Initialize system TTS."""
        import subprocess
        import sys

        if sys.platform == "darwin":
            self._system_cmd    = "say"
            self._is_available  = True
        elif sys.platform.startswith("linux"):
            # Try espeak
            result = subprocess.run(
                ["which", "espeak"], capture_output=True
            )
            if result.returncode == 0:
                self._system_cmd   = "espeak"
                self._is_available = True
            else:
                self._is_available = False
        elif sys.platform == "win32":
            self._system_cmd   = "powershell"
            self._is_available = True
        else:
            self._is_available = False

        if self._is_available:
            logger.info(f"System TTS initialized: {self._system_cmd}")

    # ── WORKER THREAD ─────────────────────────────────────
    def _start_worker(self) -> None:
        """Start the background speech worker thread."""
        self._worker = threading.Thread(
            target  = self._speech_worker,
            name    = "ShadowVoiceOutput",
            daemon  = True,
        )
        self._worker.start()
        logger.debug("TTS worker started.")

    def _speech_worker(self) -> None:
        """Background worker that processes the speech queue."""
        while not self._should_stop:
            try:
                # Get next request (timeout to allow checking _should_stop)
                priority, seq, request = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if self._should_stop:
                break

            self._speak_now(request)
            self._queue.task_done()

    # ── SPEAK METHOD ──────────────────────────────────────
    def speak(
        self,
        text:     str,
        priority: int   = 0,
        blocking: bool  = False,
        clean:    bool  = True,
    ) -> None:
        """
        Speak text asynchronously (queued) or synchronously.

        priority: higher values speak before lower values.
        blocking: if True, waits for speech to complete.
        clean: if True, removes markdown/special chars.
        """
        if not self._is_available or not text.strip():
            return

        if clean:
            text = self._clean_text(text)

        if not text.strip():
            return

        request = SpeakRequest(
            text     = text,
            priority = priority,
            blocking = blocking,
        )

        if blocking:
            self._speak_now(request)
        else:
            # Add to priority queue
            with self._lock:
                seq = self._sequence
                self._sequence += 1
            self._queue.put((-priority, seq, request))

    def speak_urgent(self, text: str) -> None:
        """Speak with highest priority — interrupts lower priority items."""
        self.speak(text, priority=100)

    def _speak_now(self, request: SpeakRequest) -> None:
        """Actually speak — called by worker or directly if blocking."""
        with self._lock:
            self._is_speaking = True

        if self.on_speak_start:
            try:
                self.on_speak_start(request.text)
            except Exception:
                pass

        start = time.perf_counter()

        try:
            if self.engine == TTSEngine.PYTTSX3:
                self._speak_pyttsx3(request)
            elif self.engine == TTSEngine.GTTS:
                self._speak_gtts(request)
            elif self.engine == TTSEngine.SYSTEM:
                self._speak_system(request)

            self._total_spoken += 1
            self._total_chars  += len(request.text)

        except Exception as e:
            logger.warning(f"TTS speak error: {e}")
        finally:
            with self._lock:
                self._is_speaking = False

            duration = time.perf_counter() - start
            if self.on_speak_end:
                try:
                    self.on_speak_end(request.text, duration)
                except Exception:
                    pass

    def _speak_pyttsx3(self, request: SpeakRequest) -> None:
        """Speak using pyttsx3."""
        if self._tts_engine is None:
            return

        # Apply request-specific settings
        if request.speed != 1.0:
            current_rate = self._tts_engine.getProperty("rate")
            self._tts_engine.setProperty("rate", int(current_rate * request.speed))

        if request.volume != 1.0:
            self._tts_engine.setProperty("volume", request.volume)

        self._tts_engine.say(request.text)
        self._tts_engine.runAndWait()

        # Restore defaults
        settings = self.PERSONA_SETTINGS.get("pyttsx3", {})
        if request.speed != 1.0:
            self._tts_engine.setProperty("rate", settings.get("rate", 160))
        if request.volume != 1.0:
            self._tts_engine.setProperty("volume", settings.get("volume", 0.95))

    def _speak_gtts(self, request: SpeakRequest) -> None:
        """Speak using Google TTS (requires pygame or playsound)."""
        try:
            from gtts import gTTS
            import tempfile

            tts = gTTS(text=request.text, lang="en", slow=False)

            # Save to temp file and play
            with tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False
            ) as tmp:
                tts.save(tmp.name)
                tmp_path = tmp.name

            self._play_audio_file(tmp_path)

            # Cleanup
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"gTTS error: {e}")
            # Fallback to pyttsx3
            if self._tts_engine:
                self._tts_engine.say(request.text)
                self._tts_engine.runAndWait()

    def _speak_system(self, request: SpeakRequest) -> None:
        """Speak using system TTS."""
        import subprocess
        import sys

        try:
            if sys.platform == "darwin":
                subprocess.run(
                    ["say", "-r", "160", request.text],
                    check=True, timeout=30,
                )
            elif sys.platform.startswith("linux"):
                subprocess.run(
                    ["espeak", "-s", "160", request.text],
                    check=True, timeout=30,
                )
            elif sys.platform == "win32":
                script = (
                    f'Add-Type -AssemblyName System.Speech; '
                    f'$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
                    f'$s.Rate = 2; '
                    f'$s.Speak("{request.text.replace(chr(34), "")}");'
                )
                subprocess.run(
                    ["powershell", "-Command", script],
                    check=True, timeout=30,
                )
        except subprocess.TimeoutExpired:
            logger.warning("System TTS timed out.")
        except Exception as e:
            logger.warning(f"System TTS error: {e}")

    def _play_audio_file(self, path: str) -> None:
        """Play an audio file using available library."""
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except ImportError:
            try:
                import playsound
                playsound.playsound(path)
            except ImportError:
                logger.warning("No audio player available (pygame/playsound)")

    # ── TEXT CLEANING ─────────────────────────────────────
    def _clean_text(self, text: str) -> str:
        """Clean text for natural TTS output."""
        import re
        # Remove markdown
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.+?)\*',     r'\1', text)  # Italic
        text = re.sub(r'`(.+?)`',       r'\1', text)  # Code
        text = re.sub(r'#{1,6}\s',       '',   text)  # Headers
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # Links

        # Remove special chars
        for prefix in self.DRAMATIC_PREFIXES:
            text = text.replace(prefix, "")

        # Remove code blocks
        text = re.sub(r'```[\s\S]+?```', 'code block', text)

        # Limit length (TTS gets slow on very long text)
        if len(text) > 500:
            text = text[:500] + "... and more."

        return text.strip()

    # ── CONTROL ───────────────────────────────────────────
    def stop(self) -> None:
        """Stop current and queued speech."""
        with self._lock:
            if self._tts_engine and self._is_speaking:
                try:
                    self._tts_engine.stop()
                except Exception:
                    pass

        # Clear queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break

    def shutdown(self) -> None:
        """Shut down TTS system."""
        self._should_stop = True
        self.stop()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=3.0)
        logger.info("VoiceOutput shut down.")

    def set_rate(self, wpm: int) -> None:
        """Set speech rate in words per minute."""
        if self._tts_engine:
            try:
                self._tts_engine.setProperty("rate", max(80, min(300, wpm)))
            except Exception:
                pass

    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)."""
        if self._tts_engine:
            try:
                self._tts_engine.setProperty("volume", max(0.0, min(1.0, volume)))
            except Exception:
                pass

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    @property
    def is_available(self) -> bool:
        return self._is_available

    # ── STATS ─────────────────────────────────────────────
    def get_stats(self) -> Dict[str, Any]:
        return {
            "available":     self._is_available,
            "engine":        self.engine.value,
            "is_speaking":   self._is_speaking,
            "queue_size":    self._queue.qsize(),
            "total_spoken":  self._total_spoken,
            "total_chars":   self._total_chars,
        }