from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "service", "is_active")
    list_filter = ("role", "service", "is_active", "is_staff")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Informations administratives", {"fields": ("role", "service", "telephone", "fonction")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Informations administratives", {"fields": ("role", "service", "telephone", "fonction")}),
    )
