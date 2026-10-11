from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def api_root(request):
    return Response({
        'chat': request.build_absolute_uri('chat/'),
        'sessions': request.build_absolute_uri('sessions/'),
    })