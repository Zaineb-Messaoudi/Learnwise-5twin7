from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def api_root(request):
    return Response({
        'quizzes': request.build_absolute_uri('quizzes/'),
        'exercises': request.build_absolute_uri('exercises/'),
    })