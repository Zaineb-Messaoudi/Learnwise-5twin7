from rest_framework.views import exception_handler as drf_exception_handler


def api_exception_handler(exc, context):
    """DRF's default handler, plus a machine-readable ``code`` next to ``detail``.

    The frontend uses it to react to specific situations (for example
    ``onboarding_required`` or ``session_revoked``) without parsing messages.
    """
    response = drf_exception_handler(exc, context)
    if response is not None and isinstance(response.data, dict) and 'code' not in response.data:
        code = getattr(response.data.get('detail'), 'code', None)
        if code:
            response.data['code'] = code
    return response
