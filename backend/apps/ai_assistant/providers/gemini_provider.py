import json
import logging
from typing import Any
from django.conf import settings
from .base import BaseAIProvider, DISCLAIMER_TEXT, infer_triage_metadata, post_json, redact_secret
from .mock_provider import MockAIProvider

logger = logging.getLogger("apps.ai_assistant")


class GeminiAIProvider(BaseAIProvider):
    """
    Google Gemini AI Provider for VakCare.
    Falls back gracefully to MockAIProvider if API credentials are not supplied or if service times out.
    """

    def __init__(self):
        self.api_key = getattr(settings, "AI_PROVIDER_API_KEY", "") or getattr(settings, "GEMINI_API_KEY", "")
        self.model = getattr(settings, "AI_PROVIDER_MODEL", "gemini-3.5-flash")
        self._fallback = MockAIProvider()

    @staticmethod
    def _format_context(context: dict[str, Any] | None) -> str:
        if not context:
            return ""
        history = context.get("history")
        if isinstance(history, list) and history:
            lines = []
            for turn in history[-4:]:
                if isinstance(turn, dict):
                    role = str(turn.get("role", "USER")).upper()
                    content = str(turn.get("content", "")).strip()[:200]
                    if content:
                        lines.append(f"- {role}: {content}")
            if lines:
                return "Recent conversation context:\n" + "\n".join(lines) + "\n\n"
        return f"Additional context: {json.dumps(context)[:400]}\n\n"

    def generate_guidance(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.api_key:
            logger.info("No AI_PROVIDER_API_KEY configured; utilizing MockAIProvider fallback.")
            return self._fallback.generate_guidance(query, context)

        context_block = self._format_context(context)
        prompt = (
            "You are a medical healthcare AI triage assistant on the VakCare platform.\n"
            f"{context_block}"
            f"User inquiry: {query}\n"
            "Guidelines:\n"
            "1. Never provide an absolute diagnosis or prescribe prescription medicines.\n"
            "2. Explain potential causes and recommended self-care or general wellness steps.\n"
            "3. Recommend an appropriate medical doctor specialization.\n"
            "4. If symptoms sound severe (chest pain, stroke signs, difficulty breathing), immediately advise emergency care.\n"
        )

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            }
            result = post_json(url, payload, headers, timeout=15)
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Gemini API returned an empty guidance response.")

            suggested_specialization, is_emergency_alert = infer_triage_metadata(query, text)
            return {
                "provider": f"Gemini ({self.model})",
                "guidance": text.strip(),
                "suggested_specialization": suggested_specialization,
                "disclaimer": DISCLAIMER_TEXT,
                "is_emergency_alert": is_emergency_alert,
            }
        except Exception as exc:
            logger.warning(
                "Gemini AI API request encountered an error (%s); falling back to MockAIProvider.",
                redact_secret(exc, self.api_key),
            )
            return self._fallback.generate_guidance(query, context)

    def summarize_medical_record(
        self,
        title: str,
        description: str,
        clinical_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            return self._fallback.summarize_medical_record(title, description, clinical_data)

        prompt = (
            "Summarize this patient medical record into patient-friendly, easy-to-understand terms:\n"
            f"Title: {title}\n"
            f"Notes: {description}\n"
            f"Vitals: {json.dumps(clinical_data or {})}\n"
            "Do not disclose confidential metadata."
        )

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            }
            result = post_json(url, payload, headers, timeout=15)
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Gemini API returned an empty record summary.")
            return {
                "provider": f"Gemini ({self.model})",
                "summary": text.strip(),
                "disclaimer": DISCLAIMER_TEXT,
            }
        except Exception as exc:
            logger.warning(
                "Gemini record summarization failed (%s); using Mock fallback.",
                redact_secret(exc, self.api_key),
            )
            return self._fallback.summarize_medical_record(title, description, clinical_data)
