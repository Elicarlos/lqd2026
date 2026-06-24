from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from localflavor.br.br_states import STATE_CHOICES
from localflavor.br.forms import BRCNPJField, BRCPFField, BRZipCodeField
from decimal import Decimal, InvalidOperation
import logging
from lojista.models import Lojista
from participante.models import DocumentoFiscal, Profile, Campanha  # Adicionado Campanha


class UserAddCoupom(forms.ModelForm):
    numeroDoCupom = forms.CharField(label="Numero do cupom")
    valorDoCupom = forms.DecimalField(label="Valor do cupom")


