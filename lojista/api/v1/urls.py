from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import LojistaViewSet, RamoAtividadeViewSet, LocalizacaoViewSet

router = DefaultRouter()
router.register(r"lojistas", LojistaViewSet)
router.register(r"ramos", RamoAtividadeViewSet)
router.register(r"localizacoes", LocalizacaoViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
