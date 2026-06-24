from rest_framework import serializers
from lojista.models import Lojista, RamoAtividade, Localizacao

class RamoAtividadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RamoAtividade
        fields = "__all__"

class LocalizacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Localizacao
        fields = "__all__"

class LojistaSerializer(serializers.ModelSerializer):
    ramoAtividade_detalhe = RamoAtividadeSerializer(source="ramoAtividade", read_only=True)
    localizacao_detalhe = LocalizacaoSerializer(source="localizacao", read_only=True)

    class Meta:
        model = Lojista
        fields = "__all__"
