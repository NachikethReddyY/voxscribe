"""
Ollama LLM bridge for Smart Write.

Connects to a locally-running Ollama server to rewrite raw transcriptions
into polished prose. Includes automatic server health detection.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from voxscribe.config import OllamaConfig

logger = logging.getLogger(__name__)


class OllamaRewriter:
    """Rewrites text using a local Ollama-served LLM."""

    def __init__(self, config: OllamaConfig) -> None:
        self._base_url = config.base_url.rstrip("/")
        self._model = config.model
        self._timeout = config.timeout_seconds
        self._system_prompt = config.system_prompt

    def is_available(self) -> bool:
        """
        Check if the Ollama server is reachable and responsive.

        Returns:
            True if the server responds to a health check within 3 seconds.
        """
        try:
            response = httpx.get(f"{self._base_url}/api/tags", timeout=3.0)
            available = response.status_code == 200
            if available:
                models = [m["name"] for m in response.json().get("models", [])]
                logger.info("Ollama is running. Available models: %s", models)
                if not any(self._model in m for m in models):
                    logger.warning(
                        "Configured model '%s' not found in Ollama. "
                        "Available: %s. You may need to run: ollama pull %s",
                        self._model,
                        models,
                        self._model,
                    )
            return available
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning("Ollama server not reachable at %s: %s", self._base_url, exc)
            return False

    def rewrite(self, raw_text: str) -> str:
        """
        Send raw transcription to the LLM for rewriting.

        Args:
            raw_text: The unprocessed transcription from Whisper.

        Returns:
            The polished rewrite from the LLM, or the original text
            if the request fails.
        """
        if not raw_text.strip():
            return raw_text

        payload = {
            "model": self._model,
            "prompt": raw_text,
            "system": self._system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
            },
        }

        try:
            logger.info("Sending text to Ollama for rewriting (%d chars)...", len(raw_text))
            response = httpx.post(
                f"{self._base_url}/api/generate",
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()

            result = response.json()
            rewritten = result.get("response", "").strip()

            if not rewritten:
                logger.warning("Ollama returned an empty response; using original text.")
                return raw_text

            logger.info(
                "Rewrite complete: %d chars → %d chars", len(raw_text), len(rewritten)
            )
            return rewritten

        except httpx.TimeoutException:
            logger.error(
                "Ollama request timed out after %d seconds. Returning original text.",
                self._timeout,
            )
            return raw_text
        except httpx.HTTPStatusError as exc:
            logger.error("Ollama HTTP error %d: %s", exc.response.status_code, exc)
            return raw_text
        except httpx.ConnectError:
            logger.error(
                "Cannot connect to Ollama at %s. Is it running?", self._base_url
            )
            return raw_text