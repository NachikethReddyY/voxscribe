"""
Microphone audio capture using sounddevice.

Provides a non-blocking recording interface that accumulates audio frames
into a buffer and returns a NumPy array of float32 samples at 16 kHz mono —
exactly the format faster-whisper expects.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

import numpy as np
import sounddevice as sd

if TYPE_CHECKING:
    from voxscribe.config import AudioConfig

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Records audio from the default input device."""

    def __init__(self, config: AudioConfig) -> None:
        self._sample_rate = config.sample_rate
        self._channels = config.channels
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._is_recording = False

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start(self) -> None:
        """Begin capturing audio from the microphone."""
        with self._lock:
            if self._is_recording:
                logger.warning("Recording already in progress, ignoring start().")
                return

            self._frames.clear()
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="float32",
                callback=self._audio_callback,
                blocksize=1024,
            )
            self._stream.start()
            self._is_recording = True
            logger.info(
                "Recording started (rate=%d, channels=%d).",
                self._sample_rate,
                self._channels,
            )

    def stop(self) -> np.ndarray:
        """
        Stop recording and return the captured audio.

        Returns:
            NumPy float32 array of shape (num_samples,) at the configured
            sample rate. Returns an empty array if nothing was recorded.
        """
        with self._lock:
            if not self._is_recording or self._stream is None:
                logger.warning("No active recording to stop.")
                return np.array([], dtype=np.float32)

            self._stream.stop()
            self._stream.close()
            self._stream = None
            self._is_recording = False

        if not self._frames:
            logger.warning("Recording stopped but no frames were captured.")
            return np.array([], dtype=np.float32)

        # Concatenate all captured frames into a single 1-D array
        audio = np.concatenate(self._frames, axis=0).flatten()
        duration = len(audio) / self._sample_rate
        logger.info("Recording stopped. Captured %.2f seconds of audio.", duration)
        return audio

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,  # noqa: ARG002
        time_info: object,  # noqa: ARG002
        status: sd.CallbackFlags,
    ) -> None:
        """sounddevice stream callback — accumulates frames."""
        if status:
            logger.warning("Audio callback status: %s", status)
        self._frames.append(indata.copy())