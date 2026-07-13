from django.contrib import admin

from .models import Marche


@admin.register(Marche)
class MarcheAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "objet", "type_procedure", "service_demandeur",
        "fournisseur", "montant", "statut", "date_lancement", "date_cloture",
    )
    list_filter = ("statut", "type_procedure", "service_demandeur")
    search_fields = ("reference", "objet", "fournisseur")
    readonly_fields = ("reference", "created_by", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
