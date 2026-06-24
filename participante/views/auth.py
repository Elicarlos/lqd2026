import json
from calendar import month
from datetime import datetime, timedelta
from decimal import Decimal
from pydoc import Doc
from unicodedata import decimal
from unittest import result
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    QueryDict,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from yaml import DocumentEndEvent
from participante.tasks import email_boas_vindas_task
from participante.forms import *
from participante.models import Campanha, Profile, DocumentoFiscal, PostoTrabalho, RegistroJornada, StatusChoices, TipoJornada, Auditoria, CancelamentoImpressao
from lojista.models import Lojista, AdesaoLojista
from participante.filters import UserFilter, DocFilter
from django.db.models.functions import Lower, Upper
from cupom.forms import AddCupomForm
from cupom.models import Cupom
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db import transaction
from participante.forms import LoginForm, CepForm
from lojista.forms import FormLojistaAdesao
import requests
from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.utils.timezone import now
from django.db import IntegrityError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from django.template.loader import render_to_string
from participante.tasks import (
    email_recuperacao_senha,
    gerar_pdf_batidas_task,
    gerar_pdf_batidas_filtros_task,
)
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from django.contrib.auth.decorators import permission_required
from django.db.models import Exists, OuterRef
from xhtml2pdf import pisa
from django.db.models import Q
from django.views.generic import TemplateView
from participante.templatetags.custom_filters import formatar_timedelta
from participante.permissions import (
    role_required,
    any_role_required,
    all_roles_required,
    is_operador,
    is_gerente,
    is_backoffice,
    is_supervisor,
    is_gerente_solve,
    is_recursos_humanos,
    get_user_roles,
    PERMISSIONS,
)
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.shortcuts import render
from django.db.models import Count
from participante.models import DocumentoFiscal
from django.db import IntegrityError
from django.http import HttpResponseGone
from django.db.models.functions import TruncMonth, TruncDate
from django.db.models.aggregates import Count, Avg, Min, Max, Sum
from django.db.models import Count, F
from utils.formatters import formatar_duracao
from django.core.files.storage import FileSystemStorage
from django.views.decorators.http import require_POST
from utils.formatters import formatar_cpf  # Importa a função do novo módulo
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie


from .utils import execute_with_celery_fallback, verificar_jornada_ativa, verificar_registro_jornada_ativa

class PoliticaPrivacidadeView(TemplateView):
    template_name = "politica_privacidade.html" # Referencia o arquivo criado
    
    # Se você precisar passar o objeto campanha (como no seu template de exemplo)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Substitua 'Campanha.objects.get(ativo=True)' pela sua lógica real
        # context['campanha'] = Campanha.objects.get(ativo=True) 
        return context


class TermosUsoView(TemplateView):
    template_name = "termos_uso.html" # Referencia o arquivo criado

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context['campanha'] = Campanha.objects.get(ativo=True) 
        return context


def user_login(request):
   
    if request.method == "POST":
        form = LoginForm(request.POST)
        
        if not form.is_valid():
            # Se há erro de CSRF, redirecionar para página de aviso elegante
            if 'csrfmiddlewaretoken' in form.errors:
                return redirecionar_aviso(
                    request,
                    titulo="Erro de Segurança",
                    mensagem="Erro de segurança. Por favor, recarregue a página e tente novamente.",
                    tipo="error",
                    acao_primaria="Tentar Novamente",
                    acao_primaria_url="/",
                    acao_primaria_icone="refresh"
                )

        if form.is_valid():
            cd = form.cleaned_data
            username = cd["username"]
            password = cd["password"]
            

            # Verifica se o usuário existe
            user_exists = User.objects.filter(username=username).exists()
           

            if user_exists:
                user_obj = User.objects.get(username=username)
                

            user = authenticate(request, username=username, password=password)

            if user is not None:
                # User authentication successful
                if user.is_active:
                    # Verificar se é colaborador inativo
                    if hasattr(user, 'profile') and user.profile.is_colaborador and not user.profile.status_ativo:
                        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                            return JsonResponse(
                                {
                                    "success": False,
                                    "message": "Seu cadastro está sendo configurado pela equipe. Aguarde a ativação."
                                }
                            )
                        return redirecionar_aviso(
                            request,
                            titulo="Cadastro em Configuração",
                            mensagem="Seu cadastro está sendo configurado pela equipe. Aguarde a ativação.",
                            tipo="warning",
                            acao_primaria="Entendi",
                            acao_primaria_url="/",
                            acao_primaria_icone="check"
                        )
                    
                    # Define mensagem de boas-vindas baseada no tipo de usuário
                    redirect_url = reverse("participante:dashboard")  # Default redirect

                    # Verificar roles do novo sistema (UserRole) - OTIMIZADO
                    from participante.models import UserRole
                    user_roles = UserRole.objects.filter(user=user).select_related('role').values_list('role__name', flat=True)
                    user_roles_list = list(user_roles)
                    
                    # Check if the user needs to select a workstation (operator groups) - OTIMIZADO
                    grupos_jornada = ["Operador", "Operadores", "Backoffice", "Supervisor", "Suporte", "Gerente Solve", "Recursos Humanos"]
                    # Verificar tanto grupos Django antigos quanto UserRoles novos
                    user_groups = set(user.groups.values_list('name', flat=True))
                    precisa_jornada = (
                        any(grupo in user_groups for grupo in grupos_jornada) or
                        any(role in grupos_jornada for role in user_roles_list)
                    )
                    
                    
                    # Verificar se é staff operacional (tem roles do sistema) - OTIMIZADO
                    roles_operacionais = ["Operador", "Supervisor", "Gerente", "Backoffice", "Gerente Solve", "Recursos Humanos", "Suporte", "Operadores"]
                    is_staff_operacional = (
                        any(role in roles_operacionais for role in user_roles_list) or
                        any(role in user_groups for role in roles_operacionais)
                    )
                    
                    if precisa_jornada:

                        if hasattr(user, 'profile') and user.profile:
                            user.profile.posto_trabalho = None
                            user.profile.save(update_fields=['posto_trabalho'])
                        
                        # Verificar se o usuário tem uma jornada de trabalho atribuída e está dentro do horário
                        pode_logar, jornada_atribuida, mensagem = verificar_jornada_ativa(user)
                        
                        if pode_logar:
                            
                            # Verificar se já tem um registro de jornada ativa (já entrou hoje)
                            tem_registro, registro_jornada = verificar_registro_jornada_ativa(user)
                            
                            if tem_registro:
                                messages.success(request, "Bem-vindo de volta! Continue seu trabalho.")
                                # Se já tem jornada ativa, vai para a área de trabalho
                                redirect_url = reverse("lojista:homepage")
                            else:
                                messages.success(request, "Bem-vindo! Selecione seu posto de trabalho para iniciar a jornada.")
                                # Primeiro acesso do dia - vai para dashboard onde modal aparecerá
                                redirect_url = reverse("lojista:homepage")
                            
                            # FAZER LOGIN APENAS SE PODE LOGAR
                            login(request, user)
                            
                        else:
                            # NÃO FAZER LOGIN - usuário fora do horário
                            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                                return JsonResponse(
                                    {
                                        "success": False,
                                        "message": mensagem,
                                        "csrf_token": get_token(request),
                                    }
                                )
                            return redirecionar_aviso(
                                request,
                                titulo="Horário de Trabalho",
                                mensagem=mensagem,
                                tipo="warning",
                                acao_primaria="Entendi",
                                acao_primaria_url="/",
                                acao_primaria_icone="clock"
                            )
                    else:
                        
                        # Lógica de redirecionamento melhorada
                        if user.is_superuser:
                            messages.success(request, "Bem-vindo, Administrador!")
                            redirect_url = reverse("lojista:homepage")
                        elif is_staff_operacional:  # Tem roles do sistema - vai para área operacional
                            role_name = user_roles_list[0] if user_roles_list else next(
                                (group for group in user_groups), "Staff"
                            )
                            messages.success(request, f"Bem-vindo, {role_name}!")
                            # Staff operacional vai para lojista (área operacional)
                            redirect_url = reverse("lojista:homepage")
                        elif user.is_staff:  # Staff sem role específico
                            messages.success(request, "Bem-vindo, Staff!")
                            redirect_url = reverse("participante:dashboard")
                        else:  # Participante comum
                            profile_name = getattr(user.profile, 'nome', user.username) if hasattr(user, 'profile') else user.username
                            messages.success(request, f"Bem-vindo, {profile_name}!")
                            redirect_url = reverse("participante:dashboard")
                        
                        # FAZER LOGIN PARA USUÁRIOS QUE NÃO PRECISAM DE JORNADA
                        login(request, user)

                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse(
                            {
                                "success": True,
                                "redirect_url": redirect_url,
                                "csrf_token": get_token(
                                    request
                                ),  # Include the new CSRF token
                            }
                        )
                    return redirect(redirect_url)
                else:
                    
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse(
                            {
                                "success": False, 
                                "message": "Conta desativada!",
                                "csrf_token": get_token(request),
                            }
                        )
                    return redirecionar_aviso(
                        request,
                        titulo="Conta Desativada",
                        mensagem="Sua conta foi desativada. Entre em contato com o administrador.",
                        tipo="error",
                        acao_primaria="Entendi",
                        acao_primaria_url="/",
                        acao_primaria_icone="user-times"
                    )
            else:
                # Verificar se o usuário existe para dar mensagem mais específica
                if user_exists:
                    # Usuário existe mas senha está errada
                    error_message = "Senha incorreta!"
                else:
                    # Usuário não existe
                    error_message = "CPF não encontrado no sistema!"
                
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": False, 
                            "message": error_message,
                            "csrf_token": get_token(request),
                        }
                    )
                return redirecionar_aviso(
                    request,
                    titulo="Erro de Login",
                    mensagem=error_message,
                    tipo="error",
                    acao_primaria="Tentar Novamente",
                    acao_primaria_url="/",
                    acao_primaria_icone="sign-in-alt"
                )
        else:
            # Verificar se é erro de CSRF
            if 'csrfmiddlewaretoken' in form.errors:
                return redirecionar_aviso(
                    request,
                    titulo="Erro de Segurança",
                    mensagem="Erro de segurança. Por favor, recarregue a página e tente novamente.",
                    tipo="error",
                    acao_primaria="Tentar Novamente",
                    acao_primaria_url="/",
                    acao_primaria_icone="refresh"
                )
            
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                errors = {}
                for field, error_list in form.errors.items():
                    errors[field] = error_list[0]
                return JsonResponse({
                    "success": False, 
                    "errors": errors,
                    "csrf_token": get_token(request),
                })
            messages.error(request, "Por favor, corrija os erros abaixo.")
    else:
        form = LoginForm()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "success": False, 
            "message": "Método não permitido",
            "csrf_token": get_token(request),
        })
    
    return redirect('/')


@transaction.atomic
def register(request):
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("=== INÍCIO DO REGISTRO ===")
    
    # Verificar se o usuário logado é colaborador
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Colaboradores não podem participar da campanha. Esta funcionalidade é restrita a participantes comuns.")
        return redirect("participante:homepage")
    
    if request.method == "POST":
        logger.info("Método POST recebido")
        
        user_form = UserRegistrationForm(request.POST)
        profile_form = ProfileRegistrationForm(request.POST, files=request.FILES)
        
        logger.info(f"Dados do formulário: {request.POST}")

        # Get raw data to check for duplicates before full validation
        username = user_form.data.get('username')
        email = user_form.data.get('email')
        
        logger.info(f"Username (CPF): {username}")
        logger.info(f"Email: {email}")

        if username and User.objects.filter(username=username).exists():
            logger.warning(f"CPF já existe: {username}")
            user_form.add_error('username', "Este CPF já está cadastrado no sistema.")
        
        if email and User.objects.filter(email=email).exists():
            logger.warning(f"Email já existe: {email}")
            user_form.add_error('email', "Este e-mail já está cadastrado no sistema.")
        
        # Verificar se o CPF já existe na tabela Profile (colaboradores ou participantes)
        if username:
            cpf_limpo = "".join(filter(str.isdigit, username))
            cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
            
            logger.info(f"CPF limpo: {cpf_limpo}")
            logger.info(f"CPF formatado: {cpf_formatado}")
            
            if Profile.objects.filter(
                Q(CPF=cpf_limpo) | 
                Q(CPF=cpf_formatado) | 
                Q(CPF__icontains=cpf_limpo)
            ).exists():
                logger.warning(f"CPF já existe no Profile: {cpf_limpo}")
                user_form.add_error('username', "Este CPF já está cadastrado no sistema.")

        # Now, validate both forms. If we added an error above, is_valid() will be False.
        logger.info("Validando formulários...")
        user_valid = user_form.is_valid()
        profile_valid = profile_form.is_valid()
        
        logger.info(f"User form válido: {user_valid}")
        logger.info(f"Profile form válido: {profile_valid}")
        
        if not user_valid:
            logger.error(f"Erros no user_form: {user_form.errors}")
        if not profile_valid:
            logger.error(f"Erros no profile_form: {profile_form.errors}")
        
        if user_valid and profile_valid:
            logger.info("Formulários válidos, tentando salvar...")
            try:
                # If we get here, forms are valid and no duplicates were found
                logger.info("Salvando usuário...")
                new_user = user_form.save(commit=False)
                new_user.set_password(user_form.cleaned_data["password"])
                new_user.save()
                logger.info(f"Usuário salvo com ID: {new_user.id}")

                logger.info("Salvando perfil...")
                new_profile = profile_form.save(commit=False)
                # Formatar o CPF antes de salvar no Profile
                cpf_limpo = new_user.username
                cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
                new_profile.CPF = cpf_formatado
                new_profile.user = new_user
                
                # Para participantes, definir is_colaborador como False
                new_profile.is_colaborador = False
                
                logger.info(f"Dados do perfil antes de salvar: CPF={new_profile.CPF}, User={new_profile.user.id}")
                new_profile.save()
                logger.info(f"Perfil salvo com ID: {new_profile.id}")

                # NÃO faz login automático
                messages.success(request, f"Participante {new_profile.nome} cadastrado com sucesso! Faça login para continuar.")
                logger.info("=== REGISTRO CONCLUÍDO COM SUCESSO ===")
                return redirect('participante:register_done')

            except Exception as e:
                logger.error(f"Erro durante o salvamento: {str(e)}", exc_info=True)
                # Add a generic error if something unexpected happens during save
                user_form.add_error(None, f"Ocorreu um erro inesperado durante o cadastro: {e}")
        
        # If we reach this point, it's because the forms were invalid from the start,
        # or we added a duplicate error. Render the page again with the forms
        # containing the error messages.
        logger.error("=== REGISTRO FALHOU - RETORNANDO FORMULÁRIO COM ERROS ===")
        messages.error(request, "Erro no formulário. Por favor, corrija os erros indicados.")
        return render(
            request,
            "participante/registerpart-new.html",
            {"user_form": user_form, "profile_form": profile_form},
        )
    else:
        logger.info("Método GET - Exibindo formulário em branco")
        # For a GET request, display a blank form
        user_form = UserRegistrationForm()
        profile_form = ProfileRegistrationForm()
        return render(
            request,
            "participante/registerpart-new.html",
            {"user_form": user_form, "profile_form": profile_form},
        )


def register_done(request):
    """
    Página de sucesso pós-cadastro. Acessada via redirect.
    """
    return render(request, "participante/register_done.html")


class CustomPasswordResetView(PasswordResetView):
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("participante:password_reset_done")
    template_name = "registration/password_reset_form.html"
    from_email = "suporte@mg.nataldeluzcdl.com.br"

    def form_valid(self, form):
        """
        Substitui o método form_valid para enviar o email de redefinição de senha usando Celery.
        """
        opts = {
            "use_https": self.request.is_secure(),
            "token_generator": self.token_generator,
            "from_email": self.from_email,
            "email_template_name": self.email_template_name,
            "subject_template_name": self.subject_template_name,
            "request": self.request,
            "html_email_template_name": self.html_email_template_name,
            "extra_email_context": self.extra_email_context,
        }

        # Salva o formulário e gera o e-mail
        form.save(**opts)

        return super().form_valid(form)

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        """
        Envia um e-mail de redefinição de senha usando Celery.
        """
        subject = render_to_string(subject_template_name, context)
        subject = "".join(subject.splitlines())
        body = render_to_string(email_template_name, context)
        
        # Usar a função helper com fallback automático
        try:
            execute_with_celery_fallback(email_recuperacao_senha, subject, to_email, body, from_email)
        except Exception as e:
            # Fallback direto se a função helper falhar
            email_recuperacao_senha(subject, to_email, body, from_email)


@login_required
def change_password(request):
    """
    View para permitir que usuários troquem sua própria senha.
    """
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Atualiza a sessão para não fazer logout
            update_session_auth_hash(request, user)
            
            # Marcar senha como não temporária
            if hasattr(user, 'profile'):
                user.profile.senha_temporaria = False
                user.profile.save()
            
            messages.success(request, 'Senha alterada com sucesso!')
            
            # Verificar se o usuário precisa selecionar posto de trabalho
            from participante.models import UserRole
            user_roles = UserRole.objects.filter(user=request.user).values_list('role__name', flat=True)
            user_roles_list = list(user_roles)
            
            grupos_jornada = ["Operador", "Operadores", "Backoffice", "Supervisor", "Suporte", "Gerente Solve", "Recursos Humanos"]
            precisa_jornada = (
                any(request.user.groups.filter(name=grupo).exists() for grupo in grupos_jornada) or
                any(role in grupos_jornada for role in user_roles_list)
            )
            
            # Se precisa de jornada e não tem posto selecionado, vai para seleção de posto
            # Superusers não precisam de posto de trabalho
            if precisa_jornada and not request.user.is_superuser and (not hasattr(request.user, 'profile') or not request.user.profile.posto_trabalho):
                return redirect('participante:selecionar_posto')
            
            # Redirecionar baseado no tipo de usuário
            if request.user.is_superuser or request.user.is_staff or request.user.groups.exists():
                return redirect('lojista:homepage')  # Área operacional para colaboradores
            else:
                return redirect('participante:dashboard')  # Dashboard de participante
        else:
            messages.error(request, 'Erro ao alterar senha. Verifique os dados informados.')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {
        'form': form,
        'section': 'change_password'
    }
    
    return render(request, 'participante/change_password.html', context)


