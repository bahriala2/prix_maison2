from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MarcheForm
from .models import Marche, StatutMarche


# Filtres par colonne de la liste des marchés : paramètre GET -> filtre ORM
MARCHE_COLUMN_FILTERS = {
    "reference": "reference__icontains",
    "objet": "objet__icontains",
    "procedure": "type_procedure",
    "fournisseur": "fournisseur__icontains",
    "statut": "statut",
}


@login_required
def marche_list(request):
    from .models import TypeProcedure

    marches = Marche.objects.select_related("service_demandeur").all()
    filtres = {}
    for param, lookup in MARCHE_COLUMN_FILTERS.items():
        valeur = request.GET.get(param, "").strip()
        if valeur:
            marches = marches.filter(**{lookup: valeur})
            filtres[param] = valeur

    return render(
        request,
        "marches/marche_list.html",
        {
            "marches": marches,
            "filtres": filtres,
            "statuts": StatutMarche.choices,
            "procedures": TypeProcedure.choices,
        },
    )


@login_required
def marche_create(request):
    if request.method == "POST":
        form = MarcheForm(request.POST)
        if form.is_valid():
            marche = form.save(commit=False)
            marche.created_by = request.user
            marche.save()
            messages.success(request, f"Marché {marche.reference} créé.")
            return redirect("marches:detail", pk=marche.pk)
    else:
        form = MarcheForm()
    return render(request, "marches/marche_form.html", {"form": form})


@login_required
def marche_detail(request, pk):
    marche = get_object_or_404(Marche.objects.select_related("service_demandeur", "demande_achat"), pk=pk)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "lier":
            cible = Marche.objects.filter(pk=request.POST.get("marche_cible")).first()
            if cible and cible.pk != marche.pk:
                marche.marches_lies.add(cible)
                messages.success(request, f"Marché {cible.reference} lié.")
        elif action == "delier":
            cible = Marche.objects.filter(pk=request.POST.get("marche_cible")).first()
            if cible:
                marche.marches_lies.remove(cible)
                messages.success(request, f"Liaison avec {cible.reference} supprimée.")
        return redirect("marches:detail", pk=marche.pk)

    return render(
        request,
        "marches/marche_detail.html",
        {
            "marche": marche,
            "documents": marche.documents.all(),
            "marches_lies": marche.marches_lies.all(),
            "similaires": marche.marches_similaires(),
        },
    )
