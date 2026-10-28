"""Lecture de la configuration (variables d'environnement ou settings Django)."""
import os
from pathlib import Path

from django.conf import settings

try:
    from dotenv import load_dotenv

    # Le fichier .env se trouve a cote de manage.py (BASE_DIR).
    load_dotenv(Path(settings.BASE_DIR) / '.env')
except Exception:  # python-dotenv absent ou BASE_DIR non defini : on ignore
    pass


def get_setting(name, default=''):
    """Cherche d'abord dans l'environnement (.env), puis dans settings.py."""
    return os.environ.get(name) or getattr(settings, name, None) or default
