from django.db import models
from django.conf import settings


class SorteioResultado(models.Model):
    cupom = models.ForeignKey('cupom.Cupom', on_delete=models.PROTECT, related_name='resultados_sorteio')
    participante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sorteios_vencidos')
    cpf = models.CharField(max_length=14)
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sorteios_realizados')
    valido = models.BooleanField(default=True)
    motivo_invalidacao = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Resultado de Sorteio'
        verbose_name_plural = 'Resultados de Sorteio'
        constraints = [
            models.UniqueConstraint(fields=['cupom'], name='unique_resultado_por_cupom')
        ]

    def __str__(self):
        return f"Sorteio #{self.id} - Cupom {self.cupom_id} - {self.cpf}"

# Create your models here.
