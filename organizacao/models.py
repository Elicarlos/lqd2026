from django.db import models
from django.core.exceptions import ValidationError


class OrigemChoices(models.TextChoices):
    CDL = 'CDL', 'CDL'
    SOLVE = 'SOLVE', 'Solve'
    OUTROS = 'OUTROS', 'Outros'


class PessoaOrganizacao(models.Model):
    nome = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14, unique=True, help_text="000.000.000-00")
    origem = models.CharField(max_length=10, choices=OrigemChoices.choices, default=OrigemChoices.CDL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pessoa da Organização'
        verbose_name_plural = 'Pessoas da Organização'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['cpf']),
            models.Index(fields=['origem']),
        ]

    def __str__(self) -> str:
        return f"{self.nome} ({self.cpf})"

    @staticmethod
    def _normalize_cpf(raw: str) -> str:
        return ''.join(ch for ch in (raw or '') if ch.isdigit())

    def clean(self):
        super().clean()
        cpf_digits = self._normalize_cpf(self.cpf)
        if len(cpf_digits) not in (11,):
            raise ValidationError({'cpf': 'CPF deve conter 11 dígitos.'})
        # Validação algorítmica do CPF
        if not self._cpf_is_valid(cpf_digits):
            raise ValidationError({'cpf': 'CPF inválido.'})
        # Armazena com formatação padrão 000.000.000-00
        self.cpf = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"

        # Garantir unicidade por dígitos (independente da máscara)
        existing = (
            PessoaOrganizacao.objects
            .exclude(pk=self.pk)
            .values_list('cpf', flat=True)
        )
        for cpf_existing in existing:
            if self._normalize_cpf(cpf_existing) == cpf_digits:
                raise ValidationError({'cpf': 'Já existe uma pessoa com este CPF.'})

    def save(self, *args, **kwargs):
        # Normaliza e aplica máscara antes de salvar
        cpf_digits = self._normalize_cpf(self.cpf)
        if cpf_digits:
            if len(cpf_digits) == 11:
                self.cpf = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"
        super().save(*args, **kwargs)

    @staticmethod
    def _cpf_is_valid(cpf_digits: str) -> bool:
        # Regras básicas
        if not cpf_digits or len(cpf_digits) != 11:
            return False
        if cpf_digits == cpf_digits[0] * 11:
            return False
        # Primeiro dígito verificador
        soma = sum(int(cpf_digits[i]) * (10 - i) for i in range(9))
        resto = (soma * 10) % 11
        dv1 = 0 if resto == 10 else resto
        if dv1 != int(cpf_digits[9]):
            return False
        # Segundo dígito verificador
        soma = sum(int(cpf_digits[i]) * (11 - i) for i in range(10))
        resto = (soma * 10) % 11
        dv2 = 0 if resto == 10 else resto
        return dv2 == int(cpf_digits[10])


