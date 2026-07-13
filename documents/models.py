from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


def document_upload_path(instance, filename):
    return f"documents/{instance.content_type.model}/{filename}"


class TypeDocument(models.TextChoices):
    PDF = "PDF", "PDF"
    IMAGE = "IMAGE", "Image scannée"
    WORD = "WORD", "Word"
    EXCEL = "EXCEL", "Excel"
    JUSTIFICATIF = "JUSTIFICATIF", "Pièce justificative"
    DEMANDE_SIGNEE = "DEMANDE_SIGNEE", "Demande signée"
    BON_COMMANDE = "BON_COMMANDE", "Bon de commande"
    CONTRAT = "CONTRAT", "Contrat"
    PV = "PV", "Procès-verbal"
    CAHIER_CHARGES = "CAHIER_CHARGES", "Cahier des charges"
    AUTRE = "AUTRE", "Autre"


class Document(models.Model):
    """Generic document attached to a Courrier, DemandeAchat or Marche."""

    fichier = models.FileField(upload_to=document_upload_path)
    nom = models.CharField(max_length=255, blank=True)
    type_document = models.CharField(max_length=20, choices=TypeDocument.choices, default=TypeDocument.AUTRE)
    description = models.TextField(blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    lie_a = GenericForeignKey("content_type", "object_id")

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="documents_uploaded"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self):
        return self.nom or self.fichier.name
