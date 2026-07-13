from django.conf import settings
from django.db import models


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "Utilisateur"
        ASSISTANT = "assistant", "Assistant"

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages_chat"
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    contenu = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Message du chat"
        verbose_name_plural = "Messages du chat"

    def __str__(self):
        return f"{self.utilisateur} [{self.role}] {self.contenu[:50]}"
