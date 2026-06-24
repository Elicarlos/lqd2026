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




class PostoTrabalho(models.Model):
    nome = models.CharField(max_length=250)
    descricao = models.TextField(blank=True)

    def __str__(self):
        return self.nome


class TipoJornada(models.Model):
    """
    Define tipos de jornada de trabalho com horários e dias da semana
    """
    nome = models.CharField(
        max_length=100,
        verbose_name="Nome da Jornada",
        help_text="Ex: Manhã, Tarde, Noite, Integral"
    )
    hora_inicio = models.TimeField(
        verbose_name="Horário de Início",
        help_text="Horário de início da jornada"
    )
    hora_fim = models.TimeField(
        verbose_name="Horário de Fim", 
        help_text="Horário de fim da jornada"
    )
    dias_semana = models.JSONField(
        default=list,
        verbose_name="Dias da Semana",
        help_text="Lista com números dos dias: 1=Segunda, 2=Terça, ..., 7=Domingo"
    )
    tolerancia_entrada = models.PositiveIntegerField(
        default=15,
        verbose_name="Tolerância Entrada (min)",
        help_text="Minutos de tolerância antes do horário de início"
    )
    tolerancia_saida = models.PositiveIntegerField(
        default=15,
        verbose_name="Tolerância Saída (min)",
        help_text="Minutos de tolerância após o horário de fim"
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo",
        help_text="Se esta jornada está ativa para uso"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Tipo de Jornada"
        verbose_name_plural = "Tipos de Jornada"
        ordering = ['nome']
        permissions = [
            ("criar_jornada", "Pode criar tipos de jornada"),
            ("editar_jornada", "Pode editar tipos de jornada"),
            ("excluir_jornada", "Pode excluir tipos de jornada"),
            ("visualizar_jornada", "Pode visualizar tipos de jornada"),
        ]
    
    def __str__(self):
        return f"{self.nome} ({self.hora_inicio.strftime('%H:%M')} - {self.hora_fim.strftime('%H:%M')})"
    
    def get_dias_semana_display(self):
        """Retorna os dias da semana em formato legível"""
        dias_map = {
            1: "Segunda", 2: "Terça", 3: "Quarta", 
            4: "Quinta", 5: "Sexta", 6: "Sábado", 7: "Domingo"
        }
        return ", ".join([dias_map.get(dia, str(dia)) for dia in self.dias_semana])
    
    def pode_logar_agora(self):
        """Verifica se é possível fazer login neste momento considerando esta jornada"""
        from django.utils import timezone
        now = timezone.localtime()
        
        # Verifica se hoje é um dia permitido
        dia_semana = now.isoweekday()  # 1=Segunda, 7=Domingo
        if dia_semana not in self.dias_semana:
            return False, "Hoje não é um dia de trabalho para esta jornada"
        
        # Horário atual
        hora_atual = now.time()
        
        # Verifica se está dentro do horário permitido
        if self.hora_inicio <= hora_atual <= self.hora_fim:
            return True, "Horário permitido"
            
        return False, f"Fora do horário. Permitido das {self.hora_inicio.strftime('%H:%M')} às {self.hora_fim.strftime('%H:%M')}"


class JornadaColaborador(models.Model):
    """
    Associa colaboradores a tipos específicos de jornada
    """
    colaborador = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="jornadas_atribuidas",
        verbose_name="Colaborador"
    )
    tipo_jornada = models.ForeignKey(
        TipoJornada,
        on_delete=models.CASCADE,
        related_name="colaboradores",
        verbose_name="Tipo de Jornada"
    )
    data_inicio = models.DateField(
        verbose_name="Data de Início",
        help_text="A partir de quando esta jornada vale para o colaborador"
    )
    data_fim = models.DateField(
        null=True, blank=True,
        verbose_name="Data de Fim",
        help_text="Até quando esta jornada vale (deixe vazio para indefinido)"
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo",
        help_text="Se esta atribuição está ativa"
    )
    observacoes = models.TextField(
        blank=True,
        verbose_name="Observações",
        help_text="Observações sobre esta atribuição de jornada"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Jornada do Colaborador"
        verbose_name_plural = "Jornadas dos Colaboradores"
        ordering = ['-data_inicio']
        # Evita múltiplas jornadas ativas para o mesmo colaborador no mesmo período
        unique_together = ['colaborador', 'data_inicio']
        permissions = [
            ("atribuir_jornada", "Pode atribuir jornadas a colaboradores"),
            ("editar_atribuicao", "Pode editar atribuições de jornada"),
            ("remover_atribuicao", "Pode remover atribuições de jornada"),
            ("visualizar_atribuicoes", "Pode visualizar atribuições de jornada"),
        ]
    
    def __str__(self):
        return f"{self.colaborador.username} - {self.tipo_jornada.nome}"
    
    def is_vigente(self, data=None):
        """Verifica se esta jornada está vigente na data especificada (ou hoje)"""
        from django.utils import timezone
        if data is None:
            data = timezone.localdate()
        
        if not self.ativo:
            return False
        
        if data < self.data_inicio:
            return False
        
        if self.data_fim and data > self.data_fim:
            return False
        
        return True
    
    @classmethod
    def get_jornada_ativa(cls, colaborador, data=None):
        """Retorna a jornada ativa do colaborador para a data especificada"""
        from django.utils import timezone
        if data is None:
            data = timezone.localdate()
        
        return cls.objects.filter(
            colaborador=colaborador,
            ativo=True,
            data_inicio__lte=data
        ).filter(
            models.Q(data_fim__isnull=True) | models.Q(data_fim__gte=data)
        ).first()


class RegistroJornada(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="registros_jornada",
        verbose_name="Usuário",
        help_text="Usuário ao qual a jornada pertence.",
    )
    posto_trabalho = models.ForeignKey(
        'PostoTrabalho',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Posto de Trabalho",
        help_text="Posto de trabalho selecionado.",
    )
    horario_inicio = models.DateTimeField(
        verbose_name="Horário de Início", help_text="Data e hora de início da jornada."
    )
    horario_fim = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Horário de Fim",
        help_text="Data e hora de término da jornada (opcional).",
    )

    ultimo_update = models.DateTimeField(default=timezone.now)
    
    # Novos campos para melhor controle
    status = models.CharField(
        max_length=20,
        choices=[
            ('ATIVA', 'Ativa'),
            ('FINALIZADA', 'Finalizada'),
            ('PAUSA', 'Em Pausa'),
            ('CANCELADA', 'Cancelada')
        ],
        default='ATIVA',
        verbose_name="Status"
    )
    observacoes = models.TextField(
        blank=True,
        verbose_name="Observações",
        help_text="Observações sobre esta jornada"
    )
    finalizada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="jornadas_finalizadas",
        verbose_name="Finalizada por"
    )

    class Meta:
        verbose_name = "Registro de Jornada"
        verbose_name_plural = "Registros de Jornada"

    def clean(self):
        """Valida que o horário de fim seja maior que o horário de início."""
        if self.horario_fim and self.horario_fim <= self.horario_inicio:
            raise ValidationError(
                {
                    "horario_fim": "O horário de fim deve ser maior que o horário de início."
                }
            )

    def save(self, *args, **kwargs):
        """Finaliza registros anteriores ativos antes de criar um novo."""
        if not self.horario_fim:
            RegistroJornada.objects.filter(
                user=self.user, horario_fim__isnull=True
            ).exclude(id=self.id).update(horario_fim=now())

        self.full_clean()
        super().save(*args, **kwargs)

    def calcular_duracao(self):
        """Calcula a duração entre o horário de início e fim."""
        if (
            self.horario_inicio
            and self.horario_fim
            and self.horario_fim > self.horario_inicio
        ):
            return self.horario_fim - self.horario_inicio
        return timedelta(0)  # Retorna 0 caso não haja um horário válido

    @staticmethod
    def calcular_horas_diarias(user, data):
        """Calcula as horas trabalhadas em um dia específico."""
        registros = RegistroJornada.objects.filter(user=user, horario_inicio__date=data)
        total_horas = registros.annotate(
            duracao=ExpressionWrapper(
                F("horario_fim") - F("horario_inicio"), output_field=DurationField()
            )
        ).aggregate(total=Sum("duracao"))["total"]
        return total_horas or timedelta(0)

    @staticmethod
    def calcular_horas_mensais(user, ano, mes):
        """Calcula as horas trabalhadas em um mês específico."""
        registros = RegistroJornada.objects.filter(
            user=user, horario_inicio__year=ano, horario_inicio__month=mes
        )
        total_horas = registros.annotate(
            duracao=ExpressionWrapper(
                F("horario_fim") - F("horario_inicio"), output_field=DurationField()
            )
        ).aggregate(total=Sum("duracao"))["total"]
        return total_horas or timedelta(0)

    @staticmethod
    def formatar_duracao(duracao):
        """Formata a duração em horas, minutos e segundos."""
        total_segundos = duracao.total_seconds()
        horas = int(total_segundos // 3600)
        minutos = int((total_segundos % 3600) // 60)
        segundos = int(total_segundos % 60)
        return f"{horas}h {minutos}m {segundos}s"
    
    def get_duracao_formatada(self):
        """Retorna a duração formatada da jornada atual"""
        duracao = self.calcular_duracao()
        return self.formatar_duracao(duracao) if duracao else "N/A"

    def is_ativa(self):
        """Verifica se a jornada está ativa"""
        return self.status == 'ATIVA' and not self.horario_fim
    
    def finalizar(self, finalizada_por=None, observacoes=None, deslogar_usuario=True):
        """
        Finaliza a jornada
        
        Args:
            finalizada_por: Usuário que finalizou a jornada
            observacoes: Observações sobre a finalização
            deslogar_usuario: Se deve deslogar o usuário (padrão: True)
        """
        self.horario_fim = timezone.now()
        self.status = 'FINALIZADA'
        if finalizada_por:
            self.finalizada_por = finalizada_por
        if observacoes:
            self.observacoes = observacoes
        self.save()
        
        # Deslogar o usuário se solicitado e se atender aos critérios
        if deslogar_usuario and self._deve_deslogar_usuario(finalizada_por):
            self._deslogar_usuario()
    
    def _deve_deslogar_usuario(self, finalizada_por):
        """
        Verifica se o usuário deve ser deslogado
        
        Critérios:
        - Deve ter um usuário que finalizou a jornada
        - Não deve ser o próprio usuário finalizando sua jornada
        - Deve ser um colaborador (is_staff=True)
        """
        if not finalizada_por:
            return False
        
        if finalizada_por == self.user:
            return False
        
        # Verificar se é um colaborador
        if not hasattr(self.user, 'is_staff') or not self.user.is_staff:
            return False
        
        return True
    
    def _deslogar_usuario(self):
        """Desloga o usuário da jornada"""
        try:
            from django.contrib.sessions.models import Session
            from django.utils import timezone
            
            agora = timezone.now()
            sessions = Session.objects.filter(expire_date__gt=agora)
            
            for session in sessions:
                if session.get_decoded().get('_auth_user_id') == str(self.user.id):
                    session.delete()
                    print(f"🔒 Usuário {self.user.username} deslogado após finalização da jornada")
                    break
                    
        except Exception as e:
            print(f"⚠️ Erro ao deslogar usuário {self.user.username}: {e}")
    
    def pausar(self, observacoes=None):
        """Pausa a jornada"""
        self.status = 'PAUSA'
        if observacoes:
            self.observacoes = observacoes
        self.save()
    
    def retomar(self, observacoes=None):
        """Retoma uma jornada pausada"""
        self.status = 'ATIVA'
        if observacoes:
            self.observacoes = observacoes
        self.save()
    
    def cancelar(self, observacoes=None):
        """Cancela a jornada"""
        self.status = 'CANCELADA'
        if observacoes:
            self.observacoes = observacoes
        self.save()
    
    @classmethod
    def get_jornada_ativa(cls, user):
        """Retorna a jornada ativa do usuário"""
        return cls.objects.filter(
            user=user,
            status='ATIVA',
            horario_fim__isnull=True
        ).first()
    
    @classmethod
    def get_jornadas_do_dia(cls, user, data=None):
        """Retorna todas as jornadas do usuário em uma data específica"""
        from django.utils import timezone
        if data is None:
            data = timezone.localdate()
        
        return cls.objects.filter(
            user=user,
            horario_inicio__date=data
        ).order_by('horario_inicio')
    
    def __str__(self):
        """Representação legível do objeto."""
        inicio_formatado = (
            localtime(self.horario_inicio).strftime("%d/%m/%Y %H:%M:%S")
            if self.horario_inicio
            else "N/A"
        )
        fim_formatado = (
            localtime(self.horario_fim).strftime("%d/%m/%Y %H:%M:%S")
            if self.horario_fim
            else "N/A"
        )
        duracao = self.calcular_duracao()
        duracao_formatada = self.formatar_duracao(duracao) if duracao else "N/A"

        return f"{self.user.username} - {self.status} - Início: {inicio_formatado} - Fim: {fim_formatado} - Duração: {duracao_formatada}"


class ConfiguracaoJornada(models.Model):
    """Configurações globais do sistema de jornada por grupo"""
    grupo = models.ForeignKey(
        'auth.Group',
        on_delete=models.CASCADE,
        verbose_name="Grupo",
        help_text="Grupo de usuários afetado por esta configuração"
    )
    requer_jornada = models.BooleanField(
        default=True,
        verbose_name="Requer controle de jornada",
        help_text="Se este grupo precisa de controle de jornada"
    )
    jornada_flexivel = models.BooleanField(
        default=False,
        verbose_name="Jornada flexível",
        help_text="Permite entrada/saída sem horário fixo"
    )
    tolerancia_entrada = models.PositiveIntegerField(
        default=15,
        verbose_name="Tolerância entrada (min)",
        help_text="Minutos de tolerância antes do horário de início"
    )
    tolerancia_saida = models.PositiveIntegerField(
        default=15,
        verbose_name="Tolerância saída (min)",
        help_text="Minutos de tolerância após o horário de fim"
    )
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de Jornada"
        verbose_name_plural = "Configurações de Jornada"
        unique_together = ['grupo']

    def __str__(self):
        return f"Configuração para {self.grupo.name}"


class ExcecaoJornada(models.Model):
    """Exceções individuais para controle de jornada"""
    TIPO_CHOICES = [
        ('SEM_JORNADA', 'Sem controle de jornada'),
        ('JORNADA_FLEXIVEL', 'Jornada flexível'),
        ('HORARIO_ESPECIAL', 'Horário especial'),
        ('FERIADO', 'Feriado/Evento'),
    ]
    
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Usuário",
        related_name="excecoes_jornada"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        verbose_name="Tipo de Exceção"
    )
    data_inicio = models.DateField(verbose_name="Data de Início")
    data_fim = models.DateField(
        null=True, blank=True,
        verbose_name="Data de Fim",
        help_text="Deixe vazio para exceção permanente"
    )
    horario_inicio = models.TimeField(
        null=True, blank=True,
        verbose_name="Horário de Início",
        help_text="Para horários especiais"
    )
    horario_fim = models.TimeField(
        null=True, blank=True,
        verbose_name="Horário de Fim",
        help_text="Para horários especiais"
    )
    justificativa = models.TextField(
        verbose_name="Justificativa",
        help_text="Motivo da exceção"
    )
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="excecoes_criadas"
    )

    class Meta:
        verbose_name = "Exceção de Jornada"
        verbose_name_plural = "Exceções de Jornada"
        ordering = ['-data_inicio']

    def __str__(self):
        return f"{self.usuario.username} - {self.get_tipo_display()}"
    
    def is_vigente(self, data=None):
        """Verifica se a exceção está vigente na data especificada"""
        from django.utils import timezone
        if data is None:
            data = timezone.localdate()
        
        if not self.ativo:
            return False
        
        if data < self.data_inicio:
            return False
        
        if self.data_fim and data > self.data_fim:
            return False
        
        return True


