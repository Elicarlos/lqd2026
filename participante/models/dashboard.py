from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from lojista.models import Lojista
from django.urls import reverse
from django.core import validators
from django.core.mail import EmailMessage
import datetime
from datetime import timedelta
from django.utils import timezone
import logging
from django.utils.timezone import now
from django.db.models import F, ExpressionWrapper, DurationField, Sum
from django.utils.timezone import localtime
from django.contrib.auth import get_user_model

User = get_user_model()




from .permissao import SystemRole
from .campanha import Campanha

class DashboardCard(models.Model):
    """
    Modelo para controlar quais cards do dashboard cada grupo pode acessar.
    """
    CARD_TYPES = [
        ('participantes', 'Participantes'),
        ('lojistas', 'Lojistas'),
        ('configuracoes', 'Configurações'),
        ('backoffice', 'Backoffice'),
        ('relatorios', 'Relatórios'),
        ('documentos', 'Documentos'),
        ('usuarios', 'Usuários'),
        ('campanha', 'Campanha'),
        ('ponto', 'Registro de Ponto'),
        ('impressao', 'Impressão'),
        ('estatisticas', 'Estatísticas'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    codename = models.CharField(max_length=50, unique=True)
    card_type = models.CharField(max_length=20, choices=CARD_TYPES)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    url_name = models.CharField(max_length=100, blank=True)
    icon = models.CharField(max_length=50, default='fas fa-cog')
    color = models.CharField(max_length=20, default='blue')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_system_card = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Card do Dashboard"
        verbose_name_plural = "Cards do Dashboard"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class RoleCard(models.Model):
    """
    Modelo para relacionar funções e cards do dashboard.
    """
    role = models.ForeignKey(SystemRole, on_delete=models.CASCADE)
    card = models.ForeignKey(DashboardCard, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ["role", "card"]
        verbose_name = "Card da Função"
        verbose_name_plural = "Cards das Funções"
    
    def __str__(self):
        return f"{self.role.name} - {self.card.name}"


class CardDinamico(models.Model):
    """Modelo para cards dinâmicos que podem ser configurados via admin"""
    TIPO_CHOICES = [
        ('PARTICIPANTE', 'Participante'),
        ('LOJISTA', 'Lojista'),
        ('RECURSOS_HUMANOS', 'Recursos Humanos'),
        ('BACKOFFICE', 'Backoffice'),
        ('RELATORIO', 'Relatório'),
        ('CONFIGURACAO', 'Configuração'),
        ('OPERACOES', 'Operações'),
    ]
    
    ICONE_CHOICES = [
        ('fas fa-chart-bar', 'Gráfico'),
        ('fas fa-file-alt', 'Documento'),
        ('fas fa-users', 'Usuários'),
        ('fas fa-store', 'Loja'),
        ('fas fa-ticket-alt', 'Cupom'),
        ('fas fa-clock', 'Jornada'),
        ('fas fa-cog', 'Configuração'),
        ('fas fa-chart-line', 'Relatório'),
        ('fas fa-database', 'Dados'),
        ('fas fa-tools', 'Ferramentas'),
        ('fas fa-eye', 'Visualizar'),
        ('fas fa-edit', 'Editar'),
        ('fas fa-plus', 'Adicionar'),
        ('fas fa-trash', 'Excluir'),
        ('fas fa-download', 'Download'),
        ('fas fa-upload', 'Upload'),
        ('fas fa-print', 'Imprimir'),
        ('fas fa-search', 'Buscar'),
        ('fas fa-filter', 'Filtrar'),
        ('fas fa-sort', 'Ordenar'),
    ]
    
    nome = models.CharField(max_length=100, verbose_name="Nome do Card")
    titulo = models.CharField(max_length=200, verbose_name="Título")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo")
    icone = models.CharField(max_length=50, choices=ICONE_CHOICES, verbose_name="Ícone")
    cor = models.CharField(max_length=20, default='primary', verbose_name="Cor")
    url = models.CharField(max_length=200, blank=True, verbose_name="URL de destino")
    ordem = models.PositiveIntegerField(default=0, verbose_name="Ordem de exibição")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    grupos_permitidos = models.ManyToManyField(
        'auth.Group', 
        blank=True, 
        verbose_name="Grupos permitidos",
        help_text="Deixe vazio para permitir todos os grupos"
    )
    usuarios_permitidos = models.ManyToManyField(
        User, 
        blank=True, 
        verbose_name="Usuários permitidos",
        help_text="Usuários específicos que podem ver este card"
    )
    usuarios_excluidos = models.ManyToManyField(
        User, 
        blank=True, 
        related_name='cards_excluidos',
        verbose_name="Usuários excluídos",
        help_text="Usuários específicos que NÃO podem ver este card"
    )
    mostrar_apenas_admin = models.BooleanField(
        default=False, 
        verbose_name="Mostrar apenas para admin"
    )
    mostrar_apenas_staff = models.BooleanField(
        default=False, 
        verbose_name="Mostrar apenas para staff"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['ordem', 'nome']
        verbose_name = "Card Dinâmico"
        verbose_name_plural = "Cards Dinâmicos"
    
    def __str__(self):
        return self.nome
    
    def pode_ver(self, user):
        """Verifica se o usuário pode ver este card"""
        # Superusers sempre podem ver todos os cards ativos
        if user.is_superuser:
            return self.ativo
        
        # Se não está ativo, ninguém pode ver
        if not self.ativo:
            return False
        
        # Se é apenas para admin e usuário não é admin
        if self.mostrar_apenas_admin and not user.is_superuser:
            return False
        
        # Se é apenas para staff e usuário não é staff
        if self.mostrar_apenas_staff and not user.is_staff:
            return False
        
        # Se usuário está na lista de excluídos
        if self.usuarios_excluidos.filter(id=user.id).exists():
            return False
        
        # Se usuário está na lista de permitidos específicos
        if self.usuarios_permitidos.filter(id=user.id).exists():
            return True
        
        # Se há grupos específicos configurados
        if self.grupos_permitidos.exists():
            # Verifica se o usuário pertence a algum dos grupos permitidos
            return self.grupos_permitidos.filter(id__in=user.groups.all()).exists()
        
        # Se não há restrições específicas, permite para todos
        return True


class Funcionalidade(models.Model):
    """Modelo para funcionalidades do sistema que podem ser controladas por permissão"""
    TIPO_CHOICES = [
        ('VIEW', 'Visualizar'),
        ('CREATE', 'Criar'),
        ('EDIT', 'Editar'),
        ('DELETE', 'Excluir'),
        ('EXPORT', 'Exportar'),
        ('IMPORT', 'Importar'),
        ('PRINT', 'Imprimir'),
        ('VALIDATE', 'Validar'),
        ('APPROVE', 'Aprovar'),
        ('REJECT', 'Rejeitar'),
    ]
    
    nome = models.CharField(max_length=100, verbose_name="Nome da Funcionalidade")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código único")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo")
    modelo = models.CharField(max_length=100, blank=True, verbose_name="Modelo relacionado")
    ativo = models.BooleanField(default=True, verbose_name="Ativa")
    grupos_permitidos = models.ManyToManyField(
        'auth.Group', 
        blank=True, 
        verbose_name="Grupos permitidos"
    )
    usuarios_permitidos = models.ManyToManyField(
        User, 
        blank=True, 
        verbose_name="Usuários permitidos"
    )
    usuarios_excluidos = models.ManyToManyField(
        User, 
        blank=True, 
        related_name='funcionalidades_excluidas',
        verbose_name="Usuários excluídos"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['nome']
        verbose_name = "Funcionalidade"
        verbose_name_plural = "Funcionalidades"
    
    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"
    
    def pode_usar(self, user):
        """Verifica se o usuário pode usar esta funcionalidade"""
        # Superusers sempre podem usar todas as funcionalidades ativas
        if user.is_superuser:
            return self.ativo
        
        if not self.ativo:
            return False
        
        # Se usuário está na lista de excluídos
        if self.usuarios_excluidos.filter(id=user.id).exists():
            return False
        
        # Se usuário está na lista de permitidos específicos
        if self.usuarios_permitidos.filter(id=user.id).exists():
            return True
        
        # Se há grupos específicos configurados
        if self.grupos_permitidos.exists():
            return self.grupos_permitidos.filter(id__in=user.groups.all()).exists()
        
        # Se não há restrições específicas, permite para todos
        return True


class ConfiguracaoSecao(models.Model):
    """Modelo para configurar seções do dashboard"""
    TIPO_CHOICES = [
        ('PARTICIPANTE', 'Participante'),
        ('LOJISTA', 'Lojista'),
        ('RECURSOS_HUMANOS', 'Recursos Humanos'),
        ('BACKOFFICE', 'Backoffice'),
        ('RELATORIO', 'Relatório'),
        ('CONFIGURACAO', 'Configuração'),
        ('OPERACOES', 'Operações'),
    ]
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, unique=True, verbose_name="Tipo da Seção")
    titulo = models.CharField(max_length=100, verbose_name="Título da Seção")
    icone = models.CharField(max_length=50, verbose_name="Ícone", help_text="Código FontAwesome (ex: fas fa-users)")
    cor = models.CharField(max_length=7, default='#0d6efd', verbose_name="Cor do Cabeçalho", help_text="Código hexadecimal (ex: #0d6efd)")
    grupos_permitidos = models.ManyToManyField(
        'auth.Group', 
        blank=True, 
        verbose_name="Grupos que podem ver esta seção",
        help_text="Deixe vazio para permitir todos os grupos"
    )
    ativo = models.BooleanField(default=True, verbose_name="Seção Ativa")
    ordem = models.PositiveIntegerField(default=0, verbose_name="Ordem de Exibição")
    
    class Meta:
        ordering = ['ordem', 'tipo']
        verbose_name = "Configuração de Seção"
        verbose_name_plural = "Configurações de Seções"
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo}"
    
    @classmethod
    def get_config(cls, tipo):
        """Retorna a configuração de uma seção específica"""
        try:
            return cls.objects.get(tipo=tipo, ativo=True)
        except cls.DoesNotExist:
            # Configuração padrão se não existir
            return cls(
                tipo=tipo,
                titulo=tipo.title(),
                icone='fas fa-cog',
                cor='#0d6efd',  # Cor hexadecimal padrão
                ativo=True,
                ordem=0
            )
    
    def pode_ver(self, user):
        """Verifica se o usuário pode ver esta seção"""
        # Superusuários sempre podem ver todas as seções
        if user.is_superuser:
            return True
        
        # Se não está ativo, ninguém pode ver
        if not self.ativo:
            return False
        
        # Se não há grupos específicos, todos podem ver
        if not self.grupos_permitidos.exists():
            return True
        
        # Verificar se o usuário está em algum dos grupos permitidos
        return self.grupos_permitidos.filter(id__in=user.groups.values_list('id', flat=True)).exists()


