"""Tranzakció CRUD, szűrés, jogosultság és adatelkülönítés tesztek."""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from finance.models import Category, Transaction

from .base import create_category, create_transaction, create_user


class TransactionListTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.other_user = create_user(email="masik@example.com")
        self.category = create_category(self.user, name="Élelmiszer")
        self.income_category = create_category(
            self.user, name="Fizetés", category_type=Category.TYPE_INCOME
        )
        self.other_category = create_category(self.other_user, name="Más kategória")

    def test_list_requires_login(self):
        response = self.client.get(reverse("finance:transaction_list"))
        self.assertEqual(response.status_code, 302)

    def test_list_only_contains_own_transactions(self):
        own = create_transaction(self.user, category=self.category, description="Saját")
        foreign = create_transaction(
            self.other_user, category=self.other_category, description="Idegen"
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("finance:transaction_list"))
        self.assertEqual(response.status_code, 200)
        ids = [item.pk for item in response.context["transactions"]]
        self.assertIn(own.pk, ids)
        self.assertNotIn(foreign.pk, ids)

    def test_filter_by_type(self):
        expense = create_transaction(self.user, category=self.category)
        income = create_transaction(self.user, category=self.income_category)
        self.client.force_login(self.user)

        response = self.client.get(reverse("finance:transaction_list"), {"type": "income"})
        ids = [item.pk for item in response.context["transactions"]]
        self.assertEqual(ids, [income.pk])
        self.assertNotIn(expense.pk, ids)

    def test_filter_by_category(self):
        expense = create_transaction(self.user, category=self.category)
        income = create_transaction(self.user, category=self.income_category)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("finance:transaction_list"), {"category": self.category.pk}
        )
        ids = [item.pk for item in response.context["transactions"]]
        self.assertEqual(ids, [expense.pk])
        self.assertNotIn(income.pk, ids)

    def test_filter_by_date_range(self):
        january = create_transaction(
            self.user, category=self.category, date=date(2026, 1, 10)
        )
        february = create_transaction(
            self.user, category=self.category, date=date(2026, 2, 10)
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("finance:transaction_list"),
            {"date_from": "2026-02-01", "date_to": "2026-02-28"},
        )
        ids = [item.pk for item in response.context["transactions"]]
        self.assertEqual(ids, [february.pk])
        self.assertNotIn(january.pk, ids)

    def test_filter_by_description(self):
        match = create_transaction(
            self.user, category=self.category, description="Heti bevásárlás"
        )
        other = create_transaction(
            self.user, category=self.category, description="Üzemanyag"
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("finance:transaction_list"), {"q": "bevásárlás"}
        )
        ids = [item.pk for item in response.context["transactions"]]
        self.assertEqual(ids, [match.pk])
        self.assertNotIn(other.pk, ids)

    def test_invalid_date_range_shows_error(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("finance:transaction_list"),
            {"date_from": "2026-03-01", "date_to": "2026-01-01"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "nem lehet későbbi")

    def test_filtered_totals(self):
        create_transaction(
            self.user,
            category=self.category,
            amount=Decimal("1000.00"),
            type=Category.TYPE_EXPENSE,
        )
        create_transaction(
            self.user,
            category=self.income_category,
            amount=Decimal("5000.00"),
            type=Category.TYPE_INCOME,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("finance:transaction_list"))
        totals = response.context["totals"]
        self.assertEqual(totals["income"], Decimal("5000.00"))
        self.assertEqual(totals["expense"], Decimal("1000.00"))
        self.assertEqual(totals["balance"], Decimal("4000.00"))
        self.assertEqual(totals["count"], 2)

    def test_pagination(self):
        for _ in range(25):
            create_transaction(self.user, category=self.category)
        self.client.force_login(self.user)

        first_page = self.client.get(reverse("finance:transaction_list"))
        second_page = self.client.get(reverse("finance:transaction_list"), {"page": 2})
        self.assertEqual(len(first_page.context["transactions"]), 20)
        self.assertEqual(len(second_page.context["transactions"]), 5)


class TransactionCrudTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.other_user = create_user(email="masik@example.com")
        self.category = create_category(self.user, name="Élelmiszer")
        self.income_category = create_category(
            self.user, name="Fizetés", category_type=Category.TYPE_INCOME
        )
        self.other_category = create_category(self.other_user, name="Idegen")
        self.client.force_login(self.user)

    def test_create_transaction(self):
        response = self.client.post(
            reverse("finance:transaction_create"),
            {
                "type": Category.TYPE_EXPENSE,
                "category": self.category.pk,
                "amount": "1234.56",
                "date": "2026-03-15",
                "description": "Bevásárlás",
            },
        )
        self.assertRedirects(response, reverse("finance:transaction_list"))
        item = Transaction.objects.get(description="Bevásárlás")
        self.assertEqual(item.owner, self.user)
        self.assertEqual(item.amount, Decimal("1234.56"))
        self.assertEqual(item.category, self.category)

    def test_create_rejects_type_mismatch(self):
        response = self.client.post(
            reverse("finance:transaction_create"),
            {
                "type": Category.TYPE_INCOME,
                "category": self.category.pk,
                "amount": "1000.00",
                "date": "2026-03-15",
                "description": "Hibás",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "meg kell egyeznie")
        self.assertFalse(Transaction.objects.filter(description="Hibás").exists())

    def test_create_rejects_other_users_category(self):
        response = self.client.post(
            reverse("finance:transaction_create"),
            {
                "type": Category.TYPE_EXPENSE,
                "category": self.other_category.pk,
                "amount": "1000.00",
                "date": "2026-03-15",
                "description": "Idegen kategória",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(description="Idegen kategória").exists())

    def test_create_rejects_invalid_amounts(self):
        for amount in ("0.00", "-100.00", "10.123"):
            with self.subTest(amount=amount):
                response = self.client.post(
                    reverse("finance:transaction_create"),
                    {
                        "type": Category.TYPE_EXPENSE,
                        "category": self.category.pk,
                        "amount": amount,
                        "date": "2026-03-15",
                        "description": f"Hibás {amount}",
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(
                    Transaction.objects.filter(description=f"Hibás {amount}").exists()
                )

    def test_update_own_transaction(self):
        item = create_transaction(
            self.user, category=self.category, amount=Decimal("1000.00")
        )
        response = self.client.post(
            reverse("finance:transaction_update", args=[item.pk]),
            {
                "type": Category.TYPE_EXPENSE,
                "category": self.category.pk,
                "amount": "2500.00",
                "date": "2026-04-01",
                "description": "Módosítva",
            },
        )
        self.assertRedirects(response, reverse("finance:transaction_list"))
        item.refresh_from_db()
        self.assertEqual(item.amount, Decimal("2500.00"))
        self.assertEqual(item.description, "Módosítva")

    def test_cannot_update_other_users_transaction(self):
        item = create_transaction(self.other_user, category=self.other_category)
        response = self.client.get(
            reverse("finance:transaction_update", args=[item.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_own_transaction(self):
        item = create_transaction(self.user, category=self.category)
        response = self.client.post(
            reverse("finance:transaction_delete", args=[item.pk])
        )
        self.assertRedirects(response, reverse("finance:transaction_list"))
        self.assertFalse(Transaction.objects.filter(pk=item.pk).exists())

    def test_cannot_delete_other_users_transaction(self):
        item = create_transaction(self.other_user, category=self.other_category)
        response = self.client.post(
            reverse("finance:transaction_delete", args=[item.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Transaction.objects.filter(pk=item.pk).exists())

    def test_delete_requires_post(self):
        item = create_transaction(self.user, category=self.category)
        response = self.client.get(
            reverse("finance:transaction_delete", args=[item.pk])
        )
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Transaction.objects.filter(pk=item.pk).exists())
