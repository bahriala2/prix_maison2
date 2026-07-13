from django.db import models

# Mots vides ignorés lors de la recherche de correspondances/dossiers similaires
STOPWORDS = {
    "avec", "pour", "dans", "cette", "votre", "notre", "leur", "vous", "nous",
    "demande", "objet", "concernant", "suite", "relative", "relatif", "lettre",
    "courrier", "monsieur", "madame", "sans", "sous", "entre", "ainsi",
    "achat", "marche", "marché",
}


class Service(models.Model):
    """Service / direction administrative (ex: Service Achat, Direction Générale...)."""

    nom = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "Service"
        verbose_name_plural = "Services"

    def __str__(self):
        return self.nom


class Correspondant(models.Model):
    """Émetteur ou récepteur de courrier. Liste gérée dans l'administration et
    enrichie automatiquement à chaque enregistrement de courrier ; elle
    alimente l'autocomplétion des champs émetteur / récepteur."""

    nom = models.CharField(max_length=255, unique=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "Correspondant (émetteur / récepteur)"
        verbose_name_plural = "Correspondants (émetteurs / récepteurs)"

    def __str__(self):
        return self.nom


class TimeStampedModel(models.Model):
    """Abstract base with creation/update timestamps and author tracking."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
