"""Űrlapvalidációs tesztek."""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from finance.forms import (
    CategoryForm,
    RegisterForm,
    TransactionFilterForm,
    TransactionForm,
)
from finance.models import Category

from .base import create_category, create_user


class RegisterFormTests(TestCase):
    def test_valid_registration_lowercases_email(self):
        form = RegisterForm(
            data={
                "email": "Teszt@Example.COM",
                "password1": "Biztonsagos123!",
                "password2": "Biztonsagos123!",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, "teszt@example.com")

    def test_mismatched_passwords_are_rejected(self):
        form = RegisterForm(
            data={
                "email": "teszt@example.com",
                "password1": "Biztonsagos123!",
                "password2": "Masik12345!",
            }
        )
        self.assertFalse(form.is_valid())


class CategoryFormTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.other_user = create_user(email="masik@example.com")

    def test_valid_form_sets_owner(self):
        form = CategoryForm(
            data={"name": "Közlekedés", "type": Category.TYPE_EXPENSE},
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        category = form.save()
        self.assertEqual(category.owner, self.user)

    def test_duplicate_name_and_type_is_rejected(self):
        create_category(self.user, name="Élelmiszer", category_type=Category.TYPE_EXPENSE)
        form = CategoryForm(
            data={"name": "élelmiszer", "type": Category.TYPE_EXPENSE},
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_duplicate_name_for_other_user_is_allowed(self):
        create_category(self.other_user, name="Élelmiszer")
        form = CategoryForm(
            data={"name": "Élelmiszer", "type": Category.TYPE_EXPENSE},
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)


class TransactionFormTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.other_user = create_user(email="masik@example.com")
        self.expense = create_category(self.user, name="Élelmiszer")
        self.income = create_category(
            self.user, name="Fizetés", category_type=Category.TYPE_INCOME
        )
        self.other_category = create_category(self.other_user, name="Idegen")
        self.valid_data = {
            "type": Category.TYPE_EXPENSE,
            "category": self.expense.pk,
            "amount": "1500.50",
            "date": "2026-01-15",
            "description": "Teszt",
        }

    def test_category_queryset_is_user_scoped(self):
        form = TransactionForm(user=self.user)
        ids = list(form.fields["category"].queryset.values_list("pk", flat=True))
        self.assertIn(self.expense.pk, ids)
        self.assertIn(self.income.pk, ids)
        self.assertNotIn(self.other_category.pk, ids)

    def test_valid_form(self):
        form = TransactionForm(data=self.valid_data, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_type_mismatch_is_rejected(self):
        data = dict(self.valid_data, type=Category.TYPE_INCOME)
        form = TransactionForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("type", form.errors)

    def test_zero_amount_is_rejected(self):
        data = dict(self.valid_data, amount="0")
        form = TransactionForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_negative_amount_is_rejected(self):
        data = dict(self.valid_data, amount="-100")
        form = TransactionForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_more_than_two_decimals_is_rejected(self):
        data = dict(self.valid_data, amount="100.123")
        form = TransactionForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_other_users_category_is_rejected(self):
        data = dict(self.valid_data, category=self.other_category.pk)
        form = TransactionForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)


class TransactionFilterFormTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.category = create_category(self.user)

    def test_valid_filter(self):
        form = TransactionFilterForm(
            data={
                "date_from": "2026-01-01",
                "date_to": "2026-01-31",
                "type": Category.TYPE_EXPENSE,
                "category": self.category.pk,
                "q": "teszt",
            },
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_date_range(self):
        form = TransactionFilterForm(
            data={"date_from": "2026-02-01", "date_to": "2026-01-01"},
            user=self.user,
        )
        self.assertFalse(form.is_valid())
