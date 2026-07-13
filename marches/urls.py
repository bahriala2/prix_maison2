from django.urls import path

from . import views

app_name = "marches"

urlpatterns = [
    path("", views.marche_list, name="list"),
    path("nouveau/", views.marche_create, name="create"),
    path("<int:pk>/", views.marche_detail, name="detail"),
]
