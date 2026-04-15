# ============================================================
# SHADOWFORGE OS — VOICE INPUT SYSTEM
# Real-time speech recognition using SpeechRecognition library.
# Supports: Google, Whisper, Vosk (offline).
# Includes noise filtering, wake word detection, VAD.
# ============================================================

import io
import time
import queue
import logging
import threading
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from core.logger import get_logger

logger = get_logger("Voice.Input")


# ── RECOGNITION ENGINES ───────────────────────────────────
class RecognitionEngine(str, Enum):
    GOOGLE       = "google"       # Free, online, accurate
    GOOGLE_CLOUD = "google_cloud" # Paid, best quality
    WHISPER      = "whisper"      # OpenAI Whisper (offline capable)
    SPHINX       = "sphinx"       # CMU Sphinx (offline, poor quality)
    VOSK         = "vosk"         # Vosk (offline, good quality)
    ASSEMBLYAI   = "assemblyai"   # AssemblyAI API


# ── VOICE STATE ───────────────────────────────────────────
class VoiceState(str, Enum):
    IDLE       = "idle"
    LISTENING  = "listening"
    PROCESSING = "processing"
    ERROR      = "error"
    DISABLED   = "disabled"


# ── VOICE RESULT ──────────────────────────────────────────
@dataclass
class VoiceResult:
    text:       str
    confidence: float = 0.0
    engine:     str   = ""
    duration:   float = 0.0
    raw_audio_size: int = 0
    success:    bool  = True
    error:      str   = ""


# ── VOICE INPUT CLASS ─────────────────────────────────────
class VoiceInput:
    """
    Handles real-time voice input and speech recognition.

    Features:
    - Multiple recognition engine support with fallback
    - Continuous listening mode with VAD (voice activity detection)
    - Wake word detection ("Hey Forge")
    - Noise threshold calibration
    - Thread-safe result queue
    - Platform compatibility checks
    """

    WAKE_WORDS = [
        "hey forge", "shadow forge", "hey shadow",
        "forge listen", "ok forge",
    ]

    DEFAULT_TIMEOUT     = 5.0    # seconds to wait for speech
    DEFAULT_PHRASE_TIME = 15.0   # max phrase duration
    ENERGY_THRESHOLD    = 4000   # microphone sensitivity

    def __init__(
        self,
        engine:             RecognitionEngine = RecognitionEngine.GOOGLE,
        on_result:          Optional[Callable] = None,
        on_state_change:    Optional[Callable] = None,
        language:           str  = "en-US",
        use_wake_word:      bool = False,
        auto_calibrate:     bool = True,
    ):
        self.engine          = engine
        self.on_result       = on_result
        self.on_state_change = on_state_change
        self.language        = language
        self.use_wake_word   = use_wake_word
        self.auto_calibrate  = auto_calibrate

        self._state          = VoiceState.DISABLED
        self._recognizer     = None
        self._microphone     = None
        self._listen_thread: Optional[threading.Thread] = None
        self._stop_event     = threading.Event()
        self._result_queue:  queue.Queue = queue.Queue()
        self._is_available   = False
        self._lock           = threading.Lock()

        # Stats
        self._total_recognized   = 0
        self._total_failed       = 0
        self._session_start_time = 0.0

        self._initialize()

    # ── INITIALIZATION ────────────────────────────────────
    def _initialize(self) -> None:
        """Initialize speech recognition library."""
        try:
            import speech_recognition as sr
            self._sr = sr
            self._recognizer = sr.Recognizer()

            # Configure recognizer
            self._recognizer.energy_threshold          = self.ENERGY_THRESHOLD
            self._recognizer.dynamic_energy_threshold  = True
            self._recognizer.dynamic_energy_adjustment_damping = 0.15
            self._recognizer.dynamic_energy_ratio      = 1.5
            self._recognizer.pause_threshold           = 0.8
            self._recognizer.operation_timeout         = None
            self._recognizer.phrase_threshold          = 0.3
            self._recognizer.non_speaking_duration     = 0.5

            # Test microphone access
            self._microphone = sr.Microphone()
            self._is_available = True
            self._set_state(VoiceState.IDLE)

            logger.info(
                f"VoiceInput initialized. Engine: {self.engine.value}, "
                f"Language: {self.language}"
            )

            # Auto-calibrate
            if self.auto_calibrate:
                self._calibrate()

        except ImportError:
            logger.warning(
                "SpeechRecognition not installed. "
                "Run: pip install SpeechRecognition pyaudio"
            )
            self._is_available = False
        except Exception as e:
            logger.warning(f"Voice input unavailable: {e}")
            self._is_available = False

    def _calibrate(self) -> None:
        """Calibrate microphone for ambient noise."""
        if not self._is_available:
            return
        try:
            with self._microphone as source:
                logger.debug("Calibrating microphone for ambient noise...")
                self._recognizer.adjust_for_ambient_noise(source, duration=1.0)
                logger.debug(
                    f"Calibration done. Energy threshold: "
                    f"{self._recognizer.energy_threshold:.0f}"
                )
        except Exception as e:
            logger.warning(f"Calibration failed: {e}")

    # ── STATE MANAGEMENT ──────────────────────────────────
    def _set_state(self, state: VoiceState) -> None:
        with self._lock:
            self._state = state
        if self.on_state_change:
            try:
                self.on_state_change(state)
            except Exception:
                pass

    @property
    def state(self) -> VoiceState:
        return self._state

    @property
    def is_available(self) -> bool:
        return self._is_available

    @property
    def is_listening(self) -> bool:
        return self._state == VoiceState.LISTENING

    # ── SINGLE CAPTURE ────────────────────────────────────
    def listen_once(
        self,
        timeout:     float = DEFAULT_TIMEOUT,
        phrase_time: float = DEFAULT_PHRASE_TIME,
    ) -> VoiceResult:
        """
        Listen for a single voice input and return the result.
        Blocking call.
        """
        if not self._is_available:
            return VoiceResult(
                text    = "",
                success = False,
                error   = "Voice input not available",
            )

        self._set_state(VoiceState.LISTENING)
        start_time = time.perf_counter()

        try:
            with self._microphone as source:
                logger.debug(f"Listening... (timeout={timeout}s)")

                try:
                    audio = self._recognizer.listen(
                        source,
                        timeout          = timeout,
                        phrase_time_limit = phrase_time,
                    )
                except self._sr.WaitTimeoutError:
                    self._set_state(VoiceState.IDLE)
                    return VoiceResult(
                        text    = "",
                        success = False,
                        error   = "Timeout: no speech detected",
                    )

            self._set_state(VoiceState.PROCESSING)

            # Recognize
            result = self._recognize(audio)
            duration = time.perf_counter() - start_time
            result.duration = duration

            if result.success:
                self._total_recognized += 1
                logger.info(f"Recognized: '{result.text[:80]}' ({duration:.1f}s)")
            else:
                self._total_failed += 1
                logger.debug(f"Recognition failed: {result.error}")

            self._set_state(VoiceState.IDLE)
            return result

        except Exception as e:
            self._set_state(VoiceState.ERROR)
            logger.error(f"Voice capture error: {e}")
            return VoiceResult(text="", success=False, error=str(e))

    # ── RECOGNITION ENGINE ────────────────────────────────
    def _recognize(self, audio) -> VoiceResult:
        """
        Run speech recognition on captured audio.
        Tries configured engine with fallback to Google.
        """
        try:
            audio_size = len(audio.get_wav_data())
        except Exception:
            audio_size = 0

        engines_to_try = [self.engine]
        if self.engine != RecognitionEngine.GOOGLE:
            engines_to_try.append(RecognitionEngine.GOOGLE)  # Fallback

        last_error = ""

        for engine in engines_to_try:
            try:
                text = self._run_engine(audio, engine)
                if text:
                    return VoiceResult(
                        text           = text.strip(),
                        confidence     = 0.9,
                        engine         = engine.value,
                        raw_audio_size = audio_size,
                        success        = True,
                    )
            except self._sr.UnknownValueError:
                last_error = "Could not understand audio"
            except self._sr.RequestError as e:
                last_error = f"API error: {str(e)[:100]}"
                logger.warning(f"Engine {engine.value} failed: {e}")
                continue
            except Exception as e:
                last_error = str(e)[:100]
                continue

        return VoiceResult(
            text    = "",
            success = False,
            error   = last_error or "Recognition failed",
        )

    def _run_engine(self, audio, engine: RecognitionEngine) -> str:
        """Run a specific recognition engine."""
        if engine == RecognitionEngine.GOOGLE:
            return self._recognizer.recognize_google(
                audio, language=self.language
            )
        elif engine == RecognitionEngine.WHISPER:
            return self._recognizer.recognize_whisper(
                audio, language=self.language.split("-")[0]
            )
        elif engine == RecognitionEngine.SPHINX:
            return self._recognizer.recognize_sphinx(audio)
        elif engine == RecognitionEngine.VOSK:
            return self._recognize_vosk(audio)
        else:
            return self._recognizer.recognize_google(
                audio, language=self.language
            )

    def _recognize_vosk(self, audio) -> str:
        """Vosk offline recognition."""
        try:
            from vosk import Model, KaldiRecognizer
            import json as _json

            model_path = Path.home() / ".vosk" / "model"
            if not model_path.exists():
                raise Exception(
                    "Vosk model not found. "
                    "Download from: https://alphacephei.com/vosk/models"
                )

            model = Model(str(model_path))
            rec   = KaldiRecognizer(model, 16000)
            wav   = audio.get_wav_data(convert_rate=16000, convert_width=2)
            rec.AcceptWaveform(wav)
            result = _json.loads(rec.FinalResult())
            return result.get("text", "")
        except ImportError:
            raise Exception("Vosk not installed: pip install vosk")

    # ── CONTINUOUS LISTENING ──────────────────────────────
    def start_continuous(
        self,
        callback:    Optional[Callable] = None,
        timeout:     float = DEFAULT_TIMEOUT,
        phrase_time: float = DEFAULT_PHRASE_TIME,
    ) -> bool:
        """
        Start continuous background listening.
        Calls callback(VoiceResult) for each recognized phrase.
        """
        if not self._is_available:
            logger.warning("Voice input not available.")
            return False

        if self.is_listening:
            logger.warning("Already listening.")
            return True

        self._stop_event.clear()
        cb = callback or self.on_result

        def _listen_loop():
            logger.info("Continuous listening started.")
            self._session_start_time = time.time()

            while not self._stop_event.is_set():
                result = self.listen_once(timeout=timeout, phrase_time=phrase_time)

                if result.success and result.text:
                    # Wake word check
                    if self.use_wake_word:
                        if not self._check_wake_word(result.text):
                            continue  # Ignore if no wake word
                        result.text = self._strip_wake_word(result.text)

                    # Put in queue
                    self._result_queue.put(result)

                    # Call callback
                    if cb:
                        try:
                            cb(result)
                        except Exception as e:
                            logger.error(f"Voice callback error: {e}")

                elif result.error and "Timeout" not in result.error:
                    logger.debug(f"Voice error: {result.error}")

            logger.info("Continuous listening stopped.")
            self._set_state(VoiceState.IDLE)

        self._listen_thread = threading.Thread(
            target=_listen_loop,
            name="ShadowVoiceInput",
            daemon=True,
        )
        self._listen_thread.start()
        self._set_state(VoiceState.LISTENING)
        return True

    def stop_continuous(self) -> None:
        """Stop continuous listening."""
        self._stop_event.set()
        if self._listen_thread and self._listen_thread.is_alive():
            self._listen_thread.join(timeout=5.0)
        self._set_state(VoiceState.IDLE)
        logger.info("Voice listening stopped.")

    # ── WAKE WORD ─────────────────────────────────────────
    def _check_wake_word(self, text: str) -> bool:
        """Check if text contains a wake word."""
        text_lower = text.lower()
        return any(ww in text_lower for ww in self.WAKE_WORDS)

    def _strip_wake_word(self, text: str) -> str:
        """Remove wake word from beginning of text."""
        text_lower = text.lower()
        for ww in self.WAKE_WORDS:
            if text_lower.startswith(ww):
                return text[len(ww):].strip().lstrip(",").strip()
        return text

    # ── QUEUE ACCESS ──────────────────────────────────────
    def get_result(self, timeout: float = 0.1) -> Optional[VoiceResult]:
        """Get next result from queue (non-blocking with timeout)."""
        try:
            return self._result_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_all_results(self) -> List[VoiceResult]:
        """Get all pending results from queue."""
        results = []
        while True:
            result = self.get_result(timeout=0.01)
            if result is None:
                break
            results.append(result)
        return results

    # ── DEVICE INFO ───────────────────────────────────────
    def get_available_microphones(self) -> List[Dict[str, Any]]:
        """Get list of available audio input devices."""
        if not self._is_available:
            return []
        try:
            import speech_recognition as sr
            mic_list = sr.Microphone.list_microphone_names()
            return [
                {"index": i, "name": name}
                for i, name in enumerate(mic_list)
            ]
        except Exception as e:
            logger.warning(f"Could not list microphones: {e}")
            return []

    # ── STATS ─────────────────────────────────────────────
    def get_stats(self) -> Dict[str, Any]:
        return {
            "available":       self._is_available,
            "state":           self._state.value,
            "engine":          self.engine.value,
            "language":        self.language,
            "total_recognized":self._total_recognized,
            "total_failed":    self._total_failed,
            "accuracy_pct": (
                round(self._total_recognized /
                      max(1, self._total_recognized + self._total_failed) * 100, 1)
            ),
            "energy_threshold": (
                self._recognizer.energy_threshold
                if self._recognizer else 0
            ),
        }

    def __del__(self):
        self.stop_continuous()