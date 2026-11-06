"""Közös teszt segédfüggvények."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from finance.models import Category, Transaction

User = get_user_model()


def create_user(email="user@example.com", password="Teszt12345!", **kwargs):
    return User.objects.create_user(email=email, password=password, **kwargs)


def create_category(user, name="Élelmiszer", category_type=Category.TYPE_EXPENSE):
    return Category.objects.create(owner=user, name=name, type=category_type)


def create_transaction(user, category=None, **kwargs):
    if category is None:
        category = create_category(user)
    data = {
        "owner": user,
        "category": category,
        "type": category.type,
        "amount": Decimal("1000.00"),
        "date": date.today(),
        "description": "",
    }
    data.update(kwargs)
    return Transaction.objects.create(**data)
