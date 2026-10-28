from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def api_root(request):
    return Response({
        'overview': request.build_absolute_uri('overview/'),
        'reports': request.build_absolute_uri('reports/'),
    })


@api_view(['GET'])
def student_overview(request):
    range_days = int(request.query_params.get('range', 30))
    return Response({
        'range_days': range_days,
        'total_hours': 12.4,
        'average_score': 87,
        'sessions': 8,
        'topics': [
            {'name': 'Neural Networks', 'score': 82, 'trend': 'up'},
            {'name': 'Gradient Descent', 'score': 76, 'trend': 'stable'},
            {'name': 'Backpropagation', 'score': 91, 'trend': 'up'},
        ],
        'weekly_activity': [
            {'day': 'Mon', 'hours': 1.2, 'score': 76},
            {'day': 'Tue', 'hours': 2.4, 'score': 82},
            {'day': 'Wed', 'hours': 1.8, 'score': 88},
            {'day': 'Thu', 'hours': 3.1, 'score': 91},
            {'day': 'Fri', 'hours': 2.2, 'score': 87},
            {'day': 'Sat', 'hours': 1.4, 'score': 94},
            {'day': 'Sun', 'hours': 2.8, 'score': 90},
        ],
    })