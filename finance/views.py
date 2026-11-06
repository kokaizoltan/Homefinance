"""Nézetek: vezérlőpult, tranzakciók, kategóriák, kimutatások, hitelesítés."""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from .forms import (
    CategoryForm,
    EmailAuthenticationForm,
    RegisterForm,
    TransactionFilterForm,
    TransactionForm,
)
from .models import Category, Transaction
from .services import (
    all_time_totals,
    category_breakdown,
    month_bounds,
    month_label,
    monthly_totals,
    monthly_trend,
    parse_year_month,
    shift_month,
)


# --- Segédosztályok --------------------------------------------------------


class OwnerQuerysetMixin(LoginRequiredMixin):
    """Csak a bejelentkezett felhasználó saját adatait engedi elérni."""

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class CategoryFormMixin:
    """A kategóriaűrlap mindig a bejelentkezett felhasználóhoz kötődjön."""

    form_class = CategoryForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


# --- Hitelesítés -----------------------------------------------------------


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "finance/register.html"
    success_url = reverse_lazy("finance:login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("finance:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Sikeres regisztráció! Most már bejelentkezhetsz az e-mail-címeddel.",
        )
        return response


class LoginView(auth_views.LoginView):
    template_name = "finance/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, "Sikeres bejelentkezés.")
        return super().form_valid(form)


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("finance:login")

    def post(self, request, *args, **kwargs):
        messages.info(request, "Sikeresen kijelentkeztél.")
        return super().post(request, *args, **kwargs)


# --- Vezérlőpult -----------------------------------------------------------


@login_required
def dashboard(request):
    today = timezone.localdate()
    year, month = today.year, today.month

    totals = monthly_totals(request.user, year, month)
    all_time = all_time_totals(request.user)
    expense_ratio = (
        (totals["expense"] / totals["income"] * 100) if totals["income"] else None
    )

    month_start, month_end = month_bounds(year, month)
    expense_breakdown = category_breakdown(
        request.user, Category.TYPE_EXPENSE, month_start, month_end
    )
    income_breakdown = category_breakdown(
        request.user, Category.TYPE_INCOME, month_start, month_end
    )
    trend = monthly_trend(request.user, year, month, months=6)

    recent_transactions = (
        Transaction.objects.filter(owner=request.user)
        .select_related("category")
        .order_by("-date", "-created_at")[:6]
    )

    context = {
        "today": today,
        "year": year,
        "month": month,
        "month_name": month_label(year, month),
        "totals": totals,
        "expense_ratio": expense_ratio,
        "all_time": all_time,
        "expense_breakdown": expense_breakdown[:6],
        "income_breakdown": income_breakdown[:6],
        "recent_transactions": recent_transactions,
        "trend": trend,
        "chart_data": {
            "expense": {
                "labels": [row["name"] for row in expense_breakdown],
                "values": [float(row["total"]) for row in expense_breakdown],
            },
            "income": {
                "labels": [row["name"] for row in income_breakdown],
                "values": [float(row["total"]) for row in income_breakdown],
            },
            "trend": trend,
        },
        "category_count": Category.objects.filter(owner=request.user).count(),
    }
    return render(request, "finance/dashboard.html", context)


# --- Tranzakciók -----------------------------------------------------------


class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = "finance/transaction_list.html"
    context_object_name = "transactions"
    paginate_by = 20

    def get_queryset(self):
        self.filter_form = TransactionFilterForm(
            self.request.GET or None, user=self.request.user
        )
        queryset = Transaction.objects.filter(owner=self.request.user).select_related(
            "category"
        )

        if self.filter_form.is_valid():
            data = self.filter_form.cleaned_data
            if data.get("date_from"):
                queryset = queryset.filter(date__gte=data["date_from"])
            if data.get("date_to"):
                queryset = queryset.filter(date__lte=data["date_to"])
            if data.get("type"):
                queryset = queryset.filter(type=data["type"])
            if data.get("category"):
                queryset = queryset.filter(category=data["category"])
            if data.get("q"):
                queryset = queryset.filter(description__icontains=data["q"])

        self.filtered_totals = queryset.aggregate(
            income=Coalesce(
                Sum("amount", filter=Q(type=Transaction.TYPE_INCOME)),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            expense=Coalesce(
                Sum("amount", filter=Q(type=Transaction.TYPE_EXPENSE)),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            count=Count("id"),
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        totals = self.filtered_totals
        context.update(
            {
                "filter_form": self.filter_form,
                "totals": {
                    "income": totals["income"],
                    "expense": totals["expense"],
                    "balance": totals["income"] - totals["expense"],
                    "count": totals["count"],
                },
                "has_filters": any(
                    value
                    for key, value in self.request.GET.items()
                    if key != "page" and value
                ),
            }
        )
        return context


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "finance/transaction_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "A tranzakció sikeresen mentve.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("finance:transaction_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Új tranzakció",
                "submit_label": "Mentés",
                "cancel_url": reverse("finance:transaction_list"),
            }
        )
        return context


class TransactionUpdateView(OwnerQuerysetMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "finance/transaction_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "A tranzakció sikeresen módosítva.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("finance:transaction_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Tranzakció szerkesztése",
                "submit_label": "Módosítások mentése",
                "cancel_url": reverse("finance:transaction_list"),
            }
        )
        return context


@login_required
@require_POST
def transaction_delete(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, owner=request.user)
    transaction.delete()
    messages.success(request, "A tranzakció törölve.")
    return redirect("finance:transaction_list")


# --- Kategóriák ------------------------------------------------------------


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = "finance/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return (
            Category.objects.filter(owner=self.request.user)
            .annotate(
                transaction_count=Count("transactions"),
                total_amount=Coalesce(
                    Sum("transactions__amount"),
                    Value(Decimal("0")),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
            )
            .order_by("type", "name")
        )


class CategoryCreateView(LoginRequiredMixin, CategoryFormMixin, CreateView):
    model = Category
    template_name = "finance/category_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "A kategória létrehozva.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("finance:category_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Új kategória",
                "submit_label": "Létrehozás",
                "cancel_url": reverse("finance:category_list"),
            }
        )
        return context


class CategoryUpdateView(OwnerQuerysetMixin, CategoryFormMixin, UpdateView):
    model = Category
    template_name = "finance/category_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "A kategória módosítva.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("finance:category_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Kategória szerkesztése",
                "submit_label": "Módosítások mentése",
                "cancel_url": reverse("finance:category_list"),
            }
        )
        return context


@login_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk, owner=request.user)
    if category.transactions.exists():
        messages.error(
            request,
            "A kategória nem törölhető, mert használatban van. "
            "Előbb töröld vagy sorold át a hozzá tartozó tranzakciókat.",
        )
        return redirect("finance:category_list")
    try:
        category.delete()
    except ProtectedError:
        messages.error(
            request,
            "A kategória nem törölhető, mert tranzakciók hivatkoznak rá.",
        )
        return redirect("finance:category_list")
    messages.success(request, "A kategória törölve.")
    return redirect("finance:category_list")


# --- Kimutatások -----------------------------------------------------------


@login_required
def reports(request):
    today = timezone.localdate()
    year, month = parse_year_month(
        request.GET.get("year"), request.GET.get("month"), today=today
    )
    start, end = month_bounds(year, month)

    totals = monthly_totals(request.user, year, month)
    income_breakdown = category_breakdown(request.user, Category.TYPE_INCOME, start, end)
    expense_breakdown = category_breakdown(request.user, Category.TYPE_EXPENSE, start, end)
    trend = monthly_trend(request.user, year, month, months=12)

    transactions = (
        Transaction.objects.filter(
            owner=request.user, date__gte=start, date__lt=end
        )
        .select_related("category")
        .order_by("-date", "-created_at")
    )

    prev_year, prev_month = shift_month(year, month, -1)
    next_year, next_month = shift_month(year, month, 1)

    years = sorted(set(range(today.year - 5, today.year + 2)) | {year})
    months = [(number, f"{number:02d}. hónap") for number in range(1, 13)]

    context = {
        "year": year,
        "month": month,
        "month_name": month_label(year, month),
        "years": years,
        "months": months,
        "totals": totals,
        "income_breakdown": income_breakdown,
        "expense_breakdown": expense_breakdown,
        "trend": trend,
        "transactions": transactions,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "chart_data": {
            "income": {
                "labels": [row["name"] for row in income_breakdown],
                "values": [float(row["total"]) for row in income_breakdown],
            },
            "expense": {
                "labels": [row["name"] for row in expense_breakdown],
                "values": [float(row["total"]) for row in expense_breakdown],
            },
            "trend": trend,
        },
    }
    return render(request, "finance/reports.html", context)
