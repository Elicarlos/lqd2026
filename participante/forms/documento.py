from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from localflavor.br.br_states import STATE_CHOICES
from localflavor.br.forms import BRCNPJField, BRCPFField, BRZipCodeField
from decimal import Decimal, InvalidOperation
import logging
from lojista.models import Lojista
from participante.models import DocumentoFiscal, Profile, Campanha  # Adicionado Campanha


# Função auxiliar para validação do valorCielo
def clean_valor_cielo_helper(valor_cielo, comprado_cielo):
    logger = logging.getLogger(__name__)
    
    logger.info(f"Validando valorCielo: valor={valor_cielo}, comprado_cielo={comprado_cielo}")
    
    # Se não comprou na Cielo, o valor deve ser 0
    if not comprado_cielo:
        logger.info("Não comprou na Cielo, retornando 0")
        return 0
    
    # Se comprou na Cielo mas não informou valor, retorna 0
    if valor_cielo is None or valor_cielo == '' or str(valor_cielo).strip() == '':
        logger.info("Valor vazio ou None, retornando 0")
        return 0
    
    # Se o valor é uma string vazia ou apenas espaços
    if isinstance(valor_cielo, str) and valor_cielo.strip() == '':
        logger.info("String vazia, retornando 0")
        return 0
    
    logger.info(f"Retornando valor original: {valor_cielo}")
    return valor_cielo


class UserAddFiscalDocForm(forms.ModelForm):
    lojista_cnpj = BRCNPJField(
        label="CNPJ da loja*",
        required=True,
        max_length=18,
        widget=forms.TextInput(
            attrs={
                "class": "form-control cnpj",
                "autocomplete": "off",
                "placeholder": "00.000.000/0000-00",
            }
        ),
    )
    vendedor = forms.CharField(
        label="Vendedor",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "placeholder": "Nome do vendedor (opcional)",
            }
        ),
    )
    numeroDocumento = forms.CharField(
        label="Número do documento*",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "placeholder": "Número da nota fiscal",
            }
        ),
    )
    dataDocumento = forms.DateField(
        label="Data*",
        required=True,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "autocomplete": "off",
            }
        ),
    )
    valorCielo = forms.CharField(
        label="Valor pago na Cielo",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control money-mask",
                "autocomplete": "off",
                "placeholder": "R$ 0,00",
                "inputmode": "decimal",
            }
        ),
    )
    valorOutros = forms.CharField(
        label="Valor pago em outros métodos",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control money-mask",
                "autocomplete": "off",
                "placeholder": "R$ 0,00",
                "inputmode": "decimal",
            }
        ),
    )
    valorDocumento = forms.CharField(
        label="Valor Total do Documento*",
        required=False,
        widget=forms.HiddenInput(
            attrs={
                "id": "id_valorDocumento",
            }
        ),
    )
    photo = forms.FileField(
        label="Documento Fiscal*",
        required=True,
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*,.pdf",
            }
        ),
    )
    photo2 = forms.FileField(
        label="Comprovante do Cartão",
        required=False,
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*,.pdf",
            }
        ),
    )

    class Meta:
        model = DocumentoFiscal
        fields = (
            "lojista_cnpj",
            "vendedor",
            "numeroDocumento",
            "dataDocumento",
            "valorCielo",
            "valorOutros",
            "valorDocumento",
            "photo",
            "photo2",
        )
        widgets = {
            "user": forms.HiddenInput,
            "pendente": forms.HiddenInput,
            "observacao": forms.HiddenInput,
            "valorREDE": forms.HiddenInput,
            "valorMASTERCARD": forms.HiddenInput,
            "valorVirtual": forms.HiddenInput,
        }

    @staticmethod
    def _parse_money(value):
        from decimal import Decimal, InvalidOperation
        if value in (None, ""):
            return Decimal('0')
        if isinstance(value, (int, float, Decimal)):
            return Decimal(str(value))
        s = str(value)
        s = s.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        try:
            return Decimal(s)
        except (InvalidOperation, ValueError):
            return Decimal('0')

    def clean_valorCielo(self):
        return self._parse_money(self.data.get('valorCielo'))

    def clean_valorOutros(self):
        return self._parse_money(self.data.get('valorOutros'))

    def clean(self):
        import logging
        logger = logging.getLogger(__name__)
        from decimal import Decimal
        cleaned_data = super().clean()
        
        logger.info("[UserAddFiscalDocForm] Iniciando validação")
        logger.debug(f"[UserAddFiscalDocForm] POST raw valorCielo='{self.data.get('valorCielo')}', valorOutros='{self.data.get('valorOutros')}', valorDocumento(hidden)='{self.data.get('valorDocumento')}'")
        
        # Limpa o número do documento
        numeroDocumento = cleaned_data.get("numeroDocumento", "").strip()
        if not numeroDocumento:
            self.add_error("numeroDocumento", "Este campo é obrigatório.")
            return cleaned_data
        
        cleaned_data["numeroDocumento"] = numeroDocumento
        logger.info(f"Número do documento: {numeroDocumento}")

        # Validação da data do documento
        dataDocumento = cleaned_data.get("dataDocumento")
        if not dataDocumento:
            self.add_error("dataDocumento", "Este campo é obrigatório.")
            return cleaned_data

        # Normaliza valores e calcula total
        valorCielo = self._parse_money(self.data.get('valorCielo'))
        valorOutros = self._parse_money(self.data.get('valorOutros'))
        valorDocumento = (valorCielo or Decimal('0')) + (valorOutros or Decimal('0'))
        cleaned_data['valorCielo'] = valorCielo
        cleaned_data['valorOutros'] = valorOutros
        cleaned_data['valorDocumento'] = valorDocumento
        logger.debug(f"[UserAddFiscalDocForm] Valores normalizados -> Cielo={valorCielo}, Outros={valorOutros}, Total={valorDocumento}")
        
        logger.info(f"Valores recebidos - Total: {valorDocumento}")
        
        # Outros campos
        lojista_cnpj = cleaned_data.get("lojista_cnpj")
        
        # Validação do CNPJ do lojista
        if not lojista_cnpj:
            self.add_error("lojista_cnpj", "Este campo é obrigatório.")
            return cleaned_data
            
        if not Lojista.objects.filter(CNPJLojista=lojista_cnpj).exists():
            self.add_error(
                "lojista_cnpj", "Lojista com o CNPJ fornecido não existe."
            )

        # Validação de documento duplicado
        if numeroDocumento and lojista_cnpj:
            existing_doc = DocumentoFiscal.objects.filter(
                lojista__CNPJLojista=lojista_cnpj,
                numeroDocumento__iexact=numeroDocumento,
            ).first()
            if existing_doc:
                error_message = (
                    "Este documento já foi registrado anteriormente no sistema. "
                    "Por favor, verifique o número do documento e tente novamente."
                )
                self.add_error(
                    "numeroDocumento",
                    error_message,
                )

        # Validação dos valores monetários
        if valorDocumento <= 0:
            logger.error(f"Valor total inválido: {valorDocumento} <= 0")
            self.add_error(
                "valorDocumento",
                "O valor total do documento deve ser maior que zero."
            )
            return cleaned_data
            
        if valorDocumento < Decimal('50.00'):
            logger.error(f"Valor total abaixo do mínimo: {valorDocumento} < 50.00")
            self.add_error(
                "valorDocumento",
                "O valor do documento deve ser de no mínimo R$ 50,00."
            )
            return cleaned_data

        return cleaned_data


class UserAddFiscalDocFormSuperuser(UserAddFiscalDocForm):
    photo = forms.FileField(label="Documento fiscal", required=False)
    photo2 = forms.FileField(label="Comprovante do cartão", required=False)


class UserAddFiscalDocFormOperador(forms.ModelForm):
    """
    Formulário específico para operadores que estão vendo o documento fisicamente.
    Não requer upload de fotos.
    """
    lojista_cnpj = BRCNPJField(
        label="CNPJ da loja*",
        required=True,
        max_length=18,
        widget=forms.TextInput(
            attrs={
                "class": "form-control cnpj",
                "autocomplete": "off",
                "placeholder": "00.000.000/0000-00",
            }
        ),
    )
    vendedor = forms.CharField(
        label="Vendedor",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "placeholder": "Nome do vendedor (opcional)",
            }
        ),
    )
    numeroDocumento = forms.CharField(
        label="Número do documento*",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "placeholder": "Número da nota fiscal",
            }
        ),
    )
    dataDocumento = forms.DateField(
        label="Data*",
        required=True,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "autocomplete": "off",
            }
        ),
    )
    valorCielo = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        localize=True,
        label="Valor pago na Cielo",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control money-mask",
                "autocomplete": "off",
                "placeholder": "R$ 0,00",
            }
        ),
    )
    valorOutros = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        localize=True,
        label="Valor pago em outros métodos",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control money-mask",
                "autocomplete": "off",
                "placeholder": "R$ 0,00",
            }
        ),
    )
    valorDocumento = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        localize=True,
        label="Valor Total do Documento*",
        widget=forms.HiddenInput(
            attrs={
                "id": "id_valorDocumento",
            }
        ),
    )

    class Meta:
        model = DocumentoFiscal
        fields = (
            "lojista_cnpj",
            "vendedor",
            "numeroDocumento",
            "dataDocumento",
            "valorCielo",
            "valorOutros",
            "valorDocumento",
        )
        widgets = {
            "user": forms.HiddenInput,
            "pendente": forms.HiddenInput,
            "observacao": forms.HiddenInput,
            "valorREDE": forms.HiddenInput,
            "valorMASTERCARD": forms.HiddenInput,
            "valorVirtual": forms.HiddenInput,
        }

    def clean(self):
        import logging
        logger = logging.getLogger(__name__)
        from decimal import Decimal
        cleaned_data = super().clean()
        
        logger.info("Iniciando validação do formulário de operador")
        logger.info(f"Dados recebidos: {self.data}")
        logger.info(f"Cleaned data: {cleaned_data}")
        
        # Limpa o número do documento
        numeroDocumento = cleaned_data.get("numeroDocumento", "").strip()
        if not numeroDocumento:
            self.add_error("numeroDocumento", "Este campo é obrigatório.")
            return cleaned_data
        
        cleaned_data["numeroDocumento"] = numeroDocumento
        logger.info(f"Número do documento: {numeroDocumento}")

        # Validação da data do documento
        dataDocumento = cleaned_data.get("dataDocumento")
        if not dataDocumento:
            self.add_error("dataDocumento", "Este campo é obrigatório.")
            return cleaned_data

        # Garante que todos os valores monetários são Decimal
        valorDocumento = cleaned_data.get("valorDocumento") or Decimal('0')
        
        logger.info(f"Valores recebidos - Total: {valorDocumento}")
        
        # Outros campos
        lojista_cnpj = cleaned_data.get("lojista_cnpj")
        
        # Validação do CNPJ do lojista
        if not lojista_cnpj:
            self.add_error("lojista_cnpj", "Este campo é obrigatório.")
            return cleaned_data
            
        if not Lojista.objects.filter(CNPJLojista=lojista_cnpj).exists():
            self.add_error(
                "lojista_cnpj", "Lojista com o CNPJ fornecido não existe."
            )

        # Validação de documento duplicado
        if numeroDocumento and lojista_cnpj:
            existing_doc = DocumentoFiscal.objects.filter(
                lojista__CNPJLojista=lojista_cnpj,
                numeroDocumento__iexact=numeroDocumento,
            ).first()
            if existing_doc:
                error_message = (
                    "Este documento já foi registrado anteriormente no sistema. "
                    "Por favor, verifique o número do documento e tente novamente."
                )
                self.add_error(
                    "numeroDocumento",
                    error_message,
                )

        # Validação dos valores monetários
        if valorDocumento <= 0:
            logger.error(f"Valor total inválido: {valorDocumento} <= 0")
            self.add_error(
                "valorDocumento",
                "O valor total do documento deve ser maior que zero."
            )
            return cleaned_data
            
        if valorDocumento < Decimal('50.00'):
            logger.error(f"Valor total abaixo do mínimo: {valorDocumento} < 50.00")
            self.add_error(
                "valorDocumento",
                "O valor do documento deve ser de no mínimo R$ 50,00."
            )
            return cleaned_data

        return cleaned_data

    def clean_valorCielo(self):
        valor_cielo = self.cleaned_data.get('valorCielo')
        logger = logging.getLogger(__name__)
        logger.info(f"Validando valorCielo no UserAddFiscalDocFormOperador: {valor_cielo}")
        
        # Se o valor é None ou vazio, retorna 0
        if valor_cielo is None or valor_cielo == '' or str(valor_cielo).strip() == '':
            logger.info("Valor vazio, retornando 0")
            return 0
        
        # Se o valor é uma string vazia ou apenas espaços
        if isinstance(valor_cielo, str) and valor_cielo.strip() == '':
            logger.info("String vazia, retornando 0")
            return 0
        
        logger.info(f"Retornando valor original: {valor_cielo}")
        return valor_cielo

    def clean_valorOutros(self):
        valor_outros = self.cleaned_data.get('valorOutros')
        logger = logging.getLogger(__name__)
        logger.info(f"Validando valorOutros no UserAddFiscalDocFormOperador: {valor_outros}")
        
        # Se o valor é None ou vazio, retorna 0
        if valor_outros is None or valor_outros == '' or str(valor_outros).strip() == '':
            logger.info("Valor vazio, retornando 0")
            return 0
        
        # Se o valor é uma string vazia ou apenas espaços
        if isinstance(valor_outros, str) and valor_outros.strip() == '':
            logger.info("String vazia, retornando 0")
            return 0
        
        logger.info(f"Retornando valor original: {valor_outros}")
        return valor_outros


class DocumentoFiscalEditFormOp(forms.ModelForm):
    lojista_cnpj = forms.CharField(
        label="CNPJ da Loja",
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={
            "class": "form-control cnpj-mask bg-light",
            "placeholder": "00.000.000/0000-00"
        })
    )
    
    # Campos de checkbox para métodos de pagamento
    compradoREDE = forms.BooleanField(
        label="Comprou com REDE",
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
            "id": "id_compradoREDE"
        })
    )
    
    compradoMASTERCARD = forms.BooleanField(
        label="Comprou com MASTERCARD",
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
            "id": "id_compradoMASTERCARD"
        })
    )
    
    compradoCielo = forms.BooleanField(
        label="Comprou com Cielo",
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
            "id": "id_compradoCielo"
        })
    )
    
    # Campo status como hidden para manter o valor atual
    status = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={
            "id": "id_status"
        })
    )
    
    class Meta:
        model = DocumentoFiscal
        exclude = (
            "user",
            "lojista",
            "posto_trabalho",
            "enviado_por_operador",
            "pendente",
        )
        fields = "__all__"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.lojista:
            self.fields['lojista_cnpj'].initial = self.instance.lojista.CNPJLojista
        else:
            self.fields['lojista_cnpj'].initial = "CNPJ não cadastrado"
        
        # Inicializar o campo status com o valor atual do documento
        if self.instance:
            self.fields['status'].initial = self.instance.status
    
    def clean_valorCielo(self):
        valor_cielo = self.cleaned_data.get('valorCielo')
        comprado_cielo = self.cleaned_data.get('compradoCielo')
        return clean_valor_cielo_helper(valor_cielo, comprado_cielo)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Limpar e validar valores monetários
        valor_cielo = cleaned_data.get('valorCielo')
        valor_outros = cleaned_data.get('valorOutros')
        valor_documento = cleaned_data.get('valorDocumento')
        
        # Converter valores string para Decimal se necessário
        if valor_cielo and isinstance(valor_cielo, str):
            try:
                # Remove R$, espaços e converte vírgula para ponto
                valor_limpo = valor_cielo.replace('R$', '').replace(' ', '').replace(',', '.')
                cleaned_data['valorCielo'] = Decimal(valor_limpo)
            except (ValueError, InvalidOperation):
                self.add_error('valorCielo', "Valor Cielo deve ser um número válido")
        
        if valor_outros and isinstance(valor_outros, str):
            try:
                valor_limpo = valor_outros.replace('R$', '').replace(' ', '').replace(',', '.')
                cleaned_data['valorOutros'] = Decimal(valor_limpo)
            except (ValueError, InvalidOperation):
                self.add_error('valorOutros', "Valor Outros deve ser um número válido")
        
        if valor_documento and isinstance(valor_documento, str):
            try:
                valor_limpo = valor_documento.replace('R$', '').replace(' ', '').replace(',', '.')
                cleaned_data['valorDocumento'] = Decimal(valor_limpo)
            except (ValueError, InvalidOperation):
                self.add_error('valorDocumento', "Valor Documento deve ser um número válido")
        
        # Garantir que valores vazios sejam 0
        if not valor_cielo or valor_cielo == '':
            cleaned_data['valorCielo'] = Decimal('0.00')
        
        if not valor_outros or valor_outros == '':
            cleaned_data['valorOutros'] = Decimal('0.00')
        
        return cleaned_data


class DocumentoFiscalEditForm(forms.ModelForm):
    lojista_cnpj = forms.CharField(
        label="CNPJ da Loja",
        required=False,
        disabled=True
    )
    numeroDocumento = forms.CharField(required=False)
    dataDocumento = forms.DateField(required=False)
    valorCielo = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        localize=True,
        label="Valor pago na Cielo",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control money-mask",
                "autocomplete": "off",
                "placeholder": "R$ 0,00",
            }
        ),
    )
    valorOutros = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        localize=True,
        label="Valor pago em outros métodos",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control money-mask",
                "autocomplete": "off",
                "placeholder": "R$ 0,00",
            }
        ),
    )
    valorDocumento = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        localize=True,
        label="Valor Total do Documento*",
        widget=forms.HiddenInput(
            attrs={
                "id": "id_valorDocumento",
            }
        ),
    )
    photo = forms.FileField(
        label="Documento Fiscal",
        required=False,
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*,.pdf",
            }
        ),
    )
    photo2 = forms.FileField(
        label="Comprovante do Cartão",
        required=False,
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*,.pdf",
            }
        ),
    )

    class Meta:
        model = DocumentoFiscal
        exclude = (
            "pendente",
            "user",
            "lojista",
            "posto_trabalho",
            "enviado_por_operador",
            "status",
        )
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.lojista:
            self.fields['lojista_cnpj'].initial = self.instance.lojista.CNPJLojista
        else:
            self.fields['lojista_cnpj'].initial = "CNPJ não cadastrado"


class DocumentoFiscalValidaForm(forms.ModelForm):
    photo = forms.FileField(
        label="Documento Fiscal",
        required=False,
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*,.pdf",
            }
        ),
    )
    photo2 = forms.FileField(
        label="Comprovante do Cartão",
        required=False,
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*,.pdf",
            }
        ),
    )

    class Meta:
        model = DocumentoFiscal
        exclude = (
            "user",
            "qtdeCupom",
            "posto_trabalho",
            "enviado_por_operador",
            "compradoMASTERCARD",
            "compradoREDE",
            "status",
        )
        fields = "__all__"
    
    def clean_valorCielo(self):
        valor_cielo = self.cleaned_data.get('valorCielo')
        comprado_cielo = self.cleaned_data.get('compradoCielo')
        return clean_valor_cielo_helper(valor_cielo, comprado_cielo)


