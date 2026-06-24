from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse

from participante.models import DocumentoFiscal, PostoTrabalho
import json
from django.utils import timezone


# Create your models here.
class Cupom(models.Model):
    user = models.ForeignKey(User, related_name="rel_user", on_delete=models.PROTECT)
    documentoFiscal = models.ForeignKey(
        DocumentoFiscal, related_name="rel_cupom_doc", on_delete=models.PROTECT
    )
    dataCriacao = models.DateTimeField(auto_now_add=True)
    dataImpressao = models.DateTimeField(null=True, blank=True)
    impresso = models.BooleanField(default=False)
    em_impressao = models.BooleanField(default=False)
    tentativa_impressao = models.DateTimeField(null=True, blank=True)
    falhas_impressao = models.IntegerField(default=0)
    reimpresso_em = models.DateTimeField(null=True, blank=True)
    operador = models.ForeignKey(
        User,
        related_name="rel_operador",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    posto_trabalho = models.ForeignKey(
        "participante.PostoTrabalho",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Posto onde foi impresso",
        help_text="Local onde o cupom foi impresso",
    )

    def __str__(self):
        return "Cupom número: {}".format(self.id)

    def get_absolute_url(self):
        return reverse("cupom:details", args=[str(self.numeroCupom)])

    def get_info(self):
        """
        Retorna informações do cupom em formato de texto simples para o QR code
        """
        info = (
            f"Cupom ID: {self.id}\n"
            f"Documento ID: {self.documentoFiscal.id}\n"
            f"Participante: {self.user.profile.nome}\n"
            f"CPF: {self.user.profile.CPF}\n"
            f"Loja: {self.documentoFiscal.lojista}\n"
            f"Data Compra: {self.documentoFiscal.dataDocumento.strftime('%d/%m/%Y')}\n"
            f"Valor: R$ {self.documentoFiscal.valorDocumento}"
        )
        return info

    def registrar_falha_impressao(self):
        """
        Registra uma falha na impressão e incrementa o contador
        """
        self.falhas_impressao += 1
        self.em_impressao = False
        self.save(update_fields=["falhas_impressao", "em_impressao"])

    def confirmar_impressao(self, posto_trabalho=None):
        """
        Confirma que a impressão foi bem sucedida
        """
        now = timezone.now()
        if not self.impresso:
            self.dataImpressao = now
            self.impresso = True
            if posto_trabalho:
                self.posto_trabalho = posto_trabalho
        else:
            self.reimpresso_em = now
        self.em_impressao = False
        fields_to_update = [
            "dataImpressao",
            "impresso",
            "reimpresso_em",
            "em_impressao",
        ]
        if posto_trabalho:
            fields_to_update.append("posto_trabalho")
        self.save(update_fields=fields_to_update)

    class Meta:
        verbose_name = "Cupom"
        verbose_name_plural = "Cupons"
