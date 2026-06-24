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




from .configuracao import get_storage

class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="profile"
    )
    date_of_birth = models.DateField(blank=True, null=True)
    photo = models.ImageField(
        upload_to="users/%Y/%m/%d", 
        blank=True,
        storage=get_storage()  # Usa storage explícito para garantir S3 quando USE_S3=True
    )
    CHOICES_SEXO = (("M", "Masculino"), ("F", "Feminino"), ("P", "Prefiro não dizer"))
    nome = models.CharField(max_length=100, blank=True)
    RG = models.CharField(max_length=40, blank=True, unique=False)
    CPF = models.CharField(max_length=14, blank=True, unique=True)
    # dataAtual = models.DateField(verbose_name=u'Data Atual', null=True, blank=True)  #mudar depois para nao colocar a data atual
    sexo = models.CharField(
        verbose_name="Sexo",
        max_length=1,
        choices=CHOICES_SEXO,
        blank=True,
        help_text="ex. M ou F ou P",
    )
    foneFixo = models.CharField(
        verbose_name="Telefone Fixo",
        max_length=20,
        blank=True,
        help_text="ex. (85)3212-0000",
    )
    foneCelular1 = models.CharField(
        verbose_name="Celular1",
        max_length=20,
        blank=True,
        help_text="ex. (85)98888-8675",
    )
    foneCelular2 = models.CharField(
        verbose_name="Celular2",
        max_length=20,
        blank=True,
        help_text="ex. (85)98888-8675",
    )
    foneCelular3 = models.CharField(
        verbose_name="Celular3",
        max_length=20,
        blank=True,
        help_text="ex. (85)98888-8675",
    )
    whatsapp = models.CharField(
        max_length=20, blank=True, help_text="ex. (85)98888-8675"
    )
    facebook = models.CharField(
        max_length=50, blank=True, help_text="ex. fb.com/nomenofacebook"
    )
    twitter = models.CharField(max_length=50, blank=True)
    endereco = models.CharField(verbose_name="Endereço", max_length=150, blank=True)
    enderecoNumero = models.CharField(
        verbose_name="Nº Endereço", max_length=200, blank=True
    )
    enderecoComplemento = models.CharField(
        verbose_name="Complemento", max_length=100, blank=True
    )

    @property
    def jornada_atual(self):
        """Retorna a jornada ativa do colaborador para hoje"""
        from django.utils import timezone
        from datetime import date
        
        hoje = date.today()
        try:
            return JornadaColaborador.objects.filter(
                colaborador=self.user,
                data_inicio__lte=hoje,
                ativo=True
            ).filter(
                models.Q(data_fim__isnull=True) | models.Q(data_fim__gte=hoje)
            ).get()
        except JornadaColaborador.DoesNotExist:
            return None
    
    def requer_controle_jornada(self):
        """Verifica se o usuário precisa de controle de jornada"""
        # Verifica exceções individuais primeiro
        excecao = ExcecaoJornada.objects.filter(
            usuario=self.user,
            tipo='SEM_JORNADA',
            ativo=True
        ).filter(
            models.Q(data_fim__isnull=True) | models.Q(data_fim__gte=timezone.localdate())
        ).first()
        
        if excecao and excecao.is_vigente():
            return False
        
        # Verifica configuração do grupo
        for grupo in self.user.groups.all():
            config = ConfiguracaoJornada.objects.filter(
                grupo=grupo,
                ativo=True
            ).first()
            
            if config and not config.requer_jornada:
                return False
        
        # Verifica configuração individual
        return self.requer_jornada
    
    def tem_jornada_flexivel(self):
        """Verifica se o usuário tem jornada flexível"""
        # Verifica exceções individuais primeiro
        excecao = ExcecaoJornada.objects.filter(
            usuario=self.user,
            tipo='JORNADA_FLEXIVEL',
            ativo=True
        ).filter(
            models.Q(data_fim__isnull=True) | models.Q(data_fim__gte=timezone.localdate())
        ).first()
        
        if excecao and excecao.is_vigente():
            return True
        
        # Verifica configuração do grupo
        for grupo in self.user.groups.all():
            config = ConfiguracaoJornada.objects.filter(
                grupo=grupo,
                ativo=True
            ).first()
            
            if config and config.jornada_flexivel:
                return True
        
        # Verifica configuração individual
        return self.jornada_flexivel
    
    def get_jornada_ativa(self):
        """Retorna a jornada ativa do usuário"""
        return RegistroJornada.get_jornada_ativa(self.user)
    
    def tem_jornada_ativa(self):
        """Verifica se o usuário tem uma jornada ativa"""
        return self.get_jornada_ativa() is not None
    
    def pode_iniciar_jornada(self):
        """Verifica se o usuário pode iniciar uma nova jornada"""
        # Se não requer jornada, não pode iniciar
        if not self.requer_controle_jornada():
            return False, "Usuário não requer controle de jornada"
        
        # Se já tem jornada ativa, não pode iniciar outra
        if self.tem_jornada_ativa():
            return False, "Usuário já possui jornada ativa"
        
        # Verificar se já tem uma jornada ativa hoje (não pode ter duas jornadas ativas simultaneamente)
        from datetime import date
        hoje = date.today()
        jornada_ativa_hoje = RegistroJornada.objects.filter(
            user=self.user,
            horario_inicio__date=hoje,
            status='ATIVA',
            horario_fim__isnull=True
        ).exists()
        
        if jornada_ativa_hoje:
            return False, "Você já possui uma jornada ativa hoje. Finalize a jornada atual antes de iniciar uma nova."
        
        # Se tem jornada flexível, pode iniciar a qualquer momento
        if self.tem_jornada_flexivel():
            return True, "Jornada flexível permitida"
        
        # Verifica se está no horário permitido usando a mesma lógica de verificar_jornada_ativa
        from datetime import date
        hoje = date.today()
        try:
            jornada_colaborador = JornadaColaborador.objects.filter(
                colaborador=self.user,
                data_inicio__lte=hoje,
                ativo=True
            ).filter(
                models.Q(data_fim__isnull=True) | models.Q(data_fim__gte=hoje)
            ).get()
            pode_logar, motivo = jornada_colaborador.tipo_jornada.pode_logar_agora()
            if pode_logar:
                return True, "Horário permitido"
            else:
                return False, motivo
        except JornadaColaborador.DoesNotExist:
            return False, "Nenhuma jornada configurada para hoje"
    bairro = models.CharField(max_length=40, blank=True)
    cidade = models.CharField(max_length=50, blank=True, default="Teresina")
    estado = models.CharField(max_length=2, blank=True, default="PI")
    CEP = models.CharField(max_length=12, blank=True)
    observacao = models.TextField(
        verbose_name="Observação", max_length=1000, blank=True, null=True
    )  # , widget=forms.Textarea(attrs={'placeholder': 'Escreva aqui alguma observação caso seja necessário.'}))
    dataCadastro = models.DateTimeField(
        verbose_name="Cadastrado em", auto_now_add=True, editable=False
    )  # nao vai aparecer na tela
    pergunta = models.TextField(
        verbose_name="Pergunta", max_length=50, blank=True, null=True
    )  # , widget=forms.Textarea(attrs={'placeholder': 'Escreva aqui alguma observação caso seja necessário.'}))
    ativo = models.BooleanField(default=True)
    pendente = models.BooleanField(default=True, verbose_name="Pendente")
    termos_de_aceite = models.BooleanField(
        default=False, verbose_name="Termos de aceite para tratamento de dados pessoais"
    )
    posto_trabalho = models.ForeignKey(
        'PostoTrabalho',
        verbose_name="Posto de trabalho",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    cadastrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Cadastrado Por",
        related_name="rel_cadastrado_por",
        editable=False,
    )
    
    is_colaborador = models.BooleanField(
        default=False,
        verbose_name="É Colaborador",
        help_text="Define se este usuário é um colaborador (equipe interna) ou participante comum"
    )
    
    senha_temporaria = models.BooleanField(
        default=False,
        verbose_name="Senha Temporária",
        help_text="Indica se o usuário precisa trocar a senha no próximo login"
    )
    
    status_ativo = models.BooleanField(
        default=True,
        verbose_name="Status Ativo",
        help_text="Para colaboradores: indica se o cadastro está ativo e configurado"
    )
    
    # Campos para controle de jornada
    requer_jornada = models.BooleanField(
        default=True,
        verbose_name="Requer controle de jornada",
        help_text="Se este usuário precisa de controle de jornada"
    )
    jornada_flexivel = models.BooleanField(
        default=False,
        verbose_name="Jornada flexível",
        help_text="Permite entrada/saída sem horário fixo"
    )
    ultima_jornada_data = models.DateField(
        null=True, blank=True,
        verbose_name="Data da última jornada",
        help_text="Data do último registro de jornada"
    )

    permissoes_adicionais = models.ManyToManyField(
        "SystemPermission",
        blank=True,
        related_name="perfis_adicionais",
        verbose_name="Permissões Adicionais",
        help_text="Permissões explicitamente concedidas a este usuário"
    )
    permissoes_excluidas = models.ManyToManyField(
        "SystemPermission",
        blank=True,
        related_name="perfis_excluidos",
        verbose_name="Permissões Excluídas",
        help_text="Permissões explicitamente revogadas para este usuário"
    )

    def get_all_permissions(self):
        """Consolida as permissões do usuário baseado em seus grupos e exceções individuais."""
        if self.user.is_superuser:
            from .permissao import SystemPermission
            return list(SystemPermission.objects.values_list('codename', flat=True))
            
        permissions = set()
        
        # 1. Obter permissões das SystemRoles associadas aos grupos do usuário ou UserRoles
        from .permissao import SystemRole
        roles_nomes = [g.name for g in self.user.groups.all()]
        roles = SystemRole.objects.filter(
            models.Q(name__in=roles_nomes) | models.Q(userrole__user=self.user)
        )
        for role in roles:
            permissions.update(role.rolepermission_set.values_list('permission__codename', flat=True))
            
        # 2. Adicionar permissões explícitas concedidas individualmente ao usuário
        permissions.update(self.permissoes_adicionais.values_list('codename', flat=True))
        
        # 3. Remover permissões explícitas bloqueadas individualmente ao usuário
        permissions.difference_update(self.permissoes_excluidas.values_list('codename', flat=True))
        
        return list(permissions)

    def __str__(self):
        return "Nome completo {}".format(self.user.username)

    def get_absolute_url_edit(self):
        return reverse("participante:user_edit", args=[self.user.id])

    def get_absolute_url_detail(self):
        return reverse("participante:user_detail", args=[self.user.id])

    def clean(self):
        """Validações customizadas do modelo"""
        super().clean()
        
        # Verificar se colaborador está tentando participar da campanha
        if self.is_colaborador and self.user.is_staff:
            raise ValidationError({
                'is_colaborador': 'Colaboradores não podem participar da campanha. Esta funcionalidade é restrita a participantes comuns.'
            })


