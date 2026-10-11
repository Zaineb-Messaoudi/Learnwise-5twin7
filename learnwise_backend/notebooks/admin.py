from django.contrib import admin
from .models import Notebook, NotebookEntry

@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'course', 'created_at', 'updated_at']
    list_filter = ['course', 'created_at']
    search_fields = ['title', 'user__email', 'user__username']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(NotebookEntry)
class NotebookEntryAdmin(admin.ModelAdmin):
    list_display = ['title', 'notebook', 'entry_type', 'position', 'created_at']
    list_filter = ['entry_type', 'created_at']
    search_fields = ['title', 'notebook__title']
    readonly_fields = ['created_at', 'updated_at']