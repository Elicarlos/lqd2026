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




def get_storage():
    """
    Retorna o storage apropriado baseado nas configurações.
    Esta função garante que o storage correto seja usado mesmo com cache do Django.
    """
    if getattr(settings, 'USE_S3', False):
        from liquida2018.storage_backends import MediaStorage
        return MediaStorage()
    return None  # None usa o DEFAULT_FILE_STORAGE quando USE_S3=False


def calcular_horas_trabalhadas_diaria(operador, data):
    registros = RegistroJornada.objects.filter(
        operador=operador, horario_inicio__date=data
    )

    total_horas = timedelta()
    for registro in registros:
        duracao = registro.calcular_duracao()
        if duracao:
            total_horas += duracao

    return total_horas


class ConfiguracaoSistema(models.Model):
    """Configurações gerais do sistema"""
    chave = models.CharField(max_length=100, unique=True, verbose_name="Chave")
    valor = models.TextField(verbose_name="Valor")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    tipo = models.CharField(
        max_length=20, 
        choices=[
            ('TEXT', 'Texto'),
            ('NUMBER', 'Número'),
            ('BOOLEAN', 'Booleano'),
            ('JSON', 'JSON'),
            ('URL', 'URL'),
        ],
        default='TEXT',
        verbose_name="Tipo"
    )
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['chave']
        verbose_name = "Configuração do Sistema"
        verbose_name_plural = "Configurações do Sistema"
    
    def __str__(self):
        return self.chave
    
    @classmethod
    def get_valor(cls, chave, default=None):
        """Obtém o valor de uma configuração"""
        try:
            config = cls.objects.get(chave=chave, ativo=True)
            return config.valor
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def set_valor(cls, chave, valor, descricao="", tipo="TEXT"):
        """Define o valor de uma configuração"""
        config, created = cls.objects.get_or_create(
            chave=chave,
            defaults={
                'valor': str(valor),
                'descricao': descricao,
                'tipo': tipo
            }
        )
        if not created:
            config.valor = str(valor)
            config.save(update_fields=['valor', 'updated_at'])
        return config


class URLTreinamento(models.Model):
    """
    Modelo para controlar URLs de treinamento para cadastro de colaboradores.
    
    Permite criar URLs públicas com hash único para cadastro de colaboradores
    durante treinamentos, com controle de ativação/desativação.
    """
    hash_url = models.CharField(max_length=50, unique=True, verbose_name="Hash da URL")
    titulo = models.CharField(max_length=100, verbose_name="Título do Treinamento")
    descricao = models.TextField(verbose_name="Descrição")
    ativo = models.BooleanField(default=True, verbose_name="URL Ativa")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Criado por")
    colaboradores_cadastrados = models.ManyToManyField('Profile', blank=True, verbose_name="Colaboradores Cadastrados")
    
    class Meta:
        verbose_name = "URL de Treinamento"
        verbose_name_plural = "URLs de Treinamento"
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.titulo} ({self.hash_url})"
    
    def get_url_completa(self, request=None):
        """Retorna a URL completa para cadastro"""
        if request:
            # Se temos o request, usa build_absolute_uri
            return request.build_absolute_uri(f'/cadastro/{self.hash_url}/')
        else:
            # Fallback para configuração manual
            from django.conf import settings
            site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
            return f"{site_url}/cadastro/{self.hash_url}/"
    
    @property
    def url_completa(self):
        """Retorna a URL completa para cadastro (sem request)"""
        return self.get_url_completa()
    
    @property
    def total_colaboradores(self):
        """Retorna o total de colaboradores cadastrados via esta URL"""
        return self.colaboradores_cadastrados.count()
    
    def ativar(self):
        """Ativa a URL de treinamento"""
        self.ativo = True
        self.save()
    
    def desativar(self):
        """Desativa a URL de treinamento"""
        self.ativo = False
        self.save()


class Auditoria(models.Model):
    """
    Modelo para rastrear todas as ações importantes do sistema.
    Permite auditoria completa de quem fez o quê, quando e por quê.
    """
    TIPO_ACAO_CHOICES = [
        ('reversao_impressao', 'Reversão de Impressão'),
        ('cancelamento_impressao', 'Cancelamento de Impressão'),
        ('impressao_cupons', 'Impressão de Cupons'),
        ('validacao_documento', 'Validação de Documento'),
        ('edicao_documento', 'Edição de Documento'),
        ('cadastro_documento', 'Cadastro de Documento'),
        ('finalizacao_jornada', 'Finalização de Jornada'),
        ('selecao_posto', 'Seleção de Posto de Trabalho'),
        ('login', 'Login no Sistema'),
        ('logout', 'Logout do Sistema'),
        ('alteracao_senha', 'Alteração de Senha'),
        ('outro', 'Outro'),
    ]
    
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='acoes_auditoria',
        verbose_name="Usuário que realizou a ação"
    )
    data_hora = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data e Hora da Ação"
    )
    tipo_acao = models.CharField(
        max_length=50,
        choices=TIPO_ACAO_CHOICES,
        verbose_name="Tipo de Ação"
    )
    descricao = models.TextField(
        verbose_name="Descrição da Ação"
    )
    documento_fiscal = models.ForeignKey(
        'DocumentoFiscal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='auditorias',
        verbose_name="Documento Fiscal Relacionado"
    )
    justificativa = models.TextField(
        blank=True,
        null=True,
        verbose_name="Justificativa da Ação"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Endereço IP"
    )
    user_agent = models.TextField(
        blank=True,
        null=True,
        verbose_name="User Agent"
    )
    
    class Meta:
        verbose_name = "Registro de Auditoria"
        verbose_name_plural = "Registros de Auditoria"
        ordering = ['-data_hora']
        indexes = [
            models.Index(fields=['usuario', 'data_hora']),
            models.Index(fields=['tipo_acao', 'data_hora']),
            models.Index(fields=['documento_fiscal', 'data_hora']),
        ]
    
    def __str__(self):
        return f"{self.usuario.username} - {self.get_tipo_acao_display()} - {self.data_hora.strftime('%d/%m/%Y %H:%M')}"
    
    @classmethod
    def registrar_acao(cls, usuario, tipo_acao, descricao, documento_fiscal=None, justificativa=None, request=None):
        """
        Registra uma nova ação na auditoria.
        
        Args:
            usuario: Usuário que realizou a ação
            tipo_acao: Tipo da ação (usar choices do modelo)
            descricao: Descrição detalhada da ação
            documento_fiscal: Documento relacionado (opcional)
            justificativa: Justificativa da ação (opcional)
            request: Request object para capturar IP e User Agent (opcional)
        """
        ip_address = None
        user_agent = None
        
        if request:
            # Capturar IP do usuário
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            # Capturar User Agent
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        return cls.objects.create(
            usuario=usuario,
            tipo_acao=tipo_acao,
            descricao=descricao,
            documento_fiscal=documento_fiscal,
            justificativa=justificativa,
            ip_address=ip_address,
            user_agent=user_agent
        )


