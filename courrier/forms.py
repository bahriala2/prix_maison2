from django import forms

from core.models import Service

from .models import Courrier


class CourrierForm(forms.ModelForm):
    class Meta:
        model = Courrier
        fields = [
            "type_courrier", "date_courrier", "emetteur", "recepteur", "objet",
            "reference_externe", "urgence", "resume", "remarque",
        ]
        labels = {"reference_externe": "Référence"}
        widgets = {
            # format ISO obligatoire pour que le champ HTML type=date affiche
            # la valeur par défaut (la date du jour, définie sur le modèle)
            "date_courrier": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
            "type_courrier": forms.Select(attrs={"class": "form-select"}),
            "emetteur": forms.TextInput(attrs={"class": "form-control", "list": "liste-correspondants", "autocomplete": "off"}),
            "recepteur": forms.TextInput(attrs={"class": "form-control", "list": "liste-correspondants", "autocomplete": "off"}),
            "objet": forms.TextInput(attrs={"class": "form-control"}),
            "reference_externe": forms.TextInput(attrs={"class": "form-control"}),
            "urgence": forms.Select(attrs={"class": "form-select"}),
            "resume": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "remarque": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class ScanUploadForm(forms.Form):
    fichier = forms.FileField(
        required=False,
        label="Document scanné (PDF ou image)",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )


class StatutChangeForm(forms.Form):
    statut = forms.ChoiceField(choices=Courrier._meta.get_field("statut").choices, widget=forms.Select(attrs={"class": "form-select"}))
    commentaire = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}))


class CourrierSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Recherche", widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "N°, objet, émetteur, récepteur..."}))
    type_courrier = forms.ChoiceField(required=False, choices=[("", "Tous")] + list(Courrier._meta.get_field("type_courrier").choices), widget=forms.Select(attrs={"class": "form-select"}))
    statut = forms.ChoiceField(required=False, choices=[("", "Tous")] + list(Courrier._meta.get_field("statut").choices), widget=forms.Select(attrs={"class": "form-select"}))
    service = forms.ModelChoiceField(required=False, queryset=Service.objects.all(), widget=forms.Select(attrs={"class": "form-select"}))
