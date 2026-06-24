from django.core.management.base import BaseCommand

from apps.logistics.services import poll_active_shipments


class Command(BaseCommand):
    help = "Опрос статусов активных отгрузок (фоллбэк к webhook). PRD 6.7."

    def handle(self, *args, **options):
        count = poll_active_shipments()
        self.stdout.write(self.style.SUCCESS(f"Обновлено отгрузок: {count}"))
