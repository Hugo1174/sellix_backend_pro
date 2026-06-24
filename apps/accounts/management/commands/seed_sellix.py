"""Сид-данные для разработки/демо (PRD 3.2.4 — категории, 3.5 — суперадмин)."""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.accounts.constants import AuthProvider, Role
from apps.accounts.models import User
from apps.catalog.models import Category

DEFAULT_CATEGORIES = [
    "Одежда и обувь", "Электроника", "Товары для дома", "Красота и здоровье",
    "Продукты питания", "Детские товары", "Спорт и отдых", "Книги", "Прочее",
]


class Command(BaseCommand):
    help = "Создаёт суперадмина и базовые категории."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="admin@mysellix.ru")
        parser.add_argument("--password", default="admin12345")

    @transaction.atomic
    def handle(self, *args, **opts):
        email = opts["email"]
        admin, created = User.objects.get_or_create(
            email=email,
            defaults={"role": Role.ADMIN, "auth_provider": AuthProvider.LOCAL,
                      "is_staff": True, "is_superuser": True, "full_name": "Суперадмин"},
        )
        if created:
            admin.set_password(opts["password"])
            admin.save()
            self.stdout.write(self.style.SUCCESS(f"Суперадмин создан: {email}"))
        else:
            self.stdout.write(f"Суперадмин уже существует: {email}")

        made = 0
        for idx, name in enumerate(DEFAULT_CATEGORIES, start=1):
            base = slugify(name, allow_unicode=False) or f"cat-{idx}"
            _, c = Category.objects.get_or_create(
                name=name, defaults={"slug": base},
            )
            made += int(c)
        self.stdout.write(self.style.SUCCESS(f"Категорий добавлено: {made}"))
