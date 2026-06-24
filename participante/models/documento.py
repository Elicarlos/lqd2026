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




from .campanha import Campanha
from .configuracao import get_storage

def validate_promotional_period(value):
    try:
        campanha_ativa = Campanha.objects.get(ativa=True)
        promotion_start = campanha_ativa.data_inicio
        promotion_end = campanha_ativa.data_fim

        if not (promotion_start <= value <= promotion_end):
            raise ValidationError(
                f"A data do documento deve estar dentro do período da campanha: "
                f"{promotion_start.strftime('%d/%m/%Y')} a {promotion_end.strftime('%d/%m/%Y')}."
            )
    except Campanha.DoesNotExist:
        raise ValidationError("Não há nenhuma campanha ativa configurada no sistema.")
    except Campanha.MultipleObjectsReturned:
        raise ValidationError(
            "ERRO: Existem múltiplas campanhas ativas. Contate o administrador."
        )


def validate_data_futura(value):
    if value > timezone.now().date():
        raise ValidationError("Verifique a data do documento, não pode ser uma data futura.")


class StatusChoices(models.TextChoices):
    PENDENTE = 'pendente', 'Pendente'
    VALIDADO = 'validado', 'Validado'
    INCONSISTENTE = 'inconsistente', 'Inconsistente'


class DocumentoFiscal(models.Model):
    # Lojista_Id = models.ForeignKey('Lojista', verbose_name=u'Loja', on_delete=models.SET_NULL, null=True)
    # Participante_Id = models.ForeignKey('Participante', default=1, verbose_name=u'Participante', on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(
        User, related_name="rel_username", on_delete=models.PROTECT
    )
    lojista = models.ForeignKey(
        Lojista,
        related_name="rel_lojista",
        null=False,
        blank=False,
        default=1,
        on_delete=models.PROTECT,
    )
    vendedor = models.CharField(
        verbose_name="Nome do Vendedor", max_length=50, blank=True, null=True
    )
    numeroDocumento = models.CharField(
        verbose_name="Número do Documento",
        max_length=50,
        blank=False,
        null=False,
        unique=False,
    )
    dataDocumento = models.DateField(
        verbose_name="Data do Documento",
        null=False,
        blank=False,
        validators=[validate_promotional_period, validate_data_futura],
    )
    valorDocumento = models.DecimalField(
        verbose_name="Valor do Documento",
        max_digits=15,
        decimal_places=2,
        blank=False,
        default=0,
    )
    compradoREDE = models.BooleanField(
        verbose_name="Comprou na maquininha da PagBank?", default=False
    )
    compradoMASTERCARD = models.BooleanField(
        verbose_name="Comprou com Elo?", default=False
    )
    compradoCielo = models.BooleanField(
        verbose_name="Comprou com Cielo?", default=False
    )
    valorCielo = models.DecimalField(
        verbose_name="Valor pago na Cielo",
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,  # Permite valores nulos no banco de dados
        default=0,
    )
    valorREDE = models.DecimalField(
        verbose_name="Valor na REDE",
        max_digits=7,
        decimal_places=2,
        editable=False,
        blank=True,
        default=0,
    )  # depois posso nao mostrar
    valorOutros = models.DecimalField(
        verbose_name="Valor pago em outros métodos",
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        default=0,
    )
    photo = models.FileField(
        upload_to="docs/%Y/%m/%d", 
        blank=True, 
        verbose_name="Foto do documento fiscal",
        storage=get_storage()  # Usa storage explícito para garantir S3 quando USE_S3=True
    )
    photo2 = models.FileField(
        upload_to="docs2/%Y/%m/%d",
        blank=True,
        verbose_name="Foto do comprovante do cartão",
        storage=get_storage()  # Usa storage explícito para garantir S3 quando USE_S3=True
    )
    valorMASTERCARD = models.DecimalField(
        verbose_name="Valor no MASTERCARD",
        max_digits=7,
        decimal_places=2,
        editable=False,
        blank=True,
        default=0,
    )
    valorVirtual = models.DecimalField(
        verbose_name="Valor com Bonificações",
        max_digits=20,
        decimal_places=2,
        editable=False,
        blank=True,
        default=0,
    )  # depois posso nao mostrar
    dataCadastro = models.DateTimeField(
        verbose_name="Cadastrado em", auto_now_add=True, editable=False
    )
    cadastrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Cadastrado Por",
        editable=False,
    )
    corrigido_pelo_participante = models.BooleanField(
        default=False,
        verbose_name="Corrigido pelo participante"
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        verbose_name="Status",
        default=StatusChoices.PENDENTE
    )
    observacao = models.TextField(
        verbose_name="Observação",
        max_length=1000,
        blank=True,
        null=True,
        default="Nenhuma",
    )
    # impressaoHab = models.BooleanField(verbose_name=u'Status', default=False)
    qtdeCupom = models.IntegerField(blank=True, null=True, editable=False)
    posto_trabalho = models.ForeignKey(
        'PostoTrabalho',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Posto de Trabalho",
    )
    enviado_por_operador = models.BooleanField(
        default=False, verbose_name="Enviado por operador"
    )

    def save(self, *args, **kwargs):
        # Garantir validações de equivalência sempre que salvar via ORM
        # Executa apenas em criação para minimizar impacto em updates existentes
        try:
            if self._state.adding:
                self.full_clean()
        except ValidationError:
            raise
        super().save(*args, **kwargs)

    def __str__(self):
        return self.numeroDocumento

    class Meta:
        # ordering = ['Participante_Id', 'NumeroDocumento']
        verbose_name = "Documento Fiscal"
        verbose_name_plural = "Documentos Fiscais"
        constraints = [
            models.UniqueConstraint(
                fields=["numeroDocumento", "lojista"],
                name="unique_user_numeroDocumento_lojista",
            )
        ]

    def get_absolute_url(self):
        return reverse("participante:editdocfiscal", args=[self.id])

    def get_absolute_url_byop(self):
        return reverse("participante:editdocfiscalbyop", args=[self.id])

    def clean(self):
        super().clean()
        try:
            campanha_ativa = Campanha.objects.get(ativa=True)
            valor_minimo = campanha_ativa.valor
            if self.valorDocumento < valor_minimo:
                raise ValidationError(
                    {
                        "valorDocumento": f"O valor do documento deve ser de no mínimo R$ {valor_minimo}."
                    }
                )
        except Campanha.DoesNotExist:
            raise ValidationError(
                "Não há nenhuma campanha ativa configurada no sistema."
            )
        except Campanha.MultipleObjectsReturned:
            raise ValidationError(
                "ERRO: Existem múltiplas campanhas ativas. Contate o administrador."
            )

        # Prevenir duplicidade equivalente por participante (ex.: "10" vs "010") para o mesmo lojista

        ### Se de ruim remover isso aqui
        try:
            if self.user_id and self.lojista_id and self.numeroDocumento:
                def normalize_document_number(raw_value: str) -> str:
                    text = str(raw_value or "").strip()
                    digits_only = "".join(ch for ch in text if ch.isdigit())
                    if digits_only:
                        # Converte para inteiro para remover zeros à esquerda e retorna como string
                        try:
                            return str(int(digits_only))
                        except ValueError:
                            pass
                    # Fallback para casos não numéricos: normaliza espaços e caixa
                    return text.lower()

                current_norm = normalize_document_number(self.numeroDocumento)
                if current_norm:
                    candidatos = (
                        DocumentoFiscal.objects
                        .filter(user_id=self.user_id, lojista_id=self.lojista_id)
                        .exclude(pk=self.pk)
                        .only("id", "numeroDocumento")
                    )
                    for existente in candidatos:
                        if normalize_document_number(existente.numeroDocumento) == current_norm:
                            raise ValidationError({
                                "numeroDocumento": (
                                    f"Já existe para você um documento equivalente deste lojista: "
                                    f"{existente.numeroDocumento}. Verifique zeros à esquerda/formatação."
                                )
                            })
        except ValidationError:
            # Propaga validações de equivalência
            raise
        except Exception:
            # Nunca bloquear salvamento por erro inesperado nesta checagem
            pass

    # def get_cupons(self):
    #     cupons = 0
    #     if self.valorDocumento >= 50:
    #         multiplo = self.valorDocumento // 50
    #         if self.compradoMASTERCARD and self.compradoREDE:
    #             # Com cartão Elo na maquininha PagBank = 5 cupons por múltiplo de R$ 50
    #             cupons = multiplo * 5
    #         elif self.compradoREDE:
    #             # Pagando na maquininha da PagBank = 3 cupons por múltiplo de R$ 50
    #             cupons = multiplo * 3
    #         elif self.compradoMASTERCARD:
    #             # Pagando com cartão Elo = 5 cupons por múltiplo de R$ 50
    #             cupons = multiplo * 3
    #         else:
    
    
    # def get_cupons(self):
    #     # Só gera cupons se o documento estiver validado
    #     if self.status != StatusChoices.VALIDADO:
    #         return 0
            
    #     if self.valorDocumento < 50:
    #         return 0

    #     # Calcula cupons para valor pago na Cielo
    #     cupons_cielo = 0
    #     valor_cielo = self.valorCielo or 0
    #     if valor_cielo > 0:
    #         multiplo_cielo = int(valor_cielo // 50)
    #         cupons_cielo = multiplo_cielo * 3

    #     # Calcula cupons para valor restante
    #     valor_restante = self.valorDocumento - valor_cielo
    #     cupons_restante = 0
    #     if valor_restante > 0:
    #         multiplo_restante = int(valor_restante // 50)
    #         cupons_restante = multiplo_restante

    #     return cupons_cielo + cupons_restante



    def get_cupons(self):
        # Só gera cupons se o documento estiver validado
        if self.status != StatusChoices.VALIDADO:
            return 0
            
        if self.valorDocumento < 50:
            return 0

        valor_cielo = self.valorCielo or 0
        valor_outros = self.valorOutros or 0  # CORREÇÃO: Usar o campo valorOutros

        # 1. Cielo > Outros
        if valor_cielo > valor_outros:
            # Calcula cupons Cielo (triplicados)
            cupons_cielo = int(valor_cielo // 50)
            resto_cielo = valor_cielo % 50
            
            # Se resto Cielo < 50, soma aos outros
            if resto_cielo > 0:
                valor_outros_ajustado = valor_outros + resto_cielo
            else:
                valor_outros_ajustado = valor_outros
            
            # Calcula cupons Outros (normais)
            cupons_outros = int(valor_outros_ajustado // 50)
            
            # Total de cupons
            return (cupons_cielo * 3) + cupons_outros
            
        # 2. Cielo < Outros
        else:
            # Calcula cupons Outros (normais)
            cupons_outros = int(valor_outros // 50)
            resto_outros = valor_outros % 50
            
            # Se resto Outros < 50, soma ao Cielo
            if resto_outros > 0:
                valor_cielo_ajustado = valor_cielo + resto_outros
            else:
                valor_cielo_ajustado = valor_cielo
            
            # Calcula cupons Cielo (triplicados)
            cupons_cielo = int(valor_cielo_ajustado // 50)
            
            # Total de cupons
            return (cupons_cielo * 3) + cupons_outros
        



    def tem_cupons_impressos(self):
        """
        Verifica se o documento tem cupons impressos
        """
        return self.rel_cupom_doc.filter(impresso=True).exists()

    def send_email(self):
        body = "Estamos chegando no ultimo dia de campanha do Natal de Luz e Prêmios. \nPedimos que você cheque os seus documentos para verificar se está tudo certo, se não falta nenhuma foto dos seus cupons fiscal para que seus documentos sejam validados com sucesso e você possa concorrer para ganhar prêmios incriveis. \n \n Atenciosamente, \n \n Organização Natal de Luz e Prêmios.\n www.liquidateresina.com.br"
        subject = "Natal de Luz e Prêmios - Estamos chegando no último dia"
        email = EmailMessage(subject, body, to=[self.user.email])
        email.send()


class ReversaoImpressao(models.Model):
    """
    Modelo para rastrear reversões de impressão por usuário e documento.
    Permite controlar quantas vezes cada usuário pode reverter a impressão de um documento.
    """
    documento = models.ForeignKey(
        'DocumentoFiscal',
        on_delete=models.CASCADE,
        related_name='reversoes_impressao',
        verbose_name="Documento Fiscal"
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reversoes_realizadas',
        verbose_name="Usuário que realizou a reversão"
    )
    data_reversao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data da reversão"
    )
    cupons_removidos = models.PositiveIntegerField(
        verbose_name="Quantidade de cupons removidos"
    )
    motivo = models.TextField(
        blank=True,
        null=True,
        verbose_name="Motivo da reversão",
        help_text="Justificativa para a reversão"
    )

    class Meta:
        verbose_name = "Reversão de Impressão"
        verbose_name_plural = "Reversões de Impressão"
        # Removido unique_together para permitir múltiplas reversões para suporte
        ordering = ['-data_reversao']

    def __str__(self):
        return f"Reversão de {self.documento.numeroDocumento} por {self.usuario.username} em {self.data_reversao.strftime('%d/%m/%Y %H:%M')}"

    @classmethod
    def pode_reverter(cls, usuario, documento):
        """
        Verifica se o usuário pode reverter a impressão do documento.
        
        Regras:
        - Operador e Backoffice: apenas 1 vez por documento por grupo
        - Suporte: ilimitado
        - Outros grupos: não podem reverter
        """
        from participante.permissions import is_operador, is_backoffice, is_suporte
        
        # Suporte pode reverter ilimitado
        if is_suporte(usuario):
            return True, "Suporte pode reverter ilimitado"
        
        # Operador e Backoffice podem reverter apenas 1 vez por grupo
        if is_operador(usuario) or is_backoffice(usuario):
            # Buscar todos os usuários do mesmo grupo
            grupo_atual = usuario.groups.first()
            if grupo_atual:
                usuarios_do_grupo = grupo_atual.user_set.all()
                
                # Verificar se qualquer usuário do grupo já reverteu este documento
            ja_reverteu = cls.objects.filter(
                documento=documento,
                    usuario__in=usuarios_do_grupo
            ).exists()
            
            if ja_reverteu:
                    return False, f"Um {grupo_atual.name} já reverteu a impressão deste documento uma vez. Não é possível reverter novamente. Solicite ao suporte."
            else:
                    return True, f"Pode reverter (primeira vez para o grupo {grupo_atual.name})"
        
        # Outros grupos não podem reverter
        return False, "Seu grupo não tem permissão para reverter impressões."

    @classmethod
    def registrar_reversao(cls, usuario, documento, cupons_removidos, motivo):
        """
        Registra uma nova reversão de impressão.
        A validação de permissões deve ser feita antes de chamar este método.
        O motivo é obrigatório.
        """
        if not motivo or not motivo.strip():
            raise ValueError("Motivo da reversão é obrigatório")
        
        return cls.objects.create(
            documento=documento,
            usuario=usuario,
            cupons_removidos=cupons_removidos,
            motivo=motivo.strip()
        )


class CancelamentoImpressao(models.Model):
    """
    Modelo para rastrear cancelamentos de impressão por usuário e documento.
    Permite controlar quantas vezes cada usuário pode cancelar a impressão de um documento.
    """
    documento = models.ForeignKey(
        'DocumentoFiscal',
        on_delete=models.CASCADE,
        related_name='cancelamentos_impressao',
        verbose_name="Documento Fiscal"
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cancelamentos_realizados',
        verbose_name="Usuário que realizou o cancelamento"
    )
    data_cancelamento = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data do cancelamento"
    )
    motivo = models.TextField(
        blank=True,
        null=True,
        verbose_name="Motivo do cancelamento"
    )

    class Meta:
        verbose_name = "Cancelamento de Impressão"
        verbose_name_plural = "Cancelamentos de Impressão"
        ordering = ['-data_cancelamento']

    def __str__(self):
        return f"Cancelamento de {self.documento.numeroDocumento} por {self.usuario.username} em {self.data_cancelamento.strftime('%d/%m/%Y %H:%M')}"

    @classmethod
    def pode_cancelar(cls, usuario, documento):
        """
        Verifica se o usuário pode cancelar a impressão do documento.
        
        Regras:
        - Suporte e Superuser: ilimitado
        - Outros usuários: apenas 1 vez por documento
        """
        from participante.permissions import is_suporte
        
        # Suporte e Superuser podem cancelar ilimitado
        if is_suporte(usuario) or usuario.is_superuser:
            return True, "Pode cancelar ilimitado"
        
        # Verificar se já foi cancelado/revertido por qualquer usuário
        ja_cancelado = cls.objects.filter(documento=documento).exists()
        ja_revertido = ReversaoImpressao.objects.filter(documento=documento).exists()
        
        if ja_cancelado or ja_revertido:
            return False, "Este documento já foi cancelado/revertido uma vez. Solicite ao suporte."
        
        return True, "Pode cancelar (primeira vez para este documento)"

    @classmethod
    def registrar_cancelamento(cls, usuario, documento, motivo):
        """
        Registra um novo cancelamento de impressão.
        A validação de permissões deve ser feita antes de chamar este método.
        """
        if not motivo or not motivo.strip():
            raise ValueError("Motivo do cancelamento é obrigatório")
        
        return cls.objects.create(
            documento=documento,
            usuario=usuario,
            motivo=motivo.strip()
        )


