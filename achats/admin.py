from django.contrib import admin

from .models import Approbation, DemandeAchat


class ApprobationInline(admin.TabularInline):
    model = Approbation
    extra = 0


@admin.register(DemandeAchat)
class DemandeAchatAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "objet", "circuit", "service_demandeur", "type_achat",
        "montant_estimatif", "statut", "date_signature_directeur", "numero_ordre_bo",
    )
    list_filter = ("circuit", "statut", "type_achat", "service_demandeur")
    search_fields = ("reference", "objet", "numero_ordre_bo")
    readonly_fields = ("reference", "created_by", "created_at", "updated_at")
    inlines = [ApprobationInline]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Approbation)
class ApprobationAdmin(admin.ModelAdmin):
    list_display = ("demande", "valideur", "fonction", "decision", "date_validation")
    list_filter = ("decision",)
