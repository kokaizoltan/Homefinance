"""Demó adatok létrehozása a fejlesztéshez és kipróbáláshoz.

Használat:
    python manage.py seed_demo
"""
import calendar
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from finance.models import Category, Transaction, User
from finance.services import shift_month


class Command(BaseCommand):
    help = "Létrehoz egy demó felhasználót kategóriákkal és tranzakciókkal."

    def handle(self, *args, **options):
        email = "demo@homefinance.hu"
        password = "Demo12345!"

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "last_name": "Demó",
                "first_name": "Felhasználó",
                "is_active": True,
            },
        )
        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS(f"Demó felhasználó létrehozva: {email}"))
        else:
            self.stdout.write(f"A demó felhasználó már létezik: {email}")

        if Transaction.objects.filter(owner=user).exists():
            self.stdout.write(
                self.style.WARNING("A demó adatok már korábban létrejöttek, kihagyom.")
            )
            self.stdout.write(f"Bejelentkezés: {email} / {password}")
            return

        category_specs = [
            ("Fizetés", Category.TYPE_INCOME),
            ("Egyéb bevétel", Category.TYPE_INCOME),
            ("Élelmiszer", Category.TYPE_EXPENSE),
            ("Lakhatás", Category.TYPE_EXPENSE),
            ("Közlekedés", Category.TYPE_EXPENSE),
            ("Szórakozás", Category.TYPE_EXPENSE),
            ("Egészség", Category.TYPE_EXPENSE),
        ]
        categories = {}
        for name, category_type in category_specs:
            category, _ = Category.objects.get_or_create(
                owner=user, name=name, type=category_type
            )
            categories[name] = category

        today = timezone.localdate()

        for offset in range(3):
            year, month = shift_month(today.year, today.month, -offset)
            last_day = calendar.monthrange(year, month)[1]

            def on(day):
                return date(year, month, min(day, last_day))

            Transaction.objects.create(
                owner=user,
                category=categories["Fizetés"],
                type=Category.TYPE_INCOME,
                amount=Decimal("650000.00"),
                date=on(5),
                description=f"Fizetés – {year}. {month:02d}.",
            )
            Transaction.objects.create(
                owner=user,
                category=categories["Élelmiszer"],
                type=Category.TYPE_EXPENSE,
                amount=Decimal("82450.00") + Decimal(offset * 3500),
                date=on(12),
                description="Havi nagybevásárlás",
            )
            Transaction.objects.create(
                owner=user,
                category=categories["Lakhatás"],
                type=Category.TYPE_EXPENSE,
                amount=Decimal("145000.00"),
                date=on(8),
                description="Rezsi és bérleti díj",
            )
            Transaction.objects.create(
                owner=user,
                category=categories["Közlekedés"],
                type=Category.TYPE_EXPENSE,
                amount=Decimal("22500.00"),
                date=on(15),
                description="Üzemanyag",
            )
            Transaction.objects.create(
                owner=user,
                category=categories["Szórakozás"],
                type=Category.TYPE_EXPENSE,
                amount=Decimal("18900.00"),
                date=on(20),
                description="Mozi és vacsora",
            )
            Transaction.objects.create(
                owner=user,
                category=categories["Egészség"],
                type=Category.TYPE_EXPENSE,
                amount=Decimal("7500.00"),
                date=on(24),
                description="Patika",
            )

            if offset == 0:
                Transaction.objects.create(
                    owner=user,
                    category=categories["Egyéb bevétel"],
                    type=Category.TYPE_INCOME,
                    amount=Decimal("35000.00"),
                    date=on(26),
                    description="Visszatérítés",
                )

        self.stdout.write(self.style.SUCCESS("Demó adatok sikeresen létrehozva."))
        self.stdout.write(f"Bejelentkezés: {email} / {password}")
