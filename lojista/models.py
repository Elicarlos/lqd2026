from django.db import models
from django.conf import settings
from django.forms import ValidationError
from django.urls import reverse
import datetime
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


def validate_promotional_period(value):
    promotion_start = datetime.date(2024, 6, 28)
    promotion_end = datetime.date(2024, 7, 7)

    if not (promotion_start <= value <= promotion_end):
        raise ValidationError(
            _("A data do documento deve estar entre %(start)s e %(end)s"),
            params={"start": promotion_start, "end": promotion_end},
        )

class RamoAtividade(models.Model):
    """
    Model representando o ramo de atividade.
    """

    atividade = models.CharField(
        max_length=80,
        help_text="Informe o Ramo de Atividade. (exemplo: alimentação, vestuário, restaurante, etc.)",
    )
    dataCadastro = models.DateTimeField(
        verbose_name="Cadastrado em", auto_now_add=True, editable=False
    )  # nao vai aparecer na tela
    cadastrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Cadastrado Por",
        editable=False,
    )

    ativo = models.BooleanField(default=True)

    def clean(self):
        # Padroniza o campo de texto para maiúsculas
        if self.atividade:
            self.atividade = self.atividade.upper()

    def save(self, *args, **kwargs):
        self.clean()  # Chama o método clean antes de salvar
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["atividade"]
        verbose_name = "ramo de Atividade"
        verbose_name_plural = "ramos de Atividades"

    def __str__(self):
        """
        String representando o Model object (in Admin site etc.)
        """
        return self.atividade

class Localizacao(models.Model):
    nome = models.CharField(max_length=250)
    descricao = models.TextField(blank=True)
    cadastrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Cadastrado Por",
        editable=False,
    )

    def clean(self):
        # Padroniza os campos de texto para maiúsculas
        if self.nome:
            self.nome = self.nome.upper()
        if self.descricao:
            self.descricao = self.descricao.upper()

    def save(self, *args, **kwargs):
        # Não chama clean() aqui pois o Django já chama automaticamente
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome

class Lojista(models.Model):
    STATUS_CHOICES = [
        ("Pendente", "Pendente"),
        ("Sim", "Sim"),
        ("Não", "Não"),
        ("Inativo", "Inativo"),
    ]
    CNPJLojista = models.CharField(
        verbose_name="CNPJ do Lojista*",
        max_length=18,
        blank=False,
        null=True,
        unique=True,
        help_text="ex. 00.000.000/0000-00",
    )
    IELojista = models.CharField(
        verbose_name="Inscrição Estadual",
        max_length=14,
        blank=True,
        unique=False,
        null=True,
    )
    razaoLojista = models.CharField(
        verbose_name="Razão Social*",
        max_length=200,
        blank=True,
        null=True,
        help_text="Razão Social",
    )
    fantasiaLojista = models.CharField(
        verbose_name="Nome Fantasia*",
        max_length=200,
        blank=False,
        help_text="Nome Fantasia",
    )
    ramoAtividade = models.ForeignKey(
        "RamoAtividade",
        verbose_name="Ramo de Atividade*",
        on_delete=models.SET_NULL,
        null=True,
    )
    localizacao = models.ForeignKey(
        Localizacao, on_delete=models.SET_NULL, null=True, blank=True
    )
    dataCadastro = models.DateTimeField(
        verbose_name="Cadastrado em", auto_now_add=True, editable=False
    )  # nao vai aparecer na tela
    cadastrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Cadastrado Por",
        editable=False,
        related_name="lojistas_cadastrados",
    )
    endereco = models.CharField(verbose_name="Endereço", max_length=150, blank=True)
    telefone = models.CharField(
        verbose_name="Telefone",
        max_length=150,
        blank=True,
        help_text="ex. (85)3212-0000",
    )
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Autorizado por",
        related_name="lojistas_autorizados",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pendente")
    lojista_cielo = models.BooleanField(default=False, verbose_name="Lojista Cielo")

    def clean(self):
        # Padroniza os campos de texto para maiúsculas
        if self.razaoLojista:
            self.razaoLojista = self.razaoLojista.upper()
        if self.fantasiaLojista:
            self.fantasiaLojista = self.fantasiaLojista.upper()
        if self.endereco:
            self.endereco = self.endereco.upper()
        # Formatar CNPJ
        if self.CNPJLojista:
            # Limpar CNPJ (remover caracteres não numéricos)
            cnpj_limpo = ''.join(filter(str.isdigit, self.CNPJLojista))
            
            # Validar se tem 14 dígitos
            if len(cnpj_limpo) != 14:
                raise ValidationError("CNPJ deve ter 14 dígitos.")
            
            # Aplicar máscara (formato XX.XXX.XXX/XXXX-XX)
            self.CNPJLojista = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"  # Remove espaços extras
        if self.IELojista:
            self.IELojista = self.IELojista.strip()  # Remove espaços extras
        if self.telefone:
            self.telefone = self.telefone.strip()  # Remove espaços extras

    def save(self, *args, **kwargs):
        self.clean()  # Chama o método clean antes de salvar
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["fantasiaLojista"]
        verbose_name = "lojista"
        verbose_name_plural = "lojistas"

    def __str__(self):
        """
        String representando o Objeto Participante.
        """
        return self.fantasiaLojista

    def get_absolute_url(self):
        return reverse("lojista:editlojista", args=[self.id])

    def atualizar_status(self, novo_status_id, usuario):
        if self.is_cielo:
            self.status = "Sim"
            self.autorizado_por = None
        else:
            novo_status = novo_status_id
            self.status = novo_status
            self.autorizado_por = usuario
        self.save()

class AdesaoLojista(models.Model):
    STATUS_CHOICES = [
        ("Pendente", "Pendente"),
        ("Sim", "Sim"),
        ("Inativo", "Inativo"),
        ("Atendido sem Venda", "Atendido sem Venda"),
        ("Nao Atendido", "Não Atendido"),
    ]
    cnpj = models.CharField(
        verbose_name="Cnpj do Lojista",
        max_length=18,
        blank=False,
        null=True,
        unique=True,
        help_text="ex. 00.000.000/0000-00",
    )
    razao_social = models.CharField(
        verbose_name="Razão Social", max_length=250, blank=False, null=True
    )
    fantasia = models.CharField(
        verbose_name="Nome Fantasia", max_length=250, blank=False, null=True
    )
    email = models.EmailField(
        verbose_name="Email", max_length=250, null=True, blank=False
    )
    telefone = models.CharField(
        verbose_name="Telefone",
        max_length=20,
        blank=False,
        null=True,
        help_text="(xx) xxxxx - xxxx",
    )
    data_contato = models.DateTimeField(
        verbose_name="Data do contato",
        null=True,
        blank=True,
        help_text="Data e hora em que o vendedor entrou em contato ",
    )
    atendido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Atendido por",
    )
    atendido = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Pendente", null=True, blank=True
    )
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="status_modificado_por",
    )

    def clean(self):
        # Padroniza os campos de texto para maiúsculas
        if self.razao_social:
            self.razao_social = self.razao_social.upper()
        if self.fantasia:
            self.fantasia = self.fantasia.upper()
        if self.email:
            self.email = self.email.lower()  # Email é melhor em minúsculas
        if self.cnpj:
            self.cnpj = self.cnpj.strip()  # Remove espaços extras
        if self.telefone:
            self.telefone = self.telefone.strip()  # Remove espaços extras

    def save(self, *args, **kwargs):
        self.clean()  # Chama o método clean antes de salvar
        super().save(*args, **kwargs)

    def atualizar_status(self, novo_status_id, usuario):
        novo_status = novo_status_id
        self.status = novo_status
        self.autorizado_por = usuario
        self.save()

    def __str__(self):
        return self.fantasia or self.razao_social

    class Meta:
        verbose_name = "Adesão de Lojista"
        verbose_name_plural = "Adesões de Lojistas"

class AutorizacaoLojista(models.Model):
    """
    Modelo para rastrear autorizações de lojistas
    """
    lojista = models.ForeignKey(Lojista, on_delete=models.CASCADE, related_name='autorizacoes')
    autorizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='autorizacoes_feitas')
    status_anterior = models.CharField(max_length=20, blank=True)
    status_novo = models.CharField(max_length=20)
    data_autorizacao = models.DateTimeField(auto_now_add=True)
    observacao = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Autorização de Lojista"
        verbose_name_plural = "Autorizações de Lojistas"
        ordering = ['-data_autorizacao']
    
    def __str__(self):
        return f"{self.lojista.fantasiaLojista} - {self.status_novo} por {self.autorizado_por}"
