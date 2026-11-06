"""Adminisztrációs felület beállításai."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _

from .models import Category, Transaction, User


class AdminUserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("email",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = AdminUserCreationForm
    form = UserChangeForm
    model = User
    ordering = ("email",)
    list_display = ("email", "last_name", "first_name", "is_staff", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email", "last_name", "first_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Személyes adatok"), {"fields": ("last_name", "first_name")}),
        (
            _("Jogosultságok"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Dátumok"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    readonly_fields = ("last_login", "date_joined")
    filter_horizontal = ("groups", "user_permissions")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "owner", "created_at")
    list_filter = ("type",)
    search_fields = ("name", "owner__email")
    list_select_related = ("owner",)
    ordering = ("owner", "type", "name")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "owner", "category", "type", "amount", "description")
    list_filter = ("type", "category", "date")
    search_fields = ("description", "owner__email", "category__name")
    list_select_related = ("owner", "category")
    date_hierarchy = "date"
    ordering = ("-date", "-created_at")
    autocomplete_fields = ("category",)
