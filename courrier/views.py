import tempfile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Correspondant, Service
from documents.models import Document, TypeDocument
from documents.services.ocr import analyze_document

from .forms import CourrierForm, ScanUploadForm, StatutChangeForm
from .models import Courrier, StatutCourrier, TypeCourrier

# Filtres par colonne : paramètre GET -> filtre ORM
COLUMN_FILTERS = {
    "numero": "numero_ordre__icontains",
    "objet": "objet__icontains",
    "emetteur": "emetteur__icontains",
    "recepteur": "recepteur__icontains",
    "reference": "reference_externe__icontains",
    "service": "service__nom__icontains",
    "statut": "statut",
    "date": "date_courrier",
}


def _liste_courriers(request, type_courrier):
    courriers = Courrier.objects.select_related("service").filter(type_courrier=type_courrier)

    filtres = {}
    for param, lookup in COLUMN_FILTERS.items():
        valeur = request.GET.get(param, "").strip()
        if valeur:
            courriers = courriers.filter(**{lookup: valeur})
            filtres[param] = valeur

    est_entrant = type_courrier == TypeCourrier.ENTRANT
    return render(
        request,
        "courrier/courrier_list.html",
        {
            "courriers": courriers,
            "filtres": filtres,
            "type_courrier": type_courrier,
            "est_entrant": est_entrant,
            "titre": "Courriers entrants" if est_entrant else "Courriers sortants",
            "statuts": StatutCourrier.choices,
        },
    )


@login_required
def courrier_entrants(request):
    return _liste_courriers(request, TypeCourrier.ENTRANT)


@login_required
def courrier_sortants(request):
    return _liste_courriers(request, TypeCourrier.SORTANT)


@login_required
def courrier_list(request):
    return redirect("courrier:entrants")


@login_required
def courrier_create(request):
    extraction = None
    initial = {}
    type_defaut = request.GET.get("type")
    if type_defaut in (TypeCourrier.ENTRANT, TypeCourrier.SORTANT):
        initial["type_courrier"] = type_defaut
    scan_form = ScanUploadForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and "analyser" in request.POST:
        if scan_form.is_valid() and scan_form.cleaned_data.get("fichier"):
            uploaded = scan_form.cleaned_data["fichier"]
            with tempfile.NamedTemporaryFile(suffix="_" + uploaded.name, delete=False) as tmp:
                for chunk in uploaded.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            extraction = analyze_document(tmp_path)
            initial.update(
                {
                    "objet": extraction.objet,
                    "emetteur": extraction.emetteur,
                    "recepteur": extraction.recepteur,
                    "reference_externe": extraction.reference,
                    "resume": extraction.resume,
                    "urgence": "URGENT" if extraction.urgence == "Urgent" else "NORMAL",
                }
            )
            if not extraction.ocr_disponible:
                messages.warning(
                    request,
                    "OCR indisponible sur ce serveur (dépendances optionnelles non installées). "
                    "Veuillez saisir les informations manuellement.",
                )
            else:
                messages.info(request, "Document analysé. Vérifiez les informations proposées avant l'enregistrement.")
        form = CourrierForm(initial=initial)

    elif request.method == "POST" and "enregistrer" in request.POST:
        form = CourrierForm(request.POST)
        if form.is_valid():
            courrier = form.save(commit=False)
            courrier.created_by = request.user
            courrier.statut = "ENREGISTRE"
            # Le service n'est plus saisi dans le formulaire : il est affecté
            # automatiquement (service de l'agent connecté, sinon le premier actif)
            courrier.service = request.user.service or Service.objects.filter(actif=True).first()
            courrier.save()
            form.save_m2m()
            courrier.log_action(request.user, "Enregistrement", "Courrier enregistré au bureau d'ordre")

            # Enrichit la liste des correspondants pour l'autocomplétion future
            for nom in (courrier.emetteur, courrier.recepteur):
                if nom.strip():
                    Correspondant.objects.get_or_create(nom=nom.strip())

            uploaded = request.FILES.get("fichier")
            if uploaded:
                Document.objects.create(
                    fichier=uploaded,
                    nom=uploaded.name,
                    type_document=TypeDocument.IMAGE if not uploaded.name.lower().endswith(".pdf") else TypeDocument.PDF,
                    content_type=ContentType.objects.get_for_model(Courrier),
                    object_id=courrier.id,
                    uploaded_by=request.user,
                )
            messages.success(request, f"Courrier {courrier.numero_ordre} enregistré avec succès.")
            return redirect("courrier:detail", pk=courrier.pk)
    else:
        form = CourrierForm(initial=initial)

    return render(
        request,
        "courrier/courrier_form.html",
        {
            "form": form,
            "scan_form": scan_form,
            "extraction": extraction,
            "correspondants": Correspondant.objects.filter(actif=True),
        },
    )


@login_required
def courrier_detail(request, pk):
    courrier = get_object_or_404(Courrier.objects.select_related("service"), pk=pk)
    statut_form = StatutChangeForm(initial={"statut": courrier.statut})

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "lier":
            cible = Courrier.objects.filter(pk=request.POST.get("courrier_cible")).first()
            if cible and cible.pk != courrier.pk:
                courrier.courriers_lies.add(cible)
                courrier.log_action(request.user, f"Liaison avec la correspondance {cible.numero_ordre}")
                messages.success(request, f"Correspondance {cible.numero_ordre} liée.")
            return redirect("courrier:detail", pk=courrier.pk)

        if action == "delier":
            cible = Courrier.objects.filter(pk=request.POST.get("courrier_cible")).first()
            if cible:
                courrier.courriers_lies.remove(cible)
                messages.success(request, f"Liaison avec {cible.numero_ordre} supprimée.")
            return redirect("courrier:detail", pk=courrier.pk)

        statut_form = StatutChangeForm(request.POST)
        if statut_form.is_valid():
            ancien_statut = courrier.get_statut_display()
            courrier.statut = statut_form.cleaned_data["statut"]
            courrier.save()
            courrier.log_action(
                request.user,
                f"Changement de statut : {ancien_statut} → {courrier.get_statut_display()}",
                statut_form.cleaned_data.get("commentaire", ""),
            )
            messages.success(request, "Statut mis à jour.")
            return redirect("courrier:detail", pk=courrier.pk)

    return render(
        request,
        "courrier/courrier_detail.html",
        {
            "courrier": courrier,
            "statut_form": statut_form,
            "historique": courrier.historique.select_related("user"),
            "documents": courrier.documents.all(),
            "courriers_lies": courrier.courriers_lies.all(),
            "similaires": courrier.correspondances_similaires(),
        },
    )
