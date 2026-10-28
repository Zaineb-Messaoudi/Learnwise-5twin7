from django.conf import settings


class CrossOriginResourcePolicyMiddleware:
    """Add Cross-Origin-Resource-Policy: cross-origin to media responses
    so cross-origin embeds (frontend on :5173 loading images from :8000)
    are not blocked by COEP.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(settings.MEDIA_URL):
            response["Cross-Origin-Resource-Policy"] = "cross-origin"
        return response
