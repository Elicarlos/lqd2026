from rest_framework import serializers
from django.contrib.auth import get_user_model

from ...models import (
    DocumentoFiscal, Profile, PostoTrabalho, RegistroJornada, Campanha,
    SystemPermission, SystemRole
)

User = get_user_model()


class CampanhaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campanha
        fields = ["id", "nome", "data_inicio", "data_fim", "valor", "instagram", "site", "whatsapp", "ativa", "banner_hero"]


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = "__all__"


class DocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoFiscal
        fields = "__all__"


class PostoTrabalhoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostoTrabalho
        fields = "__all__"


class RegistroJornadaSerializer(serializers.ModelSerializer):
    posto_trabalho_detalhe = PostoTrabalhoSerializer(source="posto_trabalho", read_only=True)
    duracao = serializers.SerializerMethodField()

    class Meta:
        model = RegistroJornada
        fields = "__all__"

    def get_duracao(self, obj):
        return obj.get_duracao_formatada()


class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_active", "is_staff"]


class SystemPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemPermission
        fields = ["id", "name", "codename", "category", "description"]


class SystemRoleSerializer(serializers.ModelSerializer):
    permissions_codenames = serializers.SerializerMethodField()

    class Meta:
        model = SystemRole
        fields = ["id", "name", "description", "permissions_codenames"]

    def get_permissions_codenames(self, obj):
        return list(obj.rolepermission_set.values_list('permission__codename', flat=True))


class ColaboradorSerializer(serializers.ModelSerializer):
    user = UserShortSerializer(read_only=True)
    grupos = serializers.SerializerMethodField()
    permissoes_calculadas = serializers.SerializerMethodField()
    permissoes_adicionais_codenames = serializers.SerializerMethodField()
    permissoes_excluidas_codenames = serializers.SerializerMethodField()
    posto_trabalho_nome = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "id", "nome", "CPF", "is_colaborador", "status_ativo", "posto_trabalho", "posto_trabalho_nome",
            "user", "grupos", "permissoes_calculadas", 
            "permissoes_adicionais_codenames", "permissoes_excluidas_codenames"
        ]

    def get_posto_trabalho_nome(self, obj):
        return obj.posto_trabalho.nome if obj.posto_trabalho else None

    def get_grupos(self, obj):
        return [{"id": g.id, "name": g.name} for g in obj.user.groups.all()]

    def get_permissoes_calculadas(self, obj):
        return obj.get_all_permissions()

    def get_permissoes_adicionais_codenames(self, obj):
        return list(obj.permissoes_adicionais.values_list('codename', flat=True))

    def get_permissoes_excluidas_codenames(self, obj):
        return list(obj.permissoes_excluidas.values_list('codename', flat=True))
