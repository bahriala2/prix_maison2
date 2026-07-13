from django import forms

from .models import Marche


class MarcheForm(forms.ModelForm):
    class Meta:
        model = Marche
        fields = [
            "objet", "type_procedure", "service_demandeur", "demande_achat",
            "fournisseur", "montant", "date_lancement", "date_attribution",
            "date_notification", "date_cloture", "statut",
        ]
        widgets = {
            "objet": forms.TextInput(attrs={"class": "form-control"}),
            "type_procedure": forms.Select(attrs={"class": "form-select"}),
            "service_demandeur": forms.Select(attrs={"class": "form-select"}),
            "demande_achat": forms.Select(attrs={"class": "form-select"}),
            "fournisseur": forms.TextInput(attrs={"class": "form-control"}),
            "montant": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "date_lancement": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
            "date_attribution": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
            "date_notification": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
            "date_cloture": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
            "statut": forms.Select(attrs={"class": "form-select"}),
        }
