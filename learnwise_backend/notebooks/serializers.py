from rest_framework import serializers
from .models import Notebook, NotebookEntry


class NotebookEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = NotebookEntry
        fields = ['id', 'entry_type', 'title', 'content', 'source_material_id', 'position', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotebookSerializer(serializers.ModelSerializer):
    entries = NotebookEntrySerializer(many=True, read_only=True)
    entries_count = serializers.IntegerField(source='entries.count', read_only=True)

    class Meta:
        model = Notebook
        fields = ['id', 'title', 'description', 'course', 'entries', 'entries_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotebookCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notebook
        fields = ['title', 'description', 'course']


class NotebookEntryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotebookEntry
        fields = ['entry_type', 'title', 'content', 'source_material_id', 'position']