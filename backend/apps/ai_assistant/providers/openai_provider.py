import json
import logging
import urllib.request
from typing import Any
from django.conf import settings
from .base import BaseAIProvider, DISCLAIMER_TEXT
from .mock_provider import MockAIProvider

logger = logging.getLogger("apps.ai_assistant")


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI Provider (e.g. GPT-4o-mini, GPT-4o) for VakCare.
    Provides medical information assistance, structured summarization,
    and conversational AI guidance with safe clinical boundaries.
    Falls back gracefully to MockAIProvider if API key is not configured or on network error.
    """

    def __init__(self):
        self.api_key = getattr(settings, "AI_PROVIDER_API_KEY", "") or getattr(settings, "OPENAI_API_KEY", "")
        self.model = getattr(settings, "AI_PROVIDER_MODEL", "gpt-4o-mini")
        self._fallback = MockAIProvider()

    def generate_guidance(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.api_key:
            logger.info("No OpenAI API key configured; using MockAIProvider fallback.")
            return self._fallback.generate_guidance(query, context)

        system_prompt = (
            "You are a medical healthcare AI triage assistant on the VakCare platform.\n"
            "Guidelines:\n"
            "1. You must NEVER provide a definitive clinical diagnosis or prescribe prescription drugs.\n"
            "2. Offer helpful health education, self-care measures, and lifestyle guidance.\n"
            "3. Identify the most suitable medical doctor specialization (e.g. GENERAL_MEDICINE, CARDIOLOGY, DERMATOLOGY, PEDIATRICS).\n"
            "4. If symptoms sound severe or life-threatening (e.g. chest pain, shortness of breath, sudden weakness), immediately advise emergency care.\n"
            "5. Always append the required clinical disclaimer."
        )

        user_content = f"User health inquiry: {query}"
        if context:
            user_content += f"\nContext: {json.dumps(context)}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.4,
            "max_tokens": 600,
        }

        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)

            with urllib.request.urlopen(req, timeout=12) as response:
                result = json.loads(response.read().decode("utf-8"))
                text = result["choices"][0]["message"]["content"]

                # Check if emergency triage is required
                lower_text = text.lower()
                is_emergency = any(kw in lower_text for kw in ["emergency", "911", "call ambulance", "hospital immediately"])

                return {
                    "provider": f"OpenAI ({self.model})",
                    "guidance": text,
                    "disclaimer": DISCLAIMER_TEXT,
                    "is_emergency_alert": is_emergency,
                }
        except Exception as exc:
            err_msg = str(exc)
            if self.api_key and self.api_key in err_msg:
                err_msg = err_msg.replace(self.api_key, "[REDACTED]")
            logger.warning("OpenAI API request failed (%s); falling back to MockAIProvider.", err_msg)
            return self._fallback.generate_guidance(query, context)

    def summarize_medical_record(
        self,
        title: str,
        description: str,
        clinical_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            return self._fallback.summarize_medical_record(title, description, clinical_data)

        system_prompt = (
            "You are a clinical documentation assistant on the VakCare platform. "
            "Summarize the patient's medical record into patient-friendly, clear, bulleted takeaways. "
            "Explain medical terms simply, outline actionable follow-up instructions, and preserve confidentiality."
        )

        user_content = (
            f"Title: {title}\n"
            f"Doctor Notes: {description}\n"
            f"Vitals / Clinical Data: {json.dumps(clinical_data or {})}"
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.3,
            "max_tokens": 500,
        }

        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)

            with urllib.request.urlopen(req, timeout=12) as response:
                result = json.loads(response.read().decode("utf-8"))
                summary = result["choices"][0]["message"]["content"]
                return {
                    "provider": f"OpenAI ({self.model})",
                    "summary": summary,
                    "disclaimer": DISCLAIMER_TEXT,
                }
        except Exception as exc:
            err_msg = str(exc)
            if self.api_key and self.api_key in err_msg:
                err_msg = err_msg.replace(self.api_key, "[REDACTED]")
            logger.warning("OpenAI record summarization failed (%s); falling back to MockAIProvider.", err_msg)
            return self._fallback.summarize_medical_record(title, description, clinical_data)
