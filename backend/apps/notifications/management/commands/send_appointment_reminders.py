from django.core.management.base import BaseCommand
from apps.notifications.services import generate_appointment_reminders


class Command(BaseCommand):
    help = "Dispatches in-app appointment reminder notifications for confirmed upcoming consultations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--lead-hours",
            type=int,
            default=48,
            help="Lead window in hours to scan for upcoming appointments (default: 48).",
        )

    def handle(self, *args, **options):
        lead_hours = options["lead_hours"]
        self.stdout.write(f"Scanning for confirmed consultations within the next {lead_hours} hours...")
        sent_count = generate_appointment_reminders(lead_hours=lead_hours)
        self.stdout.write(self.style.SUCCESS(f"Successfully generated {sent_count} appointment reminders."))
