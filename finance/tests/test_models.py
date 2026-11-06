"""Adatmodell-tesztek: felhasználó, kategória, tranzakció."""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction as db_transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from finance.models import Category, Transaction, User

from .base import create_category, create_transaction, create_user


class UserModelTests(TestCase):
    def test_create_user_normalizes_email(self):
        user = User.objects.create_user(email="Teszt@Example.COM", password="Titok12345!")
        self.assertEqual(user.email, "teszt@example.com")
        self.assertTrue(user.check_password("Titok12345!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_email_is_unique(self):
        create_user(email="egyedi@example.com")
        with self.assertRaises(IntegrityError), db_transaction.atomic():
            User.objects.create_user(email="egyedi@example.com", password="Titok12345!")

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="Titok12345!")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_get_full_name_and_short_name(self):
        user = create_user(email="nev@example.com", last_name="Kis", first_name="Anna")
        self.assertEqual(user.get_full_name(), "Kis Anna")
        self.assertEqual(user.get_short_name(), "Anna")
        self.assertEqual(str(user), "nev@example.com")

    def test_full_clean_rejects_case_insensitive_duplicate_email(self):
        create_user(email="letezo@example.com")
        user = User(email="LETEZO@example.com")
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_full_clean_normalizes_email(self):
        user = User(email="Nagy@Example.COM")
        user.full_clean(exclude=["password"])
        self.assertEqual(user.email, "nagy@example.com")


class CategoryModelTests(TestCase):
    def setUp(self):
        self.user = create_user()

    def test_category_string_representation(self):
        category = create_category(self.user, name="Élelmiszer")
        self.assertIn("Élelmiszer", str(category))
        self.assertTrue(category.is_expense)
        self.assertFalse(category.is_income)

    def test_duplicate_category_is_rejected_by_database(self):
        create_category(self.user, name="Élelmiszer")
        with self.assertRaises(IntegrityError), db_transaction.atomic():
            Category.objects.create(
                owner=self.user, name="Élelmiszer", type=Category.TYPE_EXPENSE
            )

    def test_same_name_allowed_for_different_type(self):
        create_category(self.user, name="Bónusz", category_type=Category.TYPE_INCOME)
        category = create_category(
            self.user, name="Bónusz", category_type=Category.TYPE_EXPENSE
        )
        self.assertEqual(category.type, Category.TYPE_EXPENSE)

    def test_has_transactions(self):
        category = create_category(self.user)
        self.assertFalse(category.has_transactions())
        create_transaction(self.user, category=category)
        self.assertTrue(category.has_transactions())

    def test_owner_is_required(self):
        category = Category(name="Teszt", type=Category.TYPE_EXPENSE)
        with self.assertRaises(ValidationError):
            category.full_clean()

    def test_type_cannot_change_while_category_is_in_use(self):
        category = create_category(self.user, name="Élelmiszer")
        create_transaction(self.user, category=category)
        category.type = Category.TYPE_INCOME
        with self.assertRaises(ValidationError):
            category.full_clean()

    def test_type_can_change_when_category_is_unused(self):
        category = create_category(self.user, name="Élelmiszer")
        category.type = Category.TYPE_INCOME
        category.full_clean()
        category.save()
        category.refresh_from_db()
        self.assertEqual(category.type, Category.TYPE_INCOME)


class TransactionModelTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.other_user = create_user(email="masik@example.com")
        self.expense_category = create_category(self.user, name="Élelmiszer")
        self.income_category = create_category(
            self.user, name="Fizetés", category_type=Category.TYPE_INCOME
        )

    def test_valid_transaction_is_saved(self):
        item = create_transaction(
            self.user,
            category=self.expense_category,
            amount=Decimal("1234.56"),
            description="Bevásárlás",
        )
        self.assertEqual(item.amount, Decimal("1234.56"))
        self.assertEqual(item.type, Category.TYPE_EXPENSE)
        self.assertIsNotNone(item.pk)

    def test_type_must_match_category_type(self):
        with self.assertRaises(ValidationError):
            create_transaction(
                self.user,
                category=self.income_category,
                type=Category.TYPE_EXPENSE,
            )

    def test_cannot_use_another_users_category(self):
        with self.assertRaises(ValidationError):
            create_transaction(
                self.other_user,
                category=self.expense_category,
            )

    def test_amount_must_be_positive(self):
        for amount in (Decimal("0.00"), Decimal("-5.00")):
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                create_transaction(self.user, category=self.expense_category, amount=amount)

    def test_amount_max_two_decimal_places(self):
        with self.assertRaises(ValidationError):
            create_transaction(
                self.user,
                category=self.expense_category,
                amount=Decimal("10.123"),
            )

    def test_category_with_transactions_cannot_be_deleted(self):
        create_transaction(self.user, category=self.expense_category)
        with self.assertRaises(ProtectedError):
            self.expense_category.delete()

    def test_ordering_is_newest_first(self):
        older = create_transaction(
            self.user, category=self.expense_category, date=date(2026, 1, 1)
        )
        newer = create_transaction(
            self.user, category=self.expense_category, date=date(2026, 2, 1)
        )
        self.assertEqual(list(Transaction.objects.all()), [newer, older])
