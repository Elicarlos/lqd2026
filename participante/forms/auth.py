from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from localflavor.br.br_states import STATE_CHOICES
from localflavor.br.forms import BRCNPJField, BRCPFField, BRZipCodeField
from decimal import Decimal, InvalidOperation
import logging
from lojista.models import Lojista
from participante.models import DocumentoFiscal, Profile, Campanha  # Adicionado Campanha


class LoginForm(forms.Form):
    username = BRCPFField(
        label="CPF",
        max_length=14,
        min_length=11,
        widget=forms.TextInput(
            attrs={
                "placeholder": "000.000.000-00",
                "class": "form-input cpf-mask",
                "autocomplete": "off",
            }
        ),
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Digite sua senha",
                "class": "form-input",
                "autocomplete": "current-password",
            }
        ),
    )

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username:
            # Remove qualquer caractere não numérico do CPF
            username = "".join(filter(str.isdigit, username))

            # Não validar se o usuário existe aqui - isso será feito na view de login
            # Apenas retornar o CPF limpo

        return username


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Senha* (mínimo de 8 caracteres)",
                "class": "custom-input",
            }
        ),
    )
    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={"placeholder": "Confirmação de senha*", "class": "custom-input"}
        ),
    )
    username = BRCPFField(
        required=True,
        max_length=14,
        min_length=11,
        widget=forms.TextInput(
            attrs={
                "placeholder": "CPF*",
                "autocomplete": "off",
                "class": "custom-input cpf",
                "cpf": "id_CPF",
            }
        ),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Email*",
                "autocomplete": "off",
                "class": "custom-input",
            }
        ),
    )

    class Meta:
        model = User
        fields = ("username", "email")

    def clean_username(self):
        username = self.cleaned_data.get("username")
        # Remove any non-digit characters from CPF
        username = "".join(filter(str.isdigit, username))
        username_qs = User.objects.filter(username=username)
        if username_qs.exists():
            raise ValidationError("CPF ou email já estão em uso. Se você já possui cadastro, faça login ou recupere sua senha.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        username = self.cleaned_data.get("username")
        if (
            email
            and User.objects.filter(email=email).exclude(username=username).exists()
        ):
            raise forms.ValidationError("CPF ou email já estão em uso. Se você já possui cadastro, faça login ou recupere sua senha.")
        return email

    def clean_password2(self):
        cd = self.cleaned_data
        # Check if both password fields exist in cleaned_data before comparing
        if "password" in cd and "password2" in cd:
            if cd["password"] != cd["password2"]:
                raise forms.ValidationError("As senhas digitadas não correspondem.")
        return cd["password2"]


class ProfileRegistrationForm(forms.ModelForm):
    CHOICES_SEXO = (("M", "Masculino"), ("F", "Feminino"), ("P", "Prefiro não dizer"))
    sexo = forms.ChoiceField(
        choices=CHOICES_SEXO,
        widget=forms.Select(attrs={"id": "sexo", "class": "custom-input"}),
    )

    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "custom-input",
                "placeholder": "Data de Nascimento*"
            }
        ),
        label="Data de Nascimento"
    )
    nome = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nome Completo*",
                "autocomplete": "off",
                "class": "custom-input",
            }
        ),
    )
    # RG = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder':'RG*','autocomplete':'off', 'class': 'custom-input' }))
    CPF = BRCPFField(
        required=False,
        max_length=14,
        min_length=11,
        widget=forms.TextInput(
            attrs={"placeholder": "CPF*", "class": "custom-input cpf", "type": "hidden"}
        ),
    )
    foneCelular1 = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Celular*",
                "class": "custom-input phone_with_ddd",
                "autocomplete": "off",
            }
        ),
    )
    whatsapp = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Whatsapp",
                "class": "custom-input phone_with_ddd",
                "autocomplete": "off",
            }
        ),
    )
    facebook = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "Facebook", "autocomplete": "off"}
        ),
    )
    twitter = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Twitter", "autocomplete": "off"}),
    )
    endereco = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Endereço*",
                "autocomplete": "off",
                "class": "custom-input",
                "id": "id_endereco",
            }
        ),
    )
    enderecoNumero = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nº da casa",
                "autocomplete": "off",
                "class": "custom-input",
            }
        ),
    )
    enderecoComplemento = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Complemento",
                "autocomplete": "off",
                "class": "custom-input",
            }
        ),
    )
    bairro = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Bairro*",
                "autocomplete": "off",
                "class": "custom-input",
                "id": "id_bairro",
            }
        ),
    )
    cidade = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Cidade*",
                "autocomplete": "off",
                "class": "custom-input",
                "id": "id_cidade",
            }
        ),
    )
    estado = forms.ChoiceField(
        required=True,
        choices=STATE_CHOICES,
        widget=forms.Select(attrs={"class": "custom-input"}),
    )
    # estado = forms.ChoiceField(required=True, widget=forms.TextInput(attrs={'placeholder':'Estado*', 'autocomplete':'off'}))
    CEP = BRZipCodeField(
        required=False,
        label="Cep*",
        widget=forms.TextInput(
            attrs={
                "class": "custom-input cep",
                "placeholder": "CEP*",
                "autocomplete": "off",
            }
        ),
    )
    pergunta = forms.ChoiceField(
        required=True,
        choices=[
            ('liquida_teresina_2025', 'Natal de Luz e Prêmios'),
            ('outra', 'Outra'),
        ],
        initial='liquida_teresina_2025',
        widget=forms.RadioSelect(attrs={
            "class": "form-check-input",
            "id": "pergunta"
        }),
        label="Qual é a maior Promoção do Comércio de Teresina?"
    )
    
    termos_de_aceite = forms.BooleanField(
        required=True,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
            "id": "aceiteTermos"
        }),
        label="Li e aceito os Termos de Uso e Política de Privacidade"
    )

    class Meta:
        model = Profile
        fields = (
            "nome",
            "CPF",
            "sexo",
            "date_of_birth",
            "foneFixo",
            "foneCelular1",
            "CEP",
            "foneCelular2",
            "foneCelular3",
            "whatsapp",
            "facebook",
            "twitter",
            "endereco",
            "enderecoNumero",
            "enderecoComplemento",
            "bairro",
            "cidade",
            "estado",
            "pergunta",
            "termos_de_aceite",
        )
        exclude = ("user", "dataCadastro", "cadastradoPor", "ativo", "pendente", "RG")

    def clean_CPF(self):
        cpf = self.cleaned_data.get("CPF")
        if cpf:
            # Remove any non-digit characters from CPF
            cpf = "".join(filter(str.isdigit, cpf))
            # Exclui o próprio objeto que está sendo editado da verificação de unicidade
            if (
                self.instance
                and Profile.objects.filter(CPF=cpf)
                .exclude(pk=self.instance.pk)
                .exists()
            ):
                raise ValidationError("Profile com este CPF já existe.")
            elif not self.instance and Profile.objects.filter(CPF=cpf).exists():
                raise ValidationError("Profile com este CPF já existe.")
        return cpf

    def clean_pergunta(self):
        pergunta = self.cleaned_data.get("pergunta")
        if pergunta != 'liquida_teresina_2025':
            raise ValidationError("Resposta incorreta. A maior Promoção do Comércio de Teresina é a Natal de Luz e Prêmios.")
        return pergunta


class UserEditForm(forms.ModelForm):
    """
    Formulário para edição dos dados básicos do usuário.
    """
    first_name = forms.CharField(required=False, widget=forms.HiddenInput())
    last_name = forms.CharField(required=False, widget=forms.HiddenInput())
    user_permissions = forms.ChoiceField(required=False, widget=forms.HiddenInput())
    groups = forms.ChoiceField(required=False, widget=forms.HiddenInput())
    is_superuser = forms.BooleanField(required=False, widget=forms.HiddenInput())
    is_staff = forms.BooleanField(required=False, widget=forms.HiddenInput())
    password = forms.CharField(required=False, widget=forms.HiddenInput())
    date_joined = forms.DateField(
        required=False, widget=forms.Select(attrs={"type": "hidden"})
    )

    class Meta:
        model = User
        fields = "__all__"
        widgets = {
            "ativo": forms.HiddenInput,
            "user_permissions": forms.HiddenInput,
            "groups": forms.HiddenInput,
            "is_superuser": forms.HiddenInput,
            "last_login": forms.HiddenInput,
            "is_staff": forms.HiddenInput,
            "password": forms.HiddenInput,
            "is_active": forms.HiddenInput,
            "date_joined": forms.HiddenInput,
        }
        exclude = (
            "password",
            "username",
        )

    def __init__(self, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        # Se você deseja garantir que `is_active` nunca seja alterado, não o inclua no formulário
        if "is_active" in self.fields:
            del self.fields["is_active"]


class ProfileEditForm(forms.ModelForm):
    """
    Formulário para edição do perfil do usuário.
    Inclui informações pessoais, contato e endereço.
    """
    CHOICES_SEXO = (
        ("", "Selecione"),
        ("M", "Masculino"), 
        ("F", "Feminino"), 
        ("P", "Prefiro não dizer")
    )
    
    # Campos pessoais
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date",
            "placeholder": "Data de Nascimento"
        })
    )
    nome = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Nome Completo"
        })
    )
    
    CPF = BRCPFField(
        required=True,
        max_length=14,
        min_length=11,
        widget=forms.TextInput(attrs={
            "class": "form-control cpf",
            "placeholder": "000.000.000-00"
        })
    )
    
    sexo = forms.ChoiceField(
        required=True,
        choices=CHOICES_SEXO,
        widget=forms.Select(attrs={
            "class": "form-control",
            "placeholder": "Selecione"
        })
    )
    
    # Campos de contato
    foneCelular1 = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control phone_with_ddd",
            "placeholder": "(00) 00000-0000"
        })
    )
    
    whatsapp = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control phone_with_ddd",
            "placeholder": "(00) 00000-0000"
        })
    )
    
    facebook = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Seu perfil no Facebook"
        })
    )
    
    twitter = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Seu perfil no Twitter"
        })
    )
    
    # Campos de endereço
    CEP = BRZipCodeField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control cep",
            "placeholder": "00000-000"
        })
    )
    
    endereco = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Rua, Avenida, etc"
        })
    )
    
    enderecoNumero = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Número"
        })
    )
    
    enderecoComplemento = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Complemento"
        })
    )
    
    bairro = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Bairro"
        })
    )
    
    cidade = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Cidade"
        })
    )
    
    estado = forms.ChoiceField(
        required=True,
        choices=STATE_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-control",
            "placeholder": "Selecione o Estado"
        })
    )
    
    # Campo oculto
    pergunta = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    class Meta:
        model = Profile
        fields = [
            'nome', 'CPF', 'sexo', 'date_of_birth', 'foneCelular1',
            'whatsapp', 'facebook', 'twitter',
            'CEP', 'endereco', 'enderecoNumero', 'enderecoComplemento',
            'bairro', 'cidade', 'estado'
        ]
        exclude = ("user", "dataCadastro", "cadastradoPor", "ativo", "pendente", "RG")


class CepForm(forms.Form):
    cep = forms.CharField(label="CEP", max_length=9)
    endereco = forms.CharField(label="Endereço", widget=forms.Textarea, required=False)


