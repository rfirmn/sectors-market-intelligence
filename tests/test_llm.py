"""Unit tests for GeminiClient with offline respx mocks."""

import respx

from src.research.llm import GeminiClient


@respx.mock
def test_gemini_client_success():
    """Verify GeminiClient parses valid candidate response."""
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"
    mock_body = {
        "candidates": [
            {"content": {"parts": [{"text": "Variant perception: Market is skeptical."}]}}
        ]
    }
    respx.post(endpoint).respond(200, json=mock_body)

    client = GeminiClient(api_key="mock_key", model="gemini-3.5-flash-lite")
    res = client.generate_text(prompt="Explain gap")

    assert res == "Variant perception: Market is skeptical."
