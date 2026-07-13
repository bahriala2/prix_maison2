import re

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Q
from django.utils import timezone

from achats.models import DemandeAchat
from core.models import STOPWORDS, Service
from documents.models import Document


class StatutMarche(models.TextChoices):
    PREPARATION = "PREPARATION", "Préparation"
    CONSULTATION_LANCEE = "CONSULTATION_LANCEE", "Consultation lancée"
    OFFRES_RECUES = "OFFRES_RECUES", "Offres reçues"
    ANALYSE_OFFRES = "ANALYSE_OFFRES", "Analyse des offres"
    ATTRIBUE = "ATTRIBUE", "Attribué"
    NOTIFIE = "NOTIFIE", "Notifié"
    EN_COURS_EXECUTION = "EN_COURS_EXECUTION", "En cours d'exécution"
    CLOTURE = "CLOTURE", "Clôturé"
    ANNULE = "ANNULE", "Annulé"


class TypeProcedure(models.TextChoices):
    APPEL_OFFRES_OUVERT = "AOO", "Appel d'offres ouvert"
    APPEL_OFFRES_RESTREINT = "AOR", "Appel d'offres restreint"
    CONSULTATION = "CONSULTATION", "Consultation"
    GRE_A_GRE = "GRE_A_GRE", "Marché de gré à gré"
    BON_COMMANDE = "BON_COMMANDE", "Bon de commande"


class Marche(models.Model):
    reference = models.CharField(max_length=30, unique=True, editable=False)
    objet = models.CharField(max_length=255)
    type_procedure = models.CharField(max_length=20, choices=TypeProcedure.choices, default=TypeProcedure.CONSULTATION)
    service_demandeur = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="marches")
    demande_achat = models.ForeignKey(
        DemandeAchat, on_delete=models.SET_NULL, null=True, blank=True, related_name="marches"
    )
    fournisseur = models.CharField(max_length=255, blank=True)
    montant = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)

    date_lancement = models.DateField(null=True, blank=True)
    date_attribution = models.DateField(null=True, blank=True)
    date_notification = models.DateField(null=True, blank=True)
    date_cloture = models.DateField(null=True, blank=True)

    statut = models.CharField(max_length=25, choices=StatutMarche.choices, default=StatutMarche.PREPARATION)

    documents = GenericRelation(Document, related_query_name="marche")

    # Marchés explicitement liés entre eux (ex : reconduction, lot complémentaire)
    marches_lies = models.ManyToManyField("self", blank=True, symmetrical=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="marches_crees"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Marché"
        verbose_name_plural = "Marchés"

    def __str__(self):
        return f"{self.reference} - {self.objet}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_reference()
        super().save(*args, **kwargs)

    def _generate_reference(self):
        year = timezone.localdate().year
        count = Marche.objects.filter(created_at__year=year).count()
        return f"MAR-{year}-{count + 1:05d}"

    def marches_similaires(self, limit=10):
        """Marchés partageant le même thème (mots significatifs de l'objet) ou
        le même fournisseur — suggérés dans la page de détail."""
        mots = [
            m.lower() for m in re.split(r"\W+", self.objet)
            if len(m) >= 4 and m.lower() not in STOPWORDS
        ]
        q = Q()
        for mot in mots[:10]:
            q |= Q(objet__icontains=mot)
        if self.fournisseur:
            q |= Q(fournisseur__iexact=self.fournisseur)
        if not q:
            return Marche.objects.none()
        return (
            Marche.objects.filter(q)
            .exclude(pk=self.pk)
            .exclude(pk__in=self.marches_lies.values_list("pk", flat=True))
            .distinct()
            .order_by("-created_at")[:limit]
        )
