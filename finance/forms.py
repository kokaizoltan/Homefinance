"""Űrlapok és szerveroldali validáció."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, BaseUserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Category, Transaction, User


class BootstrapFormMixin:
    """Egységes Bootstrap stílusok az űrlapmezőkön."""

    def _apply_bootstrap_classes(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css_class = "form-select"
            else:
                css_class = "form-control"
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css_class}".strip()


class RegisterForm(BootstrapFormMixin, BaseUserCreationForm):
    """Regisztrációs űrlap e-mail-címmel."""

    class Meta:
        model = User
        fields = ("email", "last_name", "first_name")
        labels = {
            "email": _("E-mail cím"),
            "last_name": _("Vezetéknév"),
            "first_name": _("Keresztnév"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update(
            {"autocomplete": "email", "placeholder": "pelda@email.hu"}
        )
        self.fields["last_name"].required = False
        self.fields["first_name"].required = False
        self.fields["password1"].label = _("Jelszó")
        self.fields["password2"].label = _("Jelszó megerősítése")
        self._apply_bootstrap_classes()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("Ezzel az e-mail-címmel már létezik felhasználó."))
        return email


class EmailAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    """Bejelentkezés e-mail-címmel."""

    username = forms.EmailField(
        label=_("E-mail cím"),
        widget=forms.EmailInput(
            attrs={"autofocus": True, "autocomplete": "email", "placeholder": "pelda@email.hu"}
        ),
    )
    password = forms.CharField(
        label=_("Jelszó"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = _("E-mail cím")
        self._apply_bootstrap_classes()

    def clean_username(self):
        return (self.cleaned_data.get("username") or "").strip().lower()


class CategoryForm(BootstrapFormMixin, forms.ModelForm):
    """Kategória létrehozása és szerkesztése."""

    class Meta:
        model = Category
        fields = ("name", "type")
        labels = {
            "name": _("Kategória neve"),
            "type": _("Típus"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "pl. Élelmiszer"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None and not self.instance.owner_id:
            self.instance.owner = user
        self._apply_bootstrap_classes()

    def clean(self):
        cleaned_data = super().clean()
        name = (cleaned_data.get("name") or "").strip()
        type_ = cleaned_data.get("type")

        if self.user and name and type_:
            # Az SQLite/PostgreSQL alapú iexact nem kezeli megbízhatóan a magyar
            # ékezetes karakterek kis- és nagybetűjét, ezért Python-oldalon
            # hasonlítunk össze casefold-dal.
            existing_names = Category.objects.filter(
                owner=self.user, type=type_
            ).values_list("pk", "name")
            for pk, existing_name in existing_names:
                if self.instance.pk and pk == self.instance.pk:
                    continue
                if existing_name.strip().casefold() == name.casefold():
                    raise ValidationError(
                        {"name": _("Már létezik ilyen nevű kategória ebben a típusban.")}
                    )

        if name:
            cleaned_data["name"] = name
        return cleaned_data


class TransactionForm(BootstrapFormMixin, forms.ModelForm):
    """Tranzakció létrehozása és szerkesztése."""

    class Meta:
        model = Transaction
        fields = ("type", "category", "amount", "date", "description")
        labels = {
            "type": _("Típus"),
            "category": _("Kategória"),
            "amount": _("Összeg (Ft)"),
            "date": _("Dátum"),
            "description": _("Leírás"),
        }
        widgets = {
            "date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "amount": forms.NumberInput(
                attrs={"step": "0.01", "min": "0.01", "placeholder": "0,00"}
            ),
            "description": forms.TextInput(attrs={"placeholder": "pl. heti bevásárlás"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["date"].input_formats = ["%Y-%m-%d"]
        if user is not None:
            self.fields["category"].queryset = Category.objects.filter(
                owner=user
            ).order_by("type", "name")
            if not self.instance.owner_id:
                self.instance.owner = user
        self.fields["category"].empty_label = _("Válassz kategóriát")
        self._apply_bootstrap_classes()

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        type_ = cleaned_data.get("type")

        if category and self.user and category.owner_id != self.user.pk:
            self.add_error(
                "category", _("A kiválasztott kategória nem ehhez a felhasználóhoz tartozik.")
            )
        elif category and type_ and category.type != type_:
            self.add_error(
                "type",
                _(
                    "A tranzakció típusának meg kell egyeznie a kiválasztott "
                    "kategória típusával."
                ),
            )
        return cleaned_data


class TransactionFilterForm(BootstrapFormMixin, forms.Form):
    """Tranzakciólista szűrője."""

    date_from = forms.DateField(
        label=_("Dátumtól"),
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        label=_("Dátumig"),
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    type = forms.ChoiceField(
        label=_("Típus"),
        required=False,
        choices=[("", _("Összes")), *Transaction.TYPE_CHOICES],
    )
    category = forms.ModelChoiceField(
        label=_("Kategória"),
        required=False,
        queryset=Category.objects.none(),
        empty_label=_("Összes"),
    )
    q = forms.CharField(
        label=_("Keresés"),
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Leírás keresése…"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["category"].queryset = Category.objects.filter(owner=user).order_by(
                "type", "name"
            )
        self.fields["date_from"].input_formats = ["%Y-%m-%d"]
        self.fields["date_to"].input_formats = ["%Y-%m-%d"]
        self._apply_bootstrap_classes()

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise ValidationError(_("A kezdődátum nem lehet későbbi a záródátumnál."))
        return cleaned_data
