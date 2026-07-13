from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("nom", "type_document", "content_type", "object_id", "uploaded_by", "uploaded_at")
    list_filter = ("type_document", "content_type")
    search_fields = ("nom", "description")
