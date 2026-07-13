from django.urls import path

from . import views

app_name = "achats"

urlpatterns = [
    path("", views.demande_list, name="list"),
    path("signees-bureau-ordre/", views.demandes_signees_bo, name="signees_bo"),
    path("nouvelle/", views.demande_create, name="create"),
    path("<int:pk>/", views.demande_detail, name="detail"),
]
