from django.contrib import admin

from .models import Correspondant, Service

admin.site.site_header = "DTPCSSO"
admin.site.site_title = "DTPCSSO"
admin.site.index_title = "Gestion administrative"


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("nom", "code", "actif")
    search_fields = ("nom", "code")
    list_filter = ("actif",)


@admin.register(Correspondant)
class CorrespondantAdmin(admin.ModelAdmin):
    list_display = ("nom", "actif")
    search_fields = ("nom",)
    list_filter = ("actif",)
