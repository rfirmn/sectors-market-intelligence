"""Gemini LLM Client for Smart Research & Mosaic Evidence Synthesis.

Connects to Google Generative Language API v1beta using HTTPX.
Used in Hari 4 (Smart Research & Mosaic Synthesis) and Hari 5 (Thesis Engine).
"""

import asyncio
import logging
from typing import Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Lightweight and robust client for Google Gemini models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ):
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.timeout_seconds = timeout_seconds
        self.endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )

    def _build_payload(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> dict:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "topP": 0.95,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        return payload

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Synchronously generate text using Gemini model."""
        if not self.api_key:
            raise ValueError("LLM_API_KEY is not configured in .env.")

        url = f"{self.endpoint}?key={self.api_key}"
        payload = self._build_payload(prompt, system_instruction, temperature)

        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, json=payload)
            if resp.is_error:
                logger.error("Gemini API error (%d): %s", resp.status_code, resp.text)
                resp.raise_for_status()

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError(f"No candidates returned by Gemini: {data}")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return ""
            return parts[0].get("text", "").strip()

    async def generate_text_async(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Asynchronously generate text using Gemini model."""
        if not self.api_key:
            raise ValueError("LLM_API_KEY is not configured in .env.")

        url = f"{self.endpoint}?key={self.api_key}"
        payload = self._build_payload(prompt, system_instruction, temperature)

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(url, json=payload)
            if resp.is_error:
                logger.error("Gemini API error (%d): %s", resp.status_code, resp.text)
                resp.raise_for_status()

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError(f"No candidates returned by Gemini: {data}")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return ""
            return parts[0].get("text", "").strip()
