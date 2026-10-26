from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Notebook, NotebookEntry
from accounts.permissions import IsOnboarded
from .serializers import NotebookSerializer, NotebookCreateSerializer, NotebookEntrySerializer, NotebookEntryCreateSerializer


class NotebookViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOnboarded]

    def get_queryset(self):
        return Notebook.objects.filter(user=self.request.user).prefetch_related('entries')

    def get_serializer_class(self):
        if self.action == 'create':
            return NotebookCreateSerializer
        return NotebookSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get', 'post'])
    def entries(self, request, pk=None):
        notebook = self.get_object()
        if request.method == 'GET':
            entries = notebook.entries.all()
            return Response(NotebookEntrySerializer(entries, many=True).data)
        else:
            serializer = NotebookEntryCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(notebook=notebook)
            return Response(NotebookEntrySerializer(serializer.instance).data, status=201)


class NotebookEntryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOnboarded]
    serializer_class = NotebookEntrySerializer

    def get_queryset(self):
        return NotebookEntry.objects.filter(notebook__user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return NotebookEntryCreateSerializer
        return NotebookEntrySerializer