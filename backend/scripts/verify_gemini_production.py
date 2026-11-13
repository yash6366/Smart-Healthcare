"""
Verification script for Gemini AI Provider in production configuration.
Does not print or expose secret keys or credentials.
"""
import os
import sys
import time
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
os.environ.setdefault("DJANGO_SECRET_KEY", "production-readiness-verification-temporary-key-at-least-40-chars")
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,vakcare.vercel.app")

import django
django.setup()

from django.conf import settings
from apps.ai_assistant.providers.gemini_provider import GeminiAIProvider
from apps.ai_assistant.providers.base import DISCLAIMER_TEXT, redact_secret
from apps.ai_assistant.providers.factory import get_ai_provider

def verify_gemini():
    print("=" * 60)
    print("VakCare AI Provider Production Verification")
    print("=" * 60)

    provider_name = getattr(settings, "AI_PROVIDER", "unknown")
    model_name = getattr(settings, "AI_PROVIDER_MODEL", "unknown")
    api_key_configured = bool(getattr(settings, "AI_PROVIDER_API_KEY", "") or getattr(settings, "GEMINI_API_KEY", ""))

    print(f"Configured Provider   : {provider_name}")
    print(f"Configured Model      : {model_name}")
    print(f"API Key Present       : {'YES (Configured)' if api_key_configured else 'NO (Missing)'}")

    provider = get_ai_provider()
    print(f"Instantiated Provider : {type(provider).__name__}")

    # 1. Live Guidance Generation & Model Availability / Quota Check
    print("\n[1] Testing Live Model Availability and API Quota...")
    start_time = time.time()
    query = "I have a mild sore throat and a slight headache for two days. What should I do?"
    
    response = provider.generate_guidance(query)
    elapsed = time.time() - start_time
    
    provider_used = response.get("provider", "")
    guidance = response.get("guidance", "")
    spec = response.get("suggested_specialization", "")
    disclaimer = response.get("disclaimer", "")
    emergency = response.get("is_emergency_alert", False)

    print(f"  Response Provider   : {provider_used}")
    print(f"  Latency             : {elapsed:.2f}s")
    print(f"  Guidance Length     : {len(guidance)} chars")
    print(f"  Triage Specialization: {spec}")
    print(f"  Emergency Flag      : {emergency}")
    print(f"  Disclaimer Present  : {disclaimer == DISCLAIMER_TEXT}")

    # Check if live or fallback was used
    if "MockAIProvider" in provider_used:
        print("  Notice: MockAIProvider fallback was utilized (live API may be unreachable, rate limited, or returned non-200).")
    else:
        print("  SUCCESS: Live Gemini API responded successfully!")

    # 2. Medical Record Summarization Check
    print("\n[2] Testing Medical Record Summarization...")
    summary_resp = provider.summarize_medical_record(
        title="Routine Health Checkup",
        description="Patient presents with blood pressure 120/80 mmHg, pulse 72 bpm. Heart and lung sounds clear. Mild seasonal allergies noted.",
        clinical_data={"bp": "120/80", "pulse": 72}
    )
    print(f"  Summary Provider    : {summary_resp.get('provider')}")
    print(f"  Summary Length      : {len(summary_resp.get('summary', ''))} chars")
    print(f"  Disclaimer Present  : {summary_resp.get('disclaimer') == DISCLAIMER_TEXT}")

    # 3. Emergency Detection Check
    print("\n[3] Testing Emergency Detection & Immediate Escalation...")
    emergency_resp = provider.generate_guidance("Crushing central chest pain radiating to left arm with shortness of breath")
    print(f"  Emergency Inquiry Alert: {emergency_resp.get('is_emergency_alert')}")
    print(f"  Emergency Specialization: {emergency_resp.get('suggested_specialization')}")

    # 4. Fallback Behavior & Sensitive-Data Redaction Check
    print("\n[4] Testing Error Handling, Timeout & Secret Redaction...")
    dummy_key = "AIzaSyTestSecretDummyKey123456789"
    test_err = RuntimeError(f"Connection failed to https://generativelanguage.googleapis.com?key={dummy_key} with Bearer ya29.test_token")
    redacted = redact_secret(test_err, dummy_key)
    has_secret_leaked = dummy_key in redacted or "ya29.test_token" in redacted
    print(f"  Secret Redacted     : {not has_secret_leaked}")
    print(f"  Redacted Message    : {redacted}")

    print("=" * 60)

if __name__ == "__main__":
    verify_gemini()

