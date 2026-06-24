from rest_framework import viewsets

from .models import DocumentoFiscal, Profile
from .serializers import DocumentoSerializer, ProfileSerializer


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    # permission_classes = ['IsAuthenticated']


class DocumentoFiscalViewSet(viewsets.ModelViewSet):
    queryset = DocumentoFiscal.objects.all()
    serializer_class = DocumentoSerializer
    permission_classes = ["IsAuthenticated"]
