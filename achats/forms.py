from django import forms

from .models import Approbation, DemandeAchat


class DemandeAchatForm(forms.ModelForm):
    class Meta:
        model = DemandeAchat
        fields = [
            "circuit", "service_demandeur", "objet", "description", "montant_estimatif",
            "type_achat", "date_creation",
        ]
        widgets = {
            "circuit": forms.Select(attrs={"class": "form-select"}),
            "service_demandeur": forms.Select(attrs={"class": "form-select"}),
            "objet": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "montant_estimatif": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "type_achat": forms.Select(attrs={"class": "form-select"}),
            "date_creation": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
        }


class ApprobationForm(forms.ModelForm):
    class Meta:
        model = Approbation
        fields = ["fonction", "decision", "commentaire"]
        widgets = {
            "fonction": forms.TextInput(attrs={"class": "form-control"}),
            "decision": forms.Select(attrs={"class": "form-select"}),
            "commentaire": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class SignatureDirecteurForm(forms.Form):
    decision_directeur = forms.CharField(widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}), required=False)
    date_signature_directeur = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d")
    )
