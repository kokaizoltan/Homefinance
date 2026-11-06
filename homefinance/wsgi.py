"""WSGI belépési pont a homefinance projekthez."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "homefinance.settings")

application = get_wsgi_application()
