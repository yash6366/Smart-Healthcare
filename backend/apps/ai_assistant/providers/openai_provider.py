import json
import logging
from typing import Any
from django.conf import settings
from .base import BaseAIProvider, DISCLAIMER_TEXT, infer_triage_metadata, post_json, redact_secret
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
        configured_model = getattr(settings, "AI_PROVIDER_MODEL", "") or "gpt-4o-mini"
        if configured_model.lower().startswith("gemini"):
            configured_model = "gpt-4o-mini"
        self.model = configured_model
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
            result = post_json(url, payload, headers, timeout=12)
            text = result["choices"][0]["message"]["content"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("OpenAI API returned an empty guidance response.")

            suggested_specialization, is_emergency = infer_triage_metadata(query, text)

            return {
                "provider": f"OpenAI ({self.model})",
                "guidance": text.strip(),
                "suggested_specialization": suggested_specialization,
                "disclaimer": DISCLAIMER_TEXT,
                "is_emergency_alert": is_emergency,
            }
        except Exception as exc:
            logger.warning(
                "OpenAI API request failed (%s); falling back to MockAIProvider.",
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
            result = post_json(url, payload, headers, timeout=12)
            summary = result["choices"][0]["message"]["content"]
            if not isinstance(summary, str) or not summary.strip():
                raise ValueError("OpenAI API returned an empty summary.")
            return {
                "provider": f"OpenAI ({self.model})",
                "summary": summary.strip(),
                "disclaimer": DISCLAIMER_TEXT,
            }
        except Exception as exc:
            logger.warning(
                "OpenAI record summarization failed (%s); falling back to MockAIProvider.",
                redact_secret(exc, self.api_key),
            )
            return self._fallback.summarize_medical_record(title, description, clinical_data)
