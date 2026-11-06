"""Az alkalmazás URL-jei."""
from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tranzakciok/", views.TransactionListView.as_view(), name="transaction_list"),
    path(
        "tranzakciok/uj/",
        views.TransactionCreateView.as_view(),
        name="transaction_create",
    ),
    path(
        "tranzakciok/<int:pk>/szerkesztes/",
        views.TransactionUpdateView.as_view(),
        name="transaction_update",
    ),
    path(
        "tranzakciok/<int:pk>/torles/",
        views.transaction_delete,
        name="transaction_delete",
    ),
    path("kategoriak/", views.CategoryListView.as_view(), name="category_list"),
    path(
        "kategoriak/uj/",
        views.CategoryCreateView.as_view(),
        name="category_create",
    ),
    path(
        "kategoriak/<int:pk>/szerkesztes/",
        views.CategoryUpdateView.as_view(),
        name="category_update",
    ),
    path(
        "kategoriak/<int:pk>/torles/",
        views.category_delete,
        name="category_delete",
    ),
    path("kimutatasok/", views.reports, name="reports"),
    path("regisztracio/", views.RegisterView.as_view(), name="register"),
    path("belepes/", views.LoginView.as_view(), name="login"),
    path("kilepes/", views.LogoutView.as_view(), name="logout"),
]
