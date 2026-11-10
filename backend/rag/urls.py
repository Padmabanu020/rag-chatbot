from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health),
    path("documents/", views.documents),
    path("documents/<int:pk>/", views.document_detail),
    path("chat/", views.chat),
    path("history/", views.history),
]
