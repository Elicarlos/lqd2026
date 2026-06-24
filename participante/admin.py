from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.timezone import localtime
from import_export import fields, resources
from import_export.admin import ImportExportActionModelAdmin, ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from .models import (
    Profile, DocumentoFiscal, Campanha, PostoTrabalho, RegistroJornada,
    SystemRole, SystemPermission, SystemResource, RolePermission, 
    RoleResource, UserRole, DashboardCard, RoleCard,
    ConfiguracaoJornada, ExcecaoJornada, CardDinamico, Funcionalidade, ConfiguracaoSistema, ConfiguracaoSecao, URLTreinamento,
    TipoJornada, JornadaColaborador, ReversaoImpressao, Auditoria
)
from .forms import CampanhaAdminForm  # Importa o novo formulário




class UserResource(resources.ModelResource):
    class Meta:
        model = User


class PostoTrabalhoResource(resources.ModelResource):
    class Meta:
        model = PostoTrabalho


class PostoTrabalhoAdmin(ImportExportModelAdmin):
    list_display = ["nome", "descricao"]
    resource_class = PostoTrabalhoResource


class MyUserAdmin(ImportExportActionModelAdmin, ImportExportModelAdmin, UserAdmin):
    resource_class = UserResource


class ProfileResource(resources.ModelResource):

    class Meta:
        model = Profile


class DocumentoFiscalResource(resources.ModelResource):

    class Meta:
        model = DocumentoFiscal


class CampanhaResource(resources.ModelResource):
    class Meta:
        model = Campanha


class RegistroJornadaResource(resources.ModelResource):
    cpf = fields.Field(
        column_name="CPF",
        attribute="user",
        widget=ForeignKeyWidget(User, "profile__CPF"),
    )
    posto_trabalho = fields.Field(
        column_name="POSTO DE TRABALHO",
        attribute="posto_trabalho",
        widget=ForeignKeyWidget(PostoTrabalho, "nome"),
    )
    inicio = fields.Field(
        column_name="INÍCIO",
        attribute="horario_inicio",
    )
    fim = fields.Field(
        column_name="FIM",
        attribute="horario_fim",
    )
    duracao = fields.Field(column_name="DURAÇÃO", readonly=True)

    class Meta:
        model = RegistroJornada
        fields = ("cpf", "posto_trabalho", "inicio", "fim", "duracao")

    def dehydrate_inicio(self, obj):
        if obj.horario_inicio:
            return localtime(obj.horario_inicio).strftime("%d de %B de %Y às %H:%M:%S")
        return "N/A"

    def dehydrate_fim(self, obj):
        if obj.horario_fim:
            return localtime(obj.horario_fim).strftime("%d de %B de %Y às %H:%M:%S")
        return "N/A"

    def dehydrate_duracao(self, obj):
        """Calcula e formata a duração."""
        duracao = obj.calcular_duracao()
        if duracao:
            total_segundos = int(duracao.total_seconds())
            horas = total_segundos // 3600
            minutos = (total_segundos % 3600) // 60
            segundos = total_segundos % 60
            return f"{horas}h {minutos}m {segundos}s"
        return "N/A"


class RegistroJornadaAdmin(ImportExportModelAdmin):
    list_display = [
        "user_cpf",
        "posto_trabalho",
        "status",
        "inicio_formatado",
        "fim_formatado",
        "duracao_formatada",
        "finalizada_por",
    ]
    search_fields = ["user__profile__CPF", "posto_trabalho__nome", "observacoes"]
    list_filter = ["status", "posto_trabalho", "horario_inicio", "horario_fim", "finalizada_por"]
    resource_class = RegistroJornadaResource
    list_editable = ["status"]

    def user_cpf(self, obj):
        """Exibe o CPF do usuário."""
        return obj.user.profile.CPF if hasattr(obj.user, "profile") else "N/A"

    user_cpf.short_description = "CPF"

    def inicio_formatado(self, obj):
        return (
            localtime(obj.horario_inicio).strftime("%d de %B de %Y às %H:%M:%S")
            if obj.horario_inicio
            else "N/A"
        )

    inicio_formatado.short_description = "Início"

    def fim_formatado(self, obj):
        return (
            localtime(obj.horario_fim).strftime("%d de %B de %Y às %H:%M:%S")
            if obj.horario_fim
            else "N/A"
        )

    fim_formatado.short_description = "Fim"

    def duracao_formatada(self, obj):
        """Exibe a duração formatada."""
        return self.resource_class().dehydrate_duracao(obj)

    duracao_formatada.short_description = "Duração"


class ProfileAdmin(ImportExportModelAdmin):
    list_display = [
        "user",
        "nome",
        "CPF",
        "ativo",
        "pendente",
        "dataCadastro",
        "posto_trabalho",
    ]
    list_filter = ('ativo', 'pendente', 'sexo', 'estado', 'dataCadastro')
    search_fields = ('nome', 'CPF', 'user__email')
    readonly_fields = ('dataCadastro',)
    ordering = ('-dataCadastro',)
    resource_class = ProfileResource


class DocumentoFiscalAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = [
        "user",
        "numeroDocumento",
        "lojista",
        "observacao",
        "vendedor",
        "dataDocumento",
        "valorDocumento",
        "compradoREDE",
        "compradoMASTERCARD",
        "valorREDE",
        "valorMASTERCARD",
        "valorVirtual",
        "dataCadastro",
        "cadastrado_por",
    ]

    readonly_fields = ("posto_trabalho", "enviado_por_operador")

    search_fields = (
        "numeroDocumento",
        "user__username",
        "cadastrado_por__username",
        "lojista__CNPJLojista",
    )
    resource_class = DocumentoFiscalResource


@admin.register(Campanha)
class CampanhaAdmin(ImportExportModelAdmin):
    form = CampanhaAdminForm  # Usa o formulário customizado
    list_display = [
        "nome",
        "data_inicio",
        "data_fim",
        "valor",  # Adicionado para visibilidade
        "ativa",
        "criada_em",
    ]
    fieldsets = (
        (None, {"fields": ("nome", "data_inicio", "data_fim", "valor", "ativa")}),
        (
            "Configurações Visuais",
            {
                "fields": (
                    "logo_principal",
                    "banner_hero",
                    "cor_primaria",
                    "cor_hover",
                ),
                "description": "Personalize a aparência da sua campanha.",
            },
        ),
        (
            "Informações de Contato",
            {
                "fields": ("instagram", "site", "whatsapp"),
                "description": "Links para redes sociais e contato da campanha.",
            },
        ),
        (
            "Status e Auditoria",
            {
                "fields": ("criada_em", "finalizada_em", "finalizada_por"),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = ("criada_em", "finalizada_em", "finalizada_por")
    resource_class = CampanhaResource


admin.site.unregister(User)
admin.site.register(User, MyUserAdmin)





class SystemRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_system_role', 'created_at')
    list_filter = ('is_system_role', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)


class SystemPermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'codename', 'category', 'is_system_permission', 'created_at')
    list_filter = ('category', 'is_system_permission', 'created_at')
    search_fields = ('name', 'codename', 'description')
    ordering = ('category', 'name')


class SystemResourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'codename', 'icon', 'url', 'is_system_resource', 'created_at')
    list_filter = ('is_system_resource', 'created_at')
    search_fields = ('name', 'codename', 'description')
    ordering = ('name',)


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1


class RoleResourceInline(admin.TabularInline):
    model = RoleResource
    extra = 1


class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 1


class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'permission', 'created_at')
    list_filter = ('role', 'permission', 'created_at')
    search_fields = ('role__name', 'permission__name')
    ordering = ('role__name', 'permission__name')


class RoleResourceAdmin(admin.ModelAdmin):
    list_display = ('role', 'resource', 'created_at')
    list_filter = ('role', 'resource', 'created_at')
    search_fields = ('role__name', 'resource__name')
    ordering = ('role__name', 'resource__name')


class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'created_by', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('user__profile__nome', 'user__email', 'role__name')
    ordering = ('user__profile__nome', 'role__name')


class DashboardCardAdmin(admin.ModelAdmin):
    list_display = ('name', 'codename', 'card_type', 'order', 'is_active', 'is_system_card')
    list_filter = ('card_type', 'is_active', 'is_system_card', 'created_at')
    search_fields = ('name', 'codename', 'title', 'description')
    ordering = ('order', 'name')
    list_editable = ('order', 'is_active')


class RoleCardInline(admin.TabularInline):
    model = RoleCard
    extra = 1


class RoleCardAdmin(admin.ModelAdmin):
    list_display = ('role', 'card', 'created_at')
    list_filter = ('role', 'card__card_type', 'created_at')
    search_fields = ('role__name', 'card__name')
    ordering = ('role__name', 'card__name')


class ConfiguracaoJornadaAdmin(admin.ModelAdmin):
    list_display = ('grupo', 'requer_jornada', 'jornada_flexivel', 'tolerancia_entrada', 'tolerancia_saida', 'ativo')
    list_filter = ('requer_jornada', 'jornada_flexivel', 'ativo', 'created_at')
    search_fields = ('grupo__name',)
    list_editable = ('requer_jornada', 'jornada_flexivel', 'tolerancia_entrada', 'tolerancia_saida', 'ativo')
    ordering = ('grupo__name',)


class ExcecaoJornadaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo', 'data_inicio', 'data_fim', 'ativo', 'created_by')
    list_filter = ('tipo', 'ativo', 'data_inicio', 'data_fim', 'created_at')
    search_fields = ('usuario__username', 'usuario__profile__nome', 'justificativa')
    list_editable = ('ativo',)
    ordering = ('-data_inicio', 'usuario__profile__nome')
    date_hierarchy = 'data_inicio'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Se é uma nova exceção
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# Registrar os modelos
admin.site.register(Profile, ProfileAdmin)
admin.site.register(DocumentoFiscal, DocumentoFiscalAdmin)
admin.site.register(PostoTrabalho, PostoTrabalhoAdmin)
admin.site.register(RegistroJornada, RegistroJornadaAdmin)

# Sistema de permissões
admin.site.register(SystemRole, SystemRoleAdmin)
admin.site.register(SystemPermission, SystemPermissionAdmin)
admin.site.register(SystemResource, SystemResourceAdmin)
admin.site.register(RolePermission, RolePermissionAdmin)
admin.site.register(RoleResource, RoleResourceAdmin)
admin.site.register(UserRole, UserRoleAdmin)

# Dashboard Cards
admin.site.register(DashboardCard, DashboardCardAdmin)
admin.site.register(RoleCard, RoleCardAdmin)

# Configurações de Jornada
admin.site.register(ConfiguracaoJornada, ConfiguracaoJornadaAdmin)
admin.site.register(ExcecaoJornada, ExcecaoJornadaAdmin)

# Admin para Cards Dinâmicos
@admin.register(CardDinamico)
class CardDinamicoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'ativo', 'ordem', 'mostrar_apenas_admin', 'mostrar_apenas_staff']
    list_filter = ['tipo', 'ativo', 'mostrar_apenas_admin', 'mostrar_apenas_staff', 'grupos_permitidos']
    search_fields = ['nome', 'titulo', 'descricao']
    list_editable = ['ativo', 'ordem']
    filter_horizontal = ['grupos_permitidos', 'usuarios_permitidos', 'usuarios_excluidos']
    ordering = ['ordem', 'nome']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'titulo', 'descricao', 'tipo', 'icone', 'cor', 'url', 'ordem')
        }),
        ('Visibilidade', {
            'fields': ('ativo', 'mostrar_apenas_admin', 'mostrar_apenas_staff')
        }),
        ('Permissões', {
            'fields': ('grupos_permitidos', 'usuarios_permitidos', 'usuarios_excluidos'),
            'description': 'Configure quem pode ver este card. Deixe vazio para permitir todos.'
        }),
    )

# Admin para Funcionalidades
@admin.register(Funcionalidade)
class FuncionalidadeAdmin(admin.ModelAdmin):
    list_display = ['nome', 'codigo', 'tipo', 'modelo', 'ativo']
    list_filter = ['tipo', 'ativo', 'grupos_permitidos']
    search_fields = ['nome', 'codigo', 'descricao']
    list_editable = ['ativo']
    filter_horizontal = ['grupos_permitidos', 'usuarios_permitidos', 'usuarios_excluidos']
    ordering = ['nome']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'codigo', 'descricao', 'tipo', 'modelo')
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
        ('Permissões', {
            'fields': ('grupos_permitidos', 'usuarios_permitidos', 'usuarios_excluidos'),
            'description': 'Configure quem pode usar esta funcionalidade.'
        }),
    )

# Admin para Configurações do Sistema
@admin.register(ConfiguracaoSistema)
class ConfiguracaoSistemaAdmin(admin.ModelAdmin):
    list_display = ['chave', 'tipo', 'ativo', 'updated_at']
    list_filter = ['tipo', 'ativo']
    search_fields = ['chave', 'descricao']
    list_editable = ['ativo']
    ordering = ['chave']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('chave', 'valor', 'descricao', 'tipo')
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
    )


@admin.register(URLTreinamento)
class URLTreinamentoAdmin(admin.ModelAdmin):
    """Admin para URLs de treinamento"""
    list_display = ['titulo', 'hash_url', 'ativo', 'criado_por', 'data_criacao', 'total_colaboradores']
    list_filter = ['ativo', 'data_criacao', 'criado_por']
    search_fields = ['titulo', 'hash_url', 'descricao']
    readonly_fields = ['hash_url', 'data_criacao', 'total_colaboradores']
    ordering = ['-data_criacao']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('titulo', 'descricao', 'hash_url')
        }),
        ('Controle', {
            'fields': ('ativo', 'criado_por', 'data_criacao')
        }),
        ('Estatísticas', {
            'fields': ('total_colaboradores', 'colaboradores_cadastrados'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Se é uma nova URL
            import uuid
            obj.hash_url = str(uuid.uuid4())[:8]  # Gera hash único
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(ConfiguracaoSecao)
class ConfiguracaoSecaoAdmin(admin.ModelAdmin):
    """Admin para configurações de seções do dashboard"""
    list_display = ['tipo', 'titulo', 'cor', 'ativo', 'ordem']
    list_filter = ['ativo', 'cor']
    list_editable = ['ativo', 'ordem']
    search_fields = ['tipo', 'titulo']
    ordering = ['ordem', 'tipo']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('tipo', 'titulo', 'icone')
        }),
        ('Aparência', {
            'fields': ('cor', 'ordem')
        }),
        ('Permissões', {
            'fields': ('grupos_permitidos',),
            'description': 'Selecione os grupos que podem ver esta seção. Deixe vazio para permitir todos.'
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
    )


@admin.register(TipoJornada)
class TipoJornadaAdmin(admin.ModelAdmin):
    """Admin para tipos de jornada"""
    list_display = ['nome', 'hora_inicio', 'hora_fim', 'ativo', 'created_at']
    list_filter = ['ativo', 'dias_semana']
    list_editable = ['ativo']
    search_fields = ['nome']
    ordering = ['nome']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'hora_inicio', 'hora_fim')
        }),
        ('Dias da Semana', {
            'fields': ('dias_semana',),
            'description': 'Selecione os dias da semana em que esta jornada é válida'
        }),
        ('Tolerâncias', {
            'fields': ('tolerancia_entrada', 'tolerancia_saida'),
            'description': 'Tolerâncias em minutos'
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
    )


@admin.register(JornadaColaborador)
class JornadaColaboradorAdmin(admin.ModelAdmin):
    """Admin para jornadas de colaboradores"""
    list_display = ['colaborador', 'tipo_jornada', 'data_inicio', 'data_fim', 'ativo']
    list_filter = ['ativo', 'tipo_jornada', 'data_inicio']
    list_editable = ['ativo']
    search_fields = ['colaborador__username', 'colaborador__first_name', 'colaborador__last_name']
    ordering = ['-data_inicio']
    
    fieldsets = (
        ('Colaborador e Jornada', {
            'fields': ('colaborador', 'tipo_jornada')
        }),
        ('Período', {
            'fields': ('data_inicio', 'data_fim'),
            'description': 'Deixe data_fim vazia para período indefinido'
        }),
        ('Informações Adicionais', {
            'fields': ('observacoes', 'ativo')
        }),
    )


@admin.register(ReversaoImpressao)
class ReversaoImpressaoAdmin(admin.ModelAdmin):
    """Admin para reversões de impressão"""
    list_display = ['documento', 'usuario', 'data_reversao', 'cupons_removidos']
    list_filter = ['data_reversao', 'usuario']
    search_fields = ['documento__numeroDocumento', 'usuario__username', 'motivo']
    ordering = ['-data_reversao']
    readonly_fields = ['data_reversao']
    
    fieldsets = (
        ('Documento e Usuário', {
            'fields': ('documento', 'usuario')
        }),
        ('Detalhes da Reversão', {
            'fields': ('cupons_removidos', 'motivo', 'data_reversao')
        }),
    )


@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    """Admin para registros de auditoria"""
    list_display = ['usuario', 'tipo_acao', 'data_hora', 'documento_fiscal']
    list_filter = ['tipo_acao', 'data_hora', 'usuario']
    search_fields = ['usuario__username', 'descricao', 'justificativa']
    ordering = ['-data_hora']
    readonly_fields = ['data_hora', 'ip_address', 'user_agent']
    
    fieldsets = (
        ('Ação', {
            'fields': ('usuario', 'tipo_acao', 'descricao')
        }),
        ('Documento Relacionado', {
            'fields': ('documento_fiscal',),
            'classes': ('collapse',)
        }),
        ('Informações Adicionais', {
            'fields': ('justificativa', 'ip_address', 'user_agent', 'data_hora'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Não permite adicionar registros de auditoria manualmente"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Não permite editar registros de auditoria"""
        return False



