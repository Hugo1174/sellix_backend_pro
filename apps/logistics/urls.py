from django.urls import path

from .views import CarrierWebhookView

urlpatterns = [
    path("logistics/webhook/<str:provider>/", CarrierWebhookView.as_view(),
         name="carrier-webhook"),
]
