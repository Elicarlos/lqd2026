from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from localflavor.br.br_states import STATE_CHOICES
from localflavor.br.forms import BRCNPJField, BRCPFField, BRZipCodeField
from decimal import Decimal, InvalidOperation
import logging
from lojista.models import Lojista
from participante.models import DocumentoFiscal, Profile, Campanha  # Adicionado Campanha


# Novo formulário para o modelo Campanha
class CampanhaAdminForm(forms.ModelForm):
    class Meta:
        model = Campanha
        fields = "__all__"  # Inclui todos os campos do modelo Campanha
        widgets = {
            "cor_primaria": forms.TextInput(attrs={"type": "color"}),
            "cor_hover": forms.TextInput(attrs={"type": "color"}),
        }


