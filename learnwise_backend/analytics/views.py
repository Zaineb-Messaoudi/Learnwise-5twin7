from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def api_root(request):
    return Response({
        'overview': request.build_absolute_uri('overview/'),
        'reports': request.build_absolute_uri('reports/'),
    })