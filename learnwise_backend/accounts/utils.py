"""Small helpers shared by the accounts models, serializers and views.

NOTE: keep this module free of imports that pull in ``rest_framework.views``
(see the note at the top of authentication.py about circular imports).
"""
import ipaddress
import re
import secrets

from django.contrib.auth import get_user_model
from rest_framework.settings import api_settings


def _valid_ip(value):
    try:
        return str(ipaddress.ip_address((value or '').strip()))
    except ValueError:
        return None


def client_ip(request):
    """Best-effort client IP address.

    ``X-Forwarded-For`` is only trusted when ``NUM_PROXIES`` is configured (the
    same rule DRF's throttling uses), otherwise ``REMOTE_ADDR`` is returned so a
    client can never spoof its address in the security log.
    """
    remote = _valid_ip(request.META.get('REMOTE_ADDR'))
    num_proxies = api_settings.NUM_PROXIES
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if num_proxies and forwarded:
        addrs = [a.strip() for a in forwarded.split(',') if a.strip()]
        if addrs:
            candidate = _valid_ip(addrs[-min(int(num_proxies), len(addrs))])
            if candidate:
                return candidate
    return remote


def unique_username(email):
    """Derive a unique, valid username from an email address."""
    User = get_user_model()
    base = re.sub(r'[^\w.@+-]', '', (email or '').split('@')[0])[:100] or 'user'
    candidate = base
    while User.objects.filter(username__iexact=candidate).exists():
        candidate = f'{base}{secrets.token_hex(2)}'
    return candidate
