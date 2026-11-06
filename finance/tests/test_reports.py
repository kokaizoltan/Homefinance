"""Vezérlőpult, kimutatások és üzleti logika tesztek."""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from finance.models import Category
from finance.services import (
    all_time_totals,
    category_breakdown,
    month_bounds,
    monthly_totals,
    monthly_trend,
    parse_year_month,
    shift_month,
)

from .base import create_category, create_transaction, create_user


class ShiftMonthTests(TestCase):
    def test_shift_month_within_year(self):
        self.assertEqual(shift_month(2026, 5, 2), (2026, 7))
        self.assertEqual(shift_month(2026, 5, -3), (2026, 2))

    def test_shift_month_across_year_boundaries(self):
        self.assertEqual(shift_month(2026, 12, 1), (2027, 1))
        self.assertEqual(shift_month(2026, 1, -1), (2025, 12))

    def test_month_bounds(self):
        start, end = month_bounds(2026, 12)
        self.assertEqual(start, date(2026, 12, 1))
        self.assertEqual(end, date(2027, 1, 1))


class ParseYearMonthTests(TestCase):
    def test_valid_values(self):
        self.assertEqual(parse_year_month("2025", "7"), (2025, 7))

    def test_invalid_values_fall_back_to_today(self):
        today = date.today()
        self.assertEqual(parse_year_month("abc", "13"), (today.year, today.month))
        self.assertEqual(parse_year_month(None, None), (today.year, today.month))


class ServiceTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.other_user = create_user(email="masik@example.com")
        self.income_category = create_category(
            self.user, name="Fizetés", category_type=Category.TYPE_INCOME
        )
        self.expense_category = create_category(
            self.user, name="Élelmiszer", category_type=Category.TYPE_EXPENSE
        )
        self.other_category = create_category(self.other_user, name="Idegen")
        create_transaction(
            self.user,
            category=self.income_category,
            amount=Decimal("6000.00"),
            date=date(2026, 1, 5),
        )
        create_transaction(
            self.user,
            category=self.income_category,
            amount=Decimal("4000.00"),
            date=date(2026, 1, 20),
        )
        create_transaction(
            self.user,
            category=self.expense_category,
            amount=Decimal("2500.00"),
            date=date(2026, 1, 10),
        )
        create_transaction(
            self.other_user,
            category=self.other_category,
            amount=Decimal("9999.00"),
            date=date(2026, 1, 10),
        )

    def test_monthly_totals_is_user_scoped(self):
        totals = monthly_totals(self.user, 2026, 1)
        self.assertEqual(totals["income"], Decimal("10000.00"))
        self.assertEqual(totals["expense"], Decimal("2500.00"))
        self.assertEqual(totals["balance"], Decimal("7500.00"))
        self.assertEqual(totals["count"], 3)

    def test_monthly_totals_empty_month(self):
        totals = monthly_totals(self.user, 2026, 3)
        self.assertEqual(totals["income"], Decimal("0"))
        self.assertEqual(totals["expense"], Decimal("0"))
        self.assertEqual(totals["count"], 0)

    def test_all_time_totals(self):
        totals = all_time_totals(self.user)
        self.assertEqual(totals["income"], Decimal("10000.00"))
        self.assertEqual(totals["expense"], Decimal("2500.00"))
        self.assertEqual(totals["count"], 3)

    def test_category_breakdown_and_percentages(self):
        start, end = month_bounds(2026, 1)
        rows = category_breakdown(self.user, Category.TYPE_INCOME, start, end)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Fizetés")
        self.assertEqual(rows[0]["total"], Decimal("10000.00"))
        self.assertEqual(rows[0]["percent"], Decimal("100.0"))

    def test_category_breakdown_percentage_split(self):
        second = create_category(
            self.user, name="Bónusz", category_type=Category.TYPE_INCOME
        )
        create_transaction(
            self.user,
            category=second,
            amount=Decimal("5000.00"),
            date=date(2026, 2, 1),
        )
        start, end = month_bounds(2026, 2)
        rows = category_breakdown(self.user, Category.TYPE_INCOME, start, end)
        self.assertEqual(rows[0]["total"], Decimal("5000.00"))
        self.assertEqual(rows[0]["percent"], Decimal("100.0"))

    def test_monthly_trend_contains_requested_months(self):
        trend = monthly_trend(self.user, 2026, 3, months=4)
        self.assertEqual(len(trend), 4)
        self.assertEqual(trend[-1]["label"], "2026. 03.")
        self.assertEqual(trend[0]["label"], "2025. 12.")
        january = next(item for item in trend if item["month"] == 1)
        self.assertEqual(january["income"], 10000.0)
        self.assertEqual(january["expense"], 2500.0)


class DashboardTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.other_user = create_user(email="masik@example.com")
        self.income_category = create_category(
            self.user, name="Fizetés", category_type=Category.TYPE_INCOME
        )
        self.expense_category = create_category(self.user, name="Élelmiszer")
        self.other_category = create_category(self.other_user, name="Idegen")

        today = timezone.localdate()
        self.current_date = today.replace(day=min(today.day, 20))
        create_transaction(
            self.user,
            category=self.income_category,
            amount=Decimal("300000.00"),
            type=Category.TYPE_INCOME,
            date=self.current_date,
        )
        create_transaction(
            self.user,
            category=self.expense_category,
            amount=Decimal("120000.00"),
            date=self.current_date,
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("finance:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_uses_only_current_users_current_month_data(self):
        create_transaction(
            self.other_user,
            category=self.other_category,
            amount=Decimal("999999.00"),
            date=self.current_date,
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("finance:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["totals"]["income"], Decimal("300000.00"))
        self.assertEqual(response.context["totals"]["expense"], Decimal("120000.00"))
        self.assertEqual(response.context["totals"]["balance"], Decimal("180000.00"))
        self.assertEqual(response.context["totals"]["count"], 2)

    def test_dashboard_chart_data(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("finance:dashboard"))
        chart_data = response.context["chart_data"]
        self.assertIn("expense", chart_data)
        self.assertIn("income", chart_data)
        self.assertEqual(len(chart_data["trend"]), 6)
        self.assertEqual(chart_data["expense"]["values"][0], 120000.0)


class ReportsTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.other_user = create_user(email="masik@example.com")
        self.income_category = create_category(
            self.user, name="Fizetés", category_type=Category.TYPE_INCOME
        )
        self.expense_category = create_category(self.user, name="Élelmiszer")
        self.other_category = create_category(self.other_user, name="Idegen")
        create_transaction(
            self.user,
            category=self.income_category,
            amount=Decimal("600000.00"),
            type=Category.TYPE_INCOME,
            date=date(2026, 1, 5),
        )
        create_transaction(
            self.user,
            category=self.expense_category,
            amount=Decimal("200000.00"),
            date=date(2026, 1, 10),
        )
        create_transaction(
            self.other_user,
            category=self.other_category,
            amount=Decimal("999999.00"),
            date=date(2026, 1, 10),
        )

    def test_reports_requires_login(self):
        response = self.client.get(reverse("finance:reports"))
        self.assertEqual(response.status_code, 302)

    def test_reports_selected_month_totals(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("finance:reports"), {"year": 2026, "month": 1}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["year"], 2026)
        self.assertEqual(response.context["month"], 1)
        self.assertEqual(response.context["totals"]["income"], Decimal("600000.00"))
        self.assertEqual(response.context["totals"]["expense"], Decimal("200000.00"))
        self.assertEqual(response.context["totals"]["balance"], Decimal("400000.00"))

    def test_reports_breakdowns(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("finance:reports"), {"year": 2026, "month": 1}
        )
        income = response.context["income_breakdown"]
        expense = response.context["expense_breakdown"]
        self.assertEqual(income[0]["name"], "Fizetés")
        self.assertEqual(income[0]["percent"], Decimal("100.0"))
        self.assertEqual(expense[0]["name"], "Élelmiszer")

    def test_reports_trend_has_twelve_months(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("finance:reports"), {"year": 2026, "month": 1}
        )
        self.assertEqual(len(response.context["trend"]), 12)
        self.assertEqual(response.context["trend"][-1]["label"], "2026. 01.")

    def test_reports_invalid_month_falls_back(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("finance:reports"), {"year": "hibás", "month": "99"}
        )
        today = timezone.localdate()
        self.assertEqual(response.context["year"], today.year)
        self.assertEqual(response.context["month"], today.month)

    def test_reports_do_not_leak_other_users_data(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("finance:reports"), {"year": 2026, "month": 1}
        )
        self.assertEqual(response.context["totals"]["income"], Decimal("600000.00"))
        self.assertNotIn("Idegen", response.context["chart_data"]["income"]["labels"])
