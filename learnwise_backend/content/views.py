from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def api_root(request):
    return Response({
        'courses': request.build_absolute_uri('courses/'),
        'materials': request.build_absolute_uri('materials/'),
    })