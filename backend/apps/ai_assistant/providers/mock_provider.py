from typing import Any
from .base import BaseAIProvider, DISCLAIMER_TEXT


class MockAIProvider(BaseAIProvider):
    """
    Mock AI Provider ensuring zero-external-dependency functionality
    for local development, CI/CD testing, and environments where external AI credentials are absent.
    """

    def generate_guidance(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        query_lower = query.lower()

        if "fever" in query_lower:
            recommendation = (
                "Mild fever may indicate an immune response to a viral or bacterial infection. "
                "Stay well hydrated, rest, and monitor your body temperature. If the fever exceeds "
                "102°F (38.9°C), persists for more than 48 hours, or is accompanied by difficulty breathing, "
                "stiff neck, or confusion, seek immediate medical attention from a doctor."
            )
            suggested_specialization = "GENERAL_MEDICINE"
        elif "headache" in query_lower:
            recommendation = (
                "Headaches can arise from stress, dehydration, eye strain, or sinus pressure. "
                "Rest in a quiet, dark room, hydrate, and consider gentle neck stretches. "
                "If the headache is sudden and unusually severe ('thunderclap'), accompanied by visual disturbances, "
                "or weakness on one side, seek emergency care immediately."
            )
            suggested_specialization = "GENERAL_MEDICINE"
        elif "heart" in query_lower or "chest" in query_lower:
            recommendation = (
                "Chest discomfort or pain can be a medical emergency. If you experience crushing chest pain, "
                "radiating pain to the jaw, neck, back, or arm, shortness of breath, dizziness, or cold sweats, "
                "call emergency medical services immediately."
            )
            suggested_specialization = "CARDIOLOGY"
        elif "skin" in query_lower or "rash" in query_lower:
            recommendation = (
                "Skin rashes can result from contact allergies, fungal infections, or eczema. "
                "Avoid scratching the affected area, keep it clean and dry, and note any recent changes in soaps or cosmetics. "
                "Consult a dermatologist for accurate evaluation."
            )
            suggested_specialization = "DERMATOLOGY"
        else:
            recommendation = (
                f"Thank you for your inquiry regarding: '{query}'. Maintaining balanced nutrition, adequate hydration, "
                "and regular physical activity supports general wellness. For personalized clinical diagnosis or prescription, "
                "please schedule a consultation with an appropriate healthcare specialist on VakCare."
            )
            suggested_specialization = "GENERAL_MEDICINE"

        return {
            "provider": "MockAIProvider (Deterministic)",
            "guidance": recommendation,
            "suggested_specialization": suggested_specialization,
            "disclaimer": DISCLAIMER_TEXT,
            "is_emergency_alert": "chest" in query_lower or "heart" in query_lower,
        }

    def summarize_medical_record(
        self,
        title: str,
        description: str,
        clinical_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        facts = [
            f"Record Title: {title}",
            f"Clinical Notes: {description}",
        ]
        if clinical_data:
            facts.append(f"Recorded Vitals & Lab Metrics: {', '.join(f'{k}: {v}' for k, v in clinical_data.items())}")

        explanations = [
            "Plain-Language Meaning: This consultation record documents clinical observations and treatment notes authored by your physician.",
            "Recommended Action: Follow all prescribed medication schedules and contact your doctor if symptoms worsen or change.",
        ]

        summary_text = (
            "--- DOCUMENTED CLINICAL FACTS ---\n"
            + "\n".join(f"• {f}" for f in facts)
            + "\n\n--- PATIENT-FRIENDLY EXPLANATION & GUIDANCE ---\n"
            + "\n".join(f"• {e}" for e in explanations)
        )

        return {
            "provider": "MockAIProvider (Deterministic)",
            "summary": summary_text,
            "disclaimer": DISCLAIMER_TEXT,
        }
