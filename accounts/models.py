from django.contrib.auth.models import AbstractUser
from django.db import models

from core.models import Service


class Role(models.TextChoices):
    ADMINISTRATEUR = "ADMIN", "Administrateur"
    AGENT_BUREAU_ORDRE = "AGENT_BO", "Agent bureau d'ordre"
    CHEF_SERVICE = "CHEF_SERVICE", "Chef de service"
    DIRECTEUR = "DIRECTEUR", "Directeur"
    SERVICE_ACHAT = "SERVICE_ACHAT", "Service achat"
    SERVICE_FINANCIER = "SERVICE_FINANCIER", "Service financier"
    AUDIT = "AUDIT", "Consultation / audit"


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.AGENT_BUREAU_ORDRE)
    service = models.ForeignKey(
        Service, on_delete=models.SET_NULL, null=True, blank=True, related_name="agents"
    )
    telephone = models.CharField(max_length=30, blank=True)
    fonction = models.CharField(max_length=150, blank=True)

    def has_role(self, *roles):
        return self.role in roles

    def __str__(self):
        return self.get_full_name() or self.username
