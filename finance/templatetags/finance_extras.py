"""Egyedi sablon szűrők és tagek."""
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def huf(value):
    """Összeg formázása magyar stílusban: 1 234 567 Ft / 1 234,50 Ft."""
    if value is None or value == "":
        return "0 Ft"
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return "0 Ft"

    if amount == amount.to_integral_value():
        formatted = f"{amount:,.0f}"
    else:
        formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")

    formatted = formatted.replace(",", "\u00a0")
    return f"{formatted} Ft"


@register.filter
def percent(value):
    """Százalék formázása magyar stílusban."""
    if value is None:
        return "0%"
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return "0%"
    formatted = f"{number:.1f}".replace(".", ",")
    if formatted.endswith(",0"):
        formatted = formatted[:-2]
    return f"{formatted}%"


@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    """Az aktuális query string módosítása (pl. lapozáshoz)."""
    request = context.get("request")
    if request is None:
        return ""
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()
