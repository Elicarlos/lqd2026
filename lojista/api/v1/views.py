from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from lojista.models import Lojista, RamoAtividade, Localizacao
from .serializers import LojistaSerializer, RamoAtividadeSerializer, LocalizacaoSerializer

class LojistaViewSet(viewsets.ModelViewSet):
    queryset = Lojista.objects.all().order_by("fantasiaLojista")
    serializer_class = LojistaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["status"]
    search_fields = ["fantasiaLojista", "razaoLojista", "CNPJLojista"]

class RamoAtividadeViewSet(viewsets.ModelViewSet):
    queryset = RamoAtividade.objects.all().order_by("atividade")
    serializer_class = RamoAtividadeSerializer
    permission_classes = [IsAuthenticated]

class LocalizacaoViewSet(viewsets.ModelViewSet):
    queryset = Localizacao.objects.all().order_by("nome")
    serializer_class = LocalizacaoSerializer
    permission_classes = [IsAuthenticated]
