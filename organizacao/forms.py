from django import forms
from localflavor.br.forms import BRCPFField
from .models import PessoaOrganizacao


class PessoaOrganizacaoForm(forms.ModelForm):
    cpf = BRCPFField(
        label="CPF",
        widget=forms.TextInput(attrs={
            "class": "form-control cpf-mask",
            "placeholder": "000.000.000-00",
            "autocomplete": "off",
        })
    )
    class Meta:
        model = PessoaOrganizacao
        fields = ["nome", "cpf", "origem"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nome completo"}),
            "origem": forms.Select(attrs={"class": "form-select"}),
        }


