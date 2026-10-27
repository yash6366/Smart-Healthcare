import json
import logging
import urllib.request
from typing import Any
from django.conf import settings
from .base import BaseAIProvider, DISCLAIMER_TEXT
from .mock_provider import MockAIProvider

logger = logging.getLogger("apps.ai_assistant")


class GeminiAIProvider(BaseAIProvider):
    """
    Google Gemini AI Provider for VakCare.
    Falls back gracefully to MockAIProvider if API credentials are not supplied or if service times out.
    """

    def __init__(self):
        self.api_key = getattr(settings, "AI_PROVIDER_API_KEY", "")
        self.model = getattr(settings, "AI_PROVIDER_MODEL", "gemini-2.5-flash")
        self._fallback = MockAIProvider()

    def generate_guidance(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.api_key:
            logger.info("No AI_PROVIDER_API_KEY configured; utilizing MockAIProvider fallback.")
            return self._fallback.generate_guidance(query, context)

        prompt = (
            f"You are a medical healthcare AI triage assistant on the VakCare platform.\n"
            f"User inquiry: {query}\n"
            f"Guidelines:\n"
            f"1. Never provide an absolute diagnosis or prescribe prescription medicines.\n"
            f"2. Explain potential causes and recommended self-care or general wellness steps.\n"
            f"3. Recommend an appropriate medical doctor specialization.\n"
            f"4. If symptoms sound severe (chest pain, stroke signs, difficulty breathing), immediately advise emergency care.\n"
        )

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            req_data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            }
            req = urllib.request.Request(url, data=req_data, headers=headers)

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "provider": f"Gemini ({self.model})",
                    "guidance": text,
                    "disclaimer": DISCLAIMER_TEXT,
                }
        except Exception as exc:
            err_msg = str(exc)
            if self.api_key and self.api_key in err_msg:
                err_msg = err_msg.replace(self.api_key, "[REDACTED]")
            logger.warning("Gemini AI API request encountered an error (%s); falling back to MockAIProvider.", err_msg)
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
            f"Summarize this patient medical record into patient-friendly, easy-to-understand terms:\n"
            f"Title: {title}\n"
            f"Notes: {description}\n"
            f"Vitals: {json.dumps(clinical_data or {})}\n"
            f"Do not disclose confidential metadata."
        )

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            req_data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            }
            req = urllib.request.Request(url, data=req_data, headers=headers)

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "provider": f"Gemini ({self.model})",
                    "summary": text,
                    "disclaimer": DISCLAIMER_TEXT,
                }
        except Exception as exc:
            err_msg = str(exc)
            if self.api_key and self.api_key in err_msg:
                err_msg = err_msg.replace(self.api_key, "[REDACTED]")
            logger.warning("Gemini record summarization failed (%s); using Mock fallback.", err_msg)
            return self._fallback.summarize_medical_record(title, description, clinical_data)
