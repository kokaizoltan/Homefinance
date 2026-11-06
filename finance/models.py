"""Adatmodellek: felhasználó, kategória és tranzakció."""
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """E-mail alapú felhasználókezelő."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Az e-mail cím megadása kötelező.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("A szuperfelhasználónak is_staff=True értékkel kell rendelkeznie.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                "A szuperfelhasználónak is_superuser=True értékkel kell rendelkeznie."
            )
        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, username):
        """Az e-mail-cím alapú bejelentkezés kis- és nagybetűtől független."""
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})


class User(AbstractBaseUser, PermissionsMixin):
    """Egyedi e-mail-címmel rendelkező felhasználó."""

    email = models.EmailField(_("e-mail cím"), unique=True)
    last_name = models.CharField(_("vezetéknév"), max_length=100, blank=True)
    first_name = models.CharField(_("keresztnév"), max_length=100, blank=True)
    is_active = models.BooleanField(_("aktív"), default=True)
    is_staff = models.BooleanField(_("adminisztrátor"), default=False)
    date_joined = models.DateTimeField(_("regisztráció dátuma"), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("felhasználó")
        verbose_name_plural = _("felhasználók")
        ordering = ["email"]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.last_name} {self.first_name}".strip() or self.email

    def get_short_name(self):
        return self.first_name or self.email.split("@")[0]

    def clean(self):
        if self.email:
            self.email = self.email.strip().lower()
            duplicates = self.__class__.objects.filter(email__iexact=self.email)
            if self.pk:
                duplicates = duplicates.exclude(pk=self.pk)
            if duplicates.exists():
                raise ValidationError(
                    {"email": _("Ezzel az e-mail-címmel már létezik felhasználó.")}
                )
        super().clean()


class Category(models.Model):
    """Bevételi vagy kiadási kategória, felhasználónként elkülönítve."""

    TYPE_INCOME = "income"
    TYPE_EXPENSE = "expense"
    TYPE_CHOICES = [
        (TYPE_INCOME, _("Bevétel")),
        (TYPE_EXPENSE, _("Kiadás")),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
        verbose_name=_("tulajdonos"),
    )
    name = models.CharField(_("név"), max_length=100)
    type = models.CharField(_("típus"), max_length=10, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(_("létrehozva"), auto_now_add=True)
    updated_at = models.DateTimeField(_("módosítva"), auto_now=True)

    class Meta:
        verbose_name = _("kategória")
        verbose_name_plural = _("kategóriák")
        ordering = ["type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name", "type"],
                name="unique_category_per_owner_and_type",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    def clean(self):
        if self.name:
            self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": _("A kategória neve nem lehet üres.")})

        if self.pk:
            original_type = (
                self.__class__.objects.filter(pk=self.pk)
                .values_list("type", flat=True)
                .first()
            )
            if (
                original_type
                and original_type != self.type
                and self.transactions.exists()
            ):
                raise ValidationError(
                    {
                        "type": _(
                            "A használatban lévő kategória típusa nem módosítható. "
                            "Előbb sorold át vagy töröld a hozzá tartozó tranzakciókat."
                        )
                    }
                )

        super().clean()

    def has_transactions(self):
        return self.transactions.exists()

    @property
    def is_income(self):
        return self.type == self.TYPE_INCOME

    @property
    def is_expense(self):
        return self.type == self.TYPE_EXPENSE


class Transaction(models.Model):
    """Pénzügyi tranzakció (bevétel vagy kiadás)."""

    TYPE_INCOME = Category.TYPE_INCOME
    TYPE_EXPENSE = Category.TYPE_EXPENSE
    TYPE_CHOICES = Category.TYPE_CHOICES

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name=_("tulajdonos"),
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name=_("kategória"),
    )
    type = models.CharField(_("típus"), max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(
        _("összeg (Ft)"),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    date = models.DateField(_("dátum"), default=timezone.localdate)
    description = models.CharField(_("leírás"), max_length=255, blank=True)
    created_at = models.DateTimeField(_("létrehozva"), auto_now_add=True)
    updated_at = models.DateTimeField(_("módosítva"), auto_now=True)

    class Meta:
        verbose_name = _("tranzakció")
        verbose_name_plural = _("tranzakciók")
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["owner", "-date"], name="tx_owner_date_idx"),
            models.Index(fields=["owner", "type"], name="tx_owner_type_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="transaction_amount_positive",
            )
        ]

    def __str__(self):
        return f"{self.date} – {self.category} – {self.amount} Ft"

    def clean(self):
        errors = {}

        if self.amount is not None:
            if self.amount <= 0:
                errors["amount"] = _("Az összegnek nullánál nagyobbnak kell lennie.")
            elif self.amount.as_tuple().exponent < -2:
                errors["amount"] = _("Az összeg legfeljebb két tizedesjegyet tartalmazhat.")

        if self.category_id:
            category = self.category
            if self.owner_id and category.owner_id != self.owner_id:
                errors["category"] = _("A kiválasztott kategória nem ehhez a felhasználóhoz tartozik.")
            elif self.type and category.type != self.type:
                errors["type"] = _(
                    "A tranzakció típusának meg kell egyeznie a kategória típusával."
                )

        if errors:
            raise ValidationError(errors)

        super().clean()

    def save(self, *args, **kwargs):
        # A model szintű validáció minden mentési útvonalon érvényesül
        # (űrlap, admin, kezelőparancs), így szerveroldalon is védettek vagyunk.
        if not kwargs.pop("skip_validation", False):
            self.full_clean()
        return super().save(*args, **kwargs)
