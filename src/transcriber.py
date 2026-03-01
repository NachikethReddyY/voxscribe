"""
Whisper transcription bridge using faster-whisper.

Loads a CTranslate2-optimized Whisper model and transcribes NumPy audio
buffers to text. The model is loaded lazily on first use to avoid blocking
application startup.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from faster_whisper import WhisperModel

if TYPE_CHECKING:
    from voxscribe.config import WhisperConfig

logger = logging.getLogger(__name__)


class Transcriber:
    """Wraps faster-whisper for local speech-to-text."""

    def __init__(self, config: WhisperConfig) -> None:
        self._model_path = config.model_path
        self._device = config.device
        self._compute_type = config.compute_type
        self._language = config.language
        self._model: WhisperModel | None = None

    def _ensure_model(self) -> WhisperModel:
        """Lazy-load the Whisper model on first transcription request."""
        if self._model is None:
            logger.info(
                "Loading Whisper model '%s' (device=%s, compute=%s)...",
                self._model_path,
                self._device,
                self._compute_type,
            )
            self._model = WhisperModel(
                self._model_path,
                device=self._device,
                compute_type=self._compute_type,
            )
            logger.info("Whisper model loaded successfully.")
        return self._model

    def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribe a float32 audio buffer to text.

        Args:
            audio: 1-D NumPy float32 array at 16 kHz.

        Returns:
            Transcribed text string. Empty string if audio is too short
            or no speech is detected.
        """
        if audio.size == 0:
            logger.warning("Empty audio buffer — nothing to transcribe.")
            return ""

        # faster-whisper requires float32 in [-1, 1] range
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        model = self._ensure_model()

        logger.info("Transcribing %.2f seconds of audio...", len(audio) / 16000)
        segments, info = model.transcribe(
            audio,
            language=self._language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        # Consume the generator and join all segment texts
        full_text = " ".join(segment.text.strip() for segment in segments)
        full_text = full_text.strip()

        logger.info(
            "Transcription complete (lang=%s, prob=%.2f): %d chars",
            info.language,
            info.language_probability,
            len(full_text),
        )
        return full_text

    def unload(self) -> None:
        """Release the model from memory."""
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Whisper model unloaded.")