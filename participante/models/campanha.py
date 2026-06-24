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

class Campanha(models.Model):
    nome = models.CharField(max_length=250)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    instagram = models.CharField(max_length=250, null=True)
    site = models.CharField(max_length=250, null=True)
    whatsapp = models.CharField(max_length=250, null=True)
    criada_em = models.DateTimeField(auto_now=True)
    finalizada_em = models.DateTimeField(null=True, blank=True)
    finalizada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="registro_campanha",
        null=True,
        blank=True,
    )
    ativa = models.BooleanField(default=True)

    # Campos de Personalização Visual
    logo_principal = models.ImageField(
        upload_to="campanhas/logos/",
        null=True,
        blank=True,
        help_text="Logo que aparecerá na barra de navegação.",
        storage=get_storage()  # Usa storage explícito para garantir S3 quando USE_S3=True
    )
    banner_hero = models.ImageField(
        upload_to="campanhas/banners/",
        null=True,
        blank=True,
        help_text="Imagem principal da página inicial.",
        storage=get_storage()  # Usa storage explícito para garantir S3 quando USE_S3=True
    )
    cor_primaria = models.CharField(
        max_length=7,
        default="#2B5C3F",
        help_text="Cor principal para botões e links (formato HEX, ex: #FF5733).",
    )
    cor_hover = models.CharField(
        max_length=7,
        default="#1A4A2E",
        help_text="Cor para o estado 'hover' dos botões (formato HEX).",
    )

    class Meta:
        permissions = [("finalizar_campanha", "Pode finalizar a campanha")]

    def __str__(self):
        return self.nome

    def verificar_inativacao(self):
        if self.data_fim < timezone.now().date() and self.ativa:
            self.ativa = False

    def esta_ativa(self):
        """Retorna True se a campanha está ativa e dentro do prazo."""
        return self.ativa and (self.data_inicio <= now().date() <= self.data_fim)

    def pode_finalizar(self):
        logger = logging.getLogger(__name__)
        logger.info("Verificando se a campanha pode ser finalizada.")
        from participante.models import DocumentoFiscal
        from cupom.models import Cupom

        documentos_pendentes = DocumentoFiscal.objects.filter(pendente=True).exists()
        cupons_pendentes = Cupom.objects.filter(impresso=False).exists()

        if documentos_pendentes or cupons_pendentes:
            return False

        return timezone.now().date() >= self.data_fim


