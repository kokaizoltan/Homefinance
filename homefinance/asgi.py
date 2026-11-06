"""ASGI belépési pont a homefinance projekthez."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "homefinance.settings")

application = get_asgi_application()
