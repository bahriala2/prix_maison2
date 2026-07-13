from django.contrib import admin

from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "role", "contenu", "created_at")
    list_filter = ("role", "utilisateur")
    search_fields = ("contenu",)
