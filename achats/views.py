from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Role

from .forms import ApprobationForm, DemandeAchatForm
from .models import Approbation, CircuitDemande, DemandeAchat, StatutDemande

# action -> (target status, roles allowed, message)
ACTIONS = {
    "soumettre": (StatutDemande.SOUMISE, {Role.AGENT_BUREAU_ORDRE, Role.CHEF_SERVICE, Role.ADMINISTRATEUR}, "Demande soumise."),
    "valider_chef_service": (StatutDemande.VALIDEE_CHEF_SERVICE, {Role.CHEF_SERVICE, Role.ADMINISTRATEUR}, "Demande validée par le chef de service."),
    "demander_accords": (StatutDemande.EN_ATTENTE_ACCORDS, {Role.CHEF_SERVICE, Role.AGENT_BUREAU_ORDRE, Role.ADMINISTRATEUR}, "Demande transmise pour accords (DCP et directions concernées)."),
    "confirmer_accords": (StatutDemande.ACCORDS_OBTENUS, {Role.CHEF_SERVICE, Role.AGENT_BUREAU_ORDRE, Role.ADMINISTRATEUR}, "Accords obtenus."),
    "soumettre_directeur": (StatutDemande.SOUMISE_DIRECTEUR, {Role.CHEF_SERVICE, Role.ADMINISTRATEUR}, "Demande soumise au directeur."),
    "signer_directeur": (StatutDemande.SIGNEE_DIRECTEUR, {Role.DIRECTEUR, Role.ADMINISTRATEUR}, "Demande signée par le directeur."),
    "recevoir_bureau_ordre": (StatutDemande.RECUE_BUREAU_ORDRE, {Role.AGENT_BUREAU_ORDRE, Role.ADMINISTRATEUR}, "Demande reçue par le bureau d'ordre."),
    "transmettre_service_achat": (StatutDemande.TRANSMISE_SERVICE_ACHAT, {Role.AGENT_BUREAU_ORDRE, Role.ADMINISTRATEUR}, "Demande transmise au service achat."),
    "traiter": (StatutDemande.EN_COURS_TRAITEMENT, {Role.SERVICE_ACHAT, Role.ADMINISTRATEUR}, "Demande en cours de traitement."),
    "preparer_bon_commande": (StatutDemande.BON_COMMANDE_PREPARE, {Role.SERVICE_ACHAT, Role.ADMINISTRATEUR}, "Bon de commande préparé."),
    "lancer_marche": (StatutDemande.MARCHE_LANCE, {Role.SERVICE_ACHAT, Role.ADMINISTRATEUR}, "Marché lancé."),
    "cloturer": (StatutDemande.CLOTUREE, {Role.SERVICE_ACHAT, Role.AGENT_BUREAU_ORDRE, Role.ADMINISTRATEUR}, "Demande clôturée."),
    "rejeter": (StatutDemande.REJETEE, {Role.CHEF_SERVICE, Role.DIRECTEUR, Role.ADMINISTRATEUR}, "Demande rejetée."),
}

# statut courant -> actions possibles, selon le circuit de la demande.
# Circuit AVEC_ACCORDS : le chef de service demande d'abord les accords de la
# DCP et des autres directions ; circuit LOCALE : passage direct au directeur.
NEXT_ACTIONS_COMMUN = {
    StatutDemande.BROUILLON: ["soumettre"],
    StatutDemande.SOUMISE: ["valider_chef_service", "rejeter"],
    StatutDemande.SOUMISE_DIRECTEUR: ["signer_directeur", "rejeter"],
    StatutDemande.SIGNEE_DIRECTEUR: ["recevoir_bureau_ordre"],
    StatutDemande.RECUE_BUREAU_ORDRE: ["enregistrer_bureau_ordre"],
    StatutDemande.ENREGISTREE: ["transmettre_service_achat"],
    StatutDemande.TRANSMISE_SERVICE_ACHAT: ["traiter"],
    StatutDemande.EN_COURS_TRAITEMENT: ["preparer_bon_commande", "lancer_marche"],
    StatutDemande.BON_COMMANDE_PREPARE: ["cloturer"],
    StatutDemande.MARCHE_LANCE: ["cloturer"],
}

NEXT_ACTIONS_PAR_CIRCUIT = {
    CircuitDemande.AVEC_ACCORDS: {
        **NEXT_ACTIONS_COMMUN,
        StatutDemande.VALIDEE_CHEF_SERVICE: ["demander_accords", "rejeter"],
        StatutDemande.EN_ATTENTE_ACCORDS: ["confirmer_accords", "rejeter"],
        StatutDemande.ACCORDS_OBTENUS: ["soumettre_directeur", "rejeter"],
    },
    CircuitDemande.LOCALE: {
        **NEXT_ACTIONS_COMMUN,
        StatutDemande.VALIDEE_CHEF_SERVICE: ["soumettre_directeur", "rejeter"],
    },
}

ACTION_LABELS = {
    "soumettre": "Soumettre",
    "valider_chef_service": "Valider (chef de service)",
    "demander_accords": "Demander les accords (DCP / directions)",
    "confirmer_accords": "Confirmer les accords obtenus",
    "soumettre_directeur": "Soumettre au directeur",
    "signer_directeur": "Signer (directeur)",
    "recevoir_bureau_ordre": "Marquer reçue au bureau d'ordre",
    "enregistrer_bureau_ordre": "Enregistrer au bureau d'ordre",
    "transmettre_service_achat": "Transmettre au service achat",
    "traiter": "Marquer en cours de traitement",
    "preparer_bon_commande": "Bon de commande préparé",
    "lancer_marche": "Marché lancé",
    "cloturer": "Clôturer",
    "rejeter": "Rejeter",
}


# Filtres par colonne de la liste des demandes : paramètre GET -> filtre ORM
DEMANDE_COLUMN_FILTERS = {
    "reference": "reference__icontains",
    "objet": "objet__icontains",
    "circuit": "circuit",
    "service": "service_demandeur__nom__icontains",
    "type_achat": "type_achat",
    "statut": "statut",
    "numero_bo": "numero_ordre_bo__icontains",
}


@login_required
def demande_list(request):
    from .models import TypeAchat

    demandes = DemandeAchat.objects.select_related("service_demandeur").all()
    filtres = {}
    for param, lookup in DEMANDE_COLUMN_FILTERS.items():
        valeur = request.GET.get(param, "").strip()
        if valeur:
            demandes = demandes.filter(**{lookup: valeur})
            filtres[param] = valeur

    return render(
        request,
        "achats/demande_list.html",
        {
            "demandes": demandes,
            "filtres": filtres,
            "statuts": StatutDemande.choices,
            "circuits": CircuitDemande.choices,
            "types_achat": TypeAchat.choices,
        },
    )


@login_required
def demandes_signees_bo(request):
    """Espace bureau d'ordre : demandes signées par le directeur, en attente d'enregistrement/transmission."""
    demandes = DemandeAchat.objects.filter(statut=StatutDemande.SIGNEE_DIRECTEUR).select_related("service_demandeur")
    return render(request, "achats/demandes_signees_bo.html", {"demandes": demandes})


@login_required
def demande_create(request):
    if request.method == "POST":
        form = DemandeAchatForm(request.POST)
        if form.is_valid():
            demande = form.save(commit=False)
            demande.created_by = request.user
            demande.save()
            messages.success(request, f"Demande {demande.reference} créée.")
            return redirect("achats:detail", pk=demande.pk)
    else:
        form = DemandeAchatForm()
    return render(request, "achats/demande_form.html", {"form": form})


@login_required
def demande_detail(request, pk):
    demande = get_object_or_404(DemandeAchat.objects.select_related("service_demandeur"), pk=pk)
    approbation_form = ApprobationForm()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "approbation":
            approbation_form = ApprobationForm(request.POST)
            if approbation_form.is_valid():
                approbation = approbation_form.save(commit=False)
                approbation.demande = demande
                approbation.valideur = request.user
                approbation.save()
                messages.success(request, "Approbation enregistrée.")
                return redirect("achats:detail", pk=demande.pk)

        elif action == "lier":
            cible = DemandeAchat.objects.filter(pk=request.POST.get("demande_cible")).first()
            if cible and cible.pk != demande.pk:
                demande.demandes_liees.add(cible)
                messages.success(request, f"Demande {cible.reference} liée.")
            return redirect("achats:detail", pk=demande.pk)

        elif action == "delier":
            cible = DemandeAchat.objects.filter(pk=request.POST.get("demande_cible")).first()
            if cible:
                demande.demandes_liees.remove(cible)
                messages.success(request, f"Liaison avec {cible.reference} supprimée.")
            return redirect("achats:detail", pk=demande.pk)

        elif action == "changer_statut":
            # Changement manuel : le workflow guidé reste proposé, mais le
            # statut est librement ajustable selon les besoins et le secteur
            # d'activité de l'administration (tous rôles sauf consultation/audit).
            if request.user.role == Role.AUDIT:
                messages.error(request, "Le rôle consultation/audit ne peut pas modifier les statuts.")
            else:
                nouveau = request.POST.get("nouveau_statut")
                if nouveau in StatutDemande.values:
                    demande.statut = nouveau
                    if nouveau == StatutDemande.SIGNEE_DIRECTEUR and not demande.date_signature_directeur:
                        demande.date_signature_directeur = timezone.localdate()
                    demande.save()
                    messages.success(request, f"Statut changé : {demande.get_statut_display()}.")
                else:
                    messages.error(request, "Statut invalide.")
            return redirect("achats:detail", pk=demande.pk)

        elif action == "enregistrer_bureau_ordre":
            if request.user.role in {Role.AGENT_BUREAU_ORDRE, Role.ADMINISTRATEUR}:
                demande.enregistrer_au_bureau_ordre()
                messages.success(request, f"Demande enregistrée au bureau d'ordre sous le n° {demande.numero_ordre_bo}.")
            else:
                messages.error(request, "Vous n'avez pas les droits pour effectuer cette action.")
            return redirect("achats:detail", pk=demande.pk)

        elif action in ACTIONS:
            target_status, roles, msg = ACTIONS[action]
            if request.user.role not in roles:
                messages.error(request, "Vous n'avez pas les droits pour effectuer cette action.")
            else:
                demande.statut = target_status
                if action == "signer_directeur":
                    demande.date_signature_directeur = timezone.localdate()
                    demande.decision_directeur = request.POST.get("decision_directeur", demande.decision_directeur)
                demande.save()
                messages.success(request, msg)
            return redirect("achats:detail", pk=demande.pk)

    actions_du_circuit = NEXT_ACTIONS_PAR_CIRCUIT.get(demande.circuit, NEXT_ACTIONS_PAR_CIRCUIT[CircuitDemande.LOCALE])
    next_actions = [
        (code, ACTION_LABELS[code]) for code in actions_du_circuit.get(demande.statut, [])
    ]

    return render(
        request,
        "achats/demande_detail.html",
        {
            "demande": demande,
            "approbation_form": approbation_form,
            "approbations": demande.approbations.select_related("valideur"),
            "documents": demande.documents.all(),
            "next_actions": next_actions,
            "tous_statuts": StatutDemande.choices,
            "demandes_liees": demande.demandes_liees.all(),
            "similaires": demande.demandes_similaires(),
        },
    )
