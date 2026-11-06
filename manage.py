#!/usr/bin/env python
"""Django parancssori segédprogram."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "homefinance.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Nem sikerült importálni a Django-t. Telepítve van és elérhető a "
            "PYTHONPATH-on? Szükség van egy virtuális környezetre?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
