from django.urls import path

from . import views

app_name = "courrier"

urlpatterns = [
    path("", views.courrier_list, name="list"),
    path("entrants/", views.courrier_entrants, name="entrants"),
    path("sortants/", views.courrier_sortants, name="sortants"),
    path("nouveau/", views.courrier_create, name="create"),
    path("<int:pk>/", views.courrier_detail, name="detail"),
]
