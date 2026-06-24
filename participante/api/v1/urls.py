from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentoViewSet, 
    ProfileViewSet, 
    TestJWTView, 
    AdminDashboardMetricsView,
    PostoTrabalhoViewSet,
    BaterPontoView,
    HistoricoPontoView,
    CampanhaAtivaView,
    SystemPermissionViewSet,
    SystemRoleViewSet
)

router = DefaultRouter()
router.register(r"profile", ProfileViewSet)
router.register(r"documentos", DocumentoViewSet)
router.register(r"posto-trabalho", PostoTrabalhoViewSet)
router.register(r"permissions", SystemPermissionViewSet, basename="permissions")
router.register(r"roles", SystemRoleViewSet, basename="roles")

urlpatterns = [
    path("", include(router.urls)),
    path("test-jwt/", TestJWTView.as_view(), name="test_jwt"),
    path("admin-dashboard/", AdminDashboardMetricsView.as_view(), name="admin_dashboard"),
    path("ponto/registrar/", BaterPontoView.as_view(), name="ponto_registrar"),
    path("ponto/historico/", HistoricoPontoView.as_view(), name="ponto_historico"),
    path("campanha/ativa/", CampanhaAtivaView.as_view(), name="campanha_ativa"),
]
