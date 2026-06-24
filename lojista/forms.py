from django import forms
from django.core.exceptions import ValidationError
from .models import Lojista, RamoAtividade, AdesaoLojista, Localizacao
from localflavor.br.forms import BRCNPJField


class LojistaRegistrationForm(forms.ModelForm):
    CNPJLojista = forms.CharField(
        label="CNPJ*",
        required=True,
        max_length=18,
        widget=forms.TextInput(
            attrs={
                "class": "form-control cnpj-mask",
                "placeholder": "00.000.000/0000-00"
            }
        ),
    )
    IELojista = forms.CharField(
        label="Inscrição Estadual",
        required=False,
        max_length=14,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Digite a Inscrição Estadual",
            }
        ),
    )
    razaoLojista = forms.CharField(
        label="Razão Social*",
        required=True,
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Digite a Razão Social"
            }
        ),
    )
    fantasiaLojista = forms.CharField(
        label="Nome Fantasia*",
        required=True,
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Digite o Nome Fantasia"
            }
        ),
    )
    endereco = forms.CharField(
        label="Endereço",
        required=False,
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Digite o endereço completo",
            }
        ),
    )
    telefone = forms.CharField(
        label="Telefone",
        required=False,
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control phone-mask",
                "placeholder": "(00) 00000-0000",
            }
        ),
    )
    ramoAtividade = forms.ModelChoiceField(
        queryset=RamoAtividade.objects.all(),
        required=True,
        label="Ramo de Atividade*",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    localizacao = forms.ModelChoiceField(
        queryset=Localizacao.objects.all(),
        required=False,
        label="Localização",
        help_text="Selecione a localização associada ao lojista",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    lojista_cielo = forms.BooleanField(
        required=False,
        label="Lojista Cielo",
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
            }
        ),
    )

    class Meta:
        model = Lojista
        fields = [
            "CNPJLojista",
            "IELojista",
            "razaoLojista",
            "fantasiaLojista",
            "endereco",
            "telefone",
            "ramoAtividade",
            "localizacao",
            "lojista_cielo",
        ]
        widgets = {
            "cadastrado_por": forms.HiddenInput,
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.status:
            instance.status = "Pendente"
        if commit:
            instance.save()
        return instance

    def clean_CNPJLojista(self):
        CNPJLojista = self.cleaned_data.get("CNPJLojista")
        if (
            Lojista.objects.filter(CNPJLojista=CNPJLojista)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise ValidationError("Já existe um lojista com este CNPJ cadastrado.")
        return CNPJLojista

class RamoAtividadeRegistrationForm(forms.ModelForm):

    class Meta:
        model = RamoAtividade
        fields = ["atividade", "ativo"]
        widgets = {
            "atividade": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Digite o nome da atividade"
                }
            ),
            "ativo": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),
        }

class LocalizacaoRegistrationForm(forms.ModelForm):

    class Meta:
        model = Localizacao
        fields = ["nome", "descricao"]
        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Digite o nome da localização"
                }
            ),
            "descricao": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Descreva a localização ou região...",
                    "rows": "4"
                }
            ),
        }

class FormLojistaAdesao(forms.ModelForm):
    class Meta:
        model = AdesaoLojista
        fields = ["fantasia", "razao_social", "email", "telefone", "cnpj"]
        widgets = {
            "fantasia": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nome da Loja"}
            ),
            "razao_social": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Razão Social"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "E-mail de contato"}
            ),
            "telefone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "(00) 00000-0000"}
            ),
            "cnpj": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "00.000.000/0000-00"}
            ),
        }

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get("cnpj")
        if cnpj and AdesaoLojista.objects.filter(cnpj=cnpj).exists():
            raise forms.ValidationError("CNPJ já cadastrado.")
        return cnpj
