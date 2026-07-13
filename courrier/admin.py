from django.contrib import admin

from .models import Courrier, HistoriqueAction


class HistoriqueInline(admin.TabularInline):
    model = HistoriqueAction
    extra = 0
    readonly_fields = ("user", "action", "commentaire", "date_action")
    can_delete = False


@admin.register(Courrier)
class CourrierAdmin(admin.ModelAdmin):
    list_display = (
        "numero_ordre", "type_courrier", "objet", "emetteur", "recepteur",
        "service", "statut", "urgence", "date_courrier",
    )
    list_filter = ("type_courrier", "statut", "urgence", "service")
    search_fields = ("numero_ordre", "objet", "emetteur", "recepteur", "reference_externe")
    readonly_fields = ("numero_ordre", "created_by", "created_at", "updated_at")
    inlines = [HistoriqueInline]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(HistoriqueAction)
class HistoriqueActionAdmin(admin.ModelAdmin):
    list_display = ("courrier", "action", "user", "date_action")
    list_filter = ("action",)
