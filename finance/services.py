"""Üzleti logikai segédfüggvények (összesítések, kimutatások)."""
from datetime import date
from decimal import Decimal

from django.db.models import Count, Q, Sum

from .models import Category, Transaction

ZERO = Decimal("0.00")


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """Adott hónap eltolása delta hónappal (negatív érték is lehet)."""
    index = (year * 12 + (month - 1)) + delta
    return index // 12, index % 12 + 1


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """A hónap [kezdet, következő hónap kezdete) intervalluma."""
    start = date(year, month, 1)
    next_year, next_month = shift_month(year, month, 1)
    end = date(next_year, next_month, 1)
    return start, end


def month_label(year: int, month: int) -> str:
    return f"{year}. {month:02d}."


def period_totals(user, start: date, end: date) -> dict:
    """Bevétel, kiadás, egyenleg és darabszám egy időszakra."""
    aggregate = Transaction.objects.filter(
        owner=user, date__gte=start, date__lt=end
    ).aggregate(
        income=Sum("amount", filter=Q(type=Category.TYPE_INCOME)),
        expense=Sum("amount", filter=Q(type=Category.TYPE_EXPENSE)),
        count=Count("id"),
    )
    income = aggregate["income"] or ZERO
    expense = aggregate["expense"] or ZERO
    return {
        "income": income,
        "expense": expense,
        "balance": income - expense,
        "count": aggregate["count"] or 0,
    }


def monthly_totals(user, year: int, month: int) -> dict:
    start, end = month_bounds(year, month)
    return period_totals(user, start, end)


def all_time_totals(user) -> dict:
    aggregate = Transaction.objects.filter(owner=user).aggregate(
        income=Sum("amount", filter=Q(type=Category.TYPE_INCOME)),
        expense=Sum("amount", filter=Q(type=Category.TYPE_EXPENSE)),
        count=Count("id"),
    )
    income = aggregate["income"] or ZERO
    expense = aggregate["expense"] or ZERO
    return {
        "income": income,
        "expense": expense,
        "balance": income - expense,
        "count": aggregate["count"] or 0,
    }


def category_breakdown(user, category_type: str, start: date, end: date) -> list[dict]:
    """Kategóriánkénti összesítés egy időszakra, csökkenő sorrendben.

    A százalékos arányt is kiszámítja a megadott típus összesített összegéhez képest.
    """
    rows = (
        Transaction.objects.filter(
            owner=user,
            type=category_type,
            date__gte=start,
            date__lt=end,
        )
        .values("category_id", "category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total", "category__name")
    )

    result = []
    grand_total = sum((row["total"] for row in rows), ZERO)
    for row in rows:
        total = row["total"] or ZERO
        percent = (total / grand_total * 100) if grand_total else ZERO
        result.append(
            {
                "category_id": row["category_id"],
                "name": row["category__name"],
                "total": total,
                "percent": round(percent, 1),
            }
        )
    return result


def monthly_trend(user, end_year: int, end_month: int, months: int = 6) -> list[dict]:
    """Az utolsó `months` hónap bevétel/kiadás/egyenleg adatai időrendben."""
    trend = []
    for offset in range(months - 1, -1, -1):
        year, month = shift_month(end_year, end_month, -offset)
        totals = monthly_totals(user, year, month)
        trend.append(
            {
                "label": f"{year}. {month:02d}.",
                "year": year,
                "month": month,
                "income": float(totals["income"]),
                "expense": float(totals["expense"]),
                "balance": float(totals["balance"]),
            }
        )
    return trend


def parse_year_month(year_value, month_value, today: date | None = None) -> tuple[int, int]:
    """Biztonságos év/hónap feldolgozás, érvénytelen érték esetén az aktuális hónap."""
    today = today or date.today()
    try:
        year = int(year_value)
        month = int(month_value)
    except (TypeError, ValueError):
        return today.year, today.month
    if not (1900 <= year <= 2200) or not (1 <= month <= 12):
        return today.year, today.month
    return year, month
