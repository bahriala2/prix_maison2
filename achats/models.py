import re

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models import STOPWORDS, Service
from documents.models import Document


class TypeAchat(models.TextChoices):
    FOURNITURES = "FOURNITURES", "Fournitures"
    PRESTATIONS = "PRESTATIONS", "Prestations de service"
    TRAVAUX = "TRAVAUX", "Travaux"
    MATERIEL_INFORMATIQUE = "MATERIEL_INFORMATIQUE", "Matériel informatique"
    MAINTENANCE = "MAINTENANCE", "Maintenance"
    AUTRE = "AUTRE", "Autre"


class CircuitDemande(models.TextChoices):
    AVEC_ACCORDS = "AVEC_ACCORDS", "Avec accords (DCP et autres directions)"
    LOCALE = "LOCALE", "Locale — signature du directeur uniquement"


class StatutDemande(models.TextChoices):
    BROUILLON = "BROUILLON", "Brouillon"
    SOUMISE = "SOUMISE", "Soumise"
    VALIDEE_CHEF_SERVICE = "VALIDEE_CHEF_SERVICE", "Validée par chef de service"
    EN_ATTENTE_ACCORDS = "EN_ATTENTE_ACCORDS", "En attente des accords (DCP / directions)"
    ACCORDS_OBTENUS = "ACCORDS_OBTENUS", "Accords obtenus"
    SOUMISE_DIRECTEUR = "SOUMISE_DIRECTEUR", "Soumise au directeur"
    SIGNEE_DIRECTEUR = "SIGNEE_DIRECTEUR", "Signée par directeur"
    RECUE_BUREAU_ORDRE = "RECUE_BUREAU_ORDRE", "Reçue par le bureau d'ordre"
    ENREGISTREE = "ENREGISTREE", "Enregistrée"
    TRANSMISE_SERVICE_ACHAT = "TRANSMISE_SERVICE_ACHAT", "Transmise au service achat"
    EN_COURS_TRAITEMENT = "EN_COURS_TRAITEMENT", "En cours de traitement"
    BON_COMMANDE_PREPARE = "BON_COMMANDE_PREPARE", "Bon de commande préparé"
    MARCHE_LANCE = "MARCHE_LANCE", "Marché lancé"
    CLOTUREE = "CLOTUREE", "Clôturée"
    REJETEE = "REJETEE", "Rejetée"


# Ordered workflows per circuit, used to drive the "next status" suggestion
# in the UI. Le circuit AVEC_ACCORDS passe par les accords de la DCP et des
# autres directions avant la signature du directeur ; le circuit LOCALE va
# directement du chef de service au directeur.
WORKFLOW_AVEC_ACCORDS = [
    StatutDemande.BROUILLON,
    StatutDemande.SOUMISE,
    StatutDemande.VALIDEE_CHEF_SERVICE,
    StatutDemande.EN_ATTENTE_ACCORDS,
    StatutDemande.ACCORDS_OBTENUS,
    StatutDemande.SOUMISE_DIRECTEUR,
    StatutDemande.SIGNEE_DIRECTEUR,
    StatutDemande.RECUE_BUREAU_ORDRE,
    StatutDemande.ENREGISTREE,
    StatutDemande.TRANSMISE_SERVICE_ACHAT,
    StatutDemande.EN_COURS_TRAITEMENT,
    StatutDemande.BON_COMMANDE_PREPARE,
    StatutDemande.MARCHE_LANCE,
    StatutDemande.CLOTUREE,
]

WORKFLOW_LOCALE = [
    StatutDemande.BROUILLON,
    StatutDemande.SOUMISE,
    StatutDemande.VALIDEE_CHEF_SERVICE,
    StatutDemande.SOUMISE_DIRECTEUR,
    StatutDemande.SIGNEE_DIRECTEUR,
    StatutDemande.RECUE_BUREAU_ORDRE,
    StatutDemande.ENREGISTREE,
    StatutDemande.TRANSMISE_SERVICE_ACHAT,
    StatutDemande.EN_COURS_TRAITEMENT,
    StatutDemande.BON_COMMANDE_PREPARE,
    StatutDemande.MARCHE_LANCE,
    StatutDemande.CLOTUREE,
]

# Statuses at/after which the request is considered "signed by the director"
# and therefore visible in the bureau d'ordre follow-up queue (section 7).
SIGNEE_OU_APRES = {
    StatutDemande.SIGNEE_DIRECTEUR,
    StatutDemande.RECUE_BUREAU_ORDRE,
    StatutDemande.ENREGISTREE,
    StatutDemande.TRANSMISE_SERVICE_ACHAT,
    StatutDemande.EN_COURS_TRAITEMENT,
    StatutDemande.BON_COMMANDE_PREPARE,
    StatutDemande.MARCHE_LANCE,
    StatutDemande.CLOTUREE,
}


class DemandeAchat(models.Model):
    reference = models.CharField(max_length=30, unique=True, editable=False)
    circuit = models.CharField(
        max_length=15,
        choices=CircuitDemande.choices,
        default=CircuitDemande.LOCALE,
        help_text="Circuit de validation : avec accords (DCP et autres directions) ou local (signature du directeur uniquement)",
    )
    service_demandeur = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="demandes_achat")
    objet = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    montant_estimatif = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    type_achat = models.CharField(max_length=25, choices=TypeAchat.choices, default=TypeAchat.AUTRE)
    date_creation = models.DateField(default=timezone.localdate)

    avis_chef_service = models.TextField(blank=True)
    decision_directeur = models.TextField(blank=True)
    date_signature_directeur = models.DateField(null=True, blank=True)

    statut = models.CharField(max_length=30, choices=StatutDemande.choices, default=StatutDemande.BROUILLON)

    numero_ordre_bo = models.CharField(max_length=30, blank=True, help_text="Numéro d'ordre attribué au bureau d'ordre")
    date_enregistrement_bo = models.DateField(null=True, blank=True)

    documents = GenericRelation(Document, related_query_name="demande_achat")

    # Demandes explicitement liées entre elles (ex : renouvellement, complément)
    demandes_liees = models.ManyToManyField("self", blank=True, symmetrical=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="demandes_creees"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Demande d'achat"
        verbose_name_plural = "Demandes d'achat"

    def __str__(self):
        return f"{self.reference} - {self.objet}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_reference()
        super().save(*args, **kwargs)

    def _generate_reference(self):
        year = timezone.localdate().year
        count = DemandeAchat.objects.filter(date_creation__year=year).count()
        return f"DA-{year}-{count + 1:05d}"

    @property
    def est_signee_par_directeur(self):
        return self.statut in SIGNEE_OU_APRES

    @property
    def workflow(self):
        if self.circuit == CircuitDemande.AVEC_ACCORDS:
            return WORKFLOW_AVEC_ACCORDS
        return WORKFLOW_LOCALE

    def demandes_similaires(self, limit=10):
        """Demandes partageant le même thème (mots significatifs de l'objet ou
        de la description) ou le même service — suggérées dans le détail."""
        mots = [
            m.lower() for m in re.split(r"\W+", f"{self.objet} {self.description}")
            if len(m) >= 4 and m.lower() not in STOPWORDS
        ]
        q = Q()
        for mot in mots[:10]:
            q |= Q(objet__icontains=mot) | Q(description__icontains=mot)
        if not q:
            return DemandeAchat.objects.none()
        return (
            DemandeAchat.objects.filter(q)
            .exclude(pk=self.pk)
            .exclude(pk__in=self.demandes_liees.values_list("pk", flat=True))
            .distinct()
            .order_by("-created_at")[:limit]
        )

    def enregistrer_au_bureau_ordre(self):
        """Attribue un numéro d'ordre au bureau d'ordre pour une demande signée (section 7)."""
        if not self.numero_ordre_bo:
            year = timezone.localdate().year
            count = DemandeAchat.objects.exclude(numero_ordre_bo="").filter(
                date_enregistrement_bo__year=year
            ).count()
            self.numero_ordre_bo = f"BO-DA-{year}-{count + 1:05d}"
        self.date_enregistrement_bo = timezone.localdate()
        self.statut = StatutDemande.ENREGISTREE
        self.save()


class Approbation(models.Model):
    class Decision(models.TextChoices):
        APPROUVE = "APPROUVE", "Approuvé"
        REJETE = "REJETE", "Rejeté"
        A_COMPLETER = "A_COMPLETER", "À compléter"
        EN_ATTENTE = "EN_ATTENTE", "En attente"

    demande = models.ForeignKey(DemandeAchat, on_delete=models.CASCADE, related_name="approbations")
    valideur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    fonction = models.CharField(max_length=150, blank=True)
    date_validation = models.DateTimeField(auto_now_add=True)
    decision = models.CharField(max_length=15, choices=Decision.choices, default=Decision.EN_ATTENTE)
    commentaire = models.TextField(blank=True)

    class Meta:
        ordering = ["-date_validation"]
        verbose_name = "Approbation"
        verbose_name_plural = "Approbations"

    def __str__(self):
        return f"{self.demande.reference} - {self.get_decision_display()} par {self.valideur}"
