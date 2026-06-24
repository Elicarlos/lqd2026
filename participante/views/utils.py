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


def limpar_posto_trabalho(user):
    """Limpa o posto de trabalho do usuário ao fazer logout"""
    if hasattr(user, 'profile') and user.profile:
        user.profile.posto_trabalho = None
        user.profile.save(update_fields=['posto_trabalho'])


def is_celery_available():
    """
    Verifica se o Celery está disponível e funcionando.
    Retorna True se o Celery estiver disponível, False caso contrário.
    """
    try:
        from django.conf import settings
        
        # Verificar se o Celery está habilitado nas configurações
        if not getattr(settings, 'USE_CELERY_FOR_PDF', True):
            return False
        
        # Verificar se o broker está configurado
        if not hasattr(settings, 'CELERY_BROKER_URL'):
            return False
        
        # Tentar importar e verificar se o Celery está funcionando
        from celery import current_app
        if not current_app.conf.broker_url:
            return False
        
        # Teste básico de conectividade (opcional)
        try:
            # Tentar uma operação simples para verificar se o broker responde
            from celery.result import AsyncResult
            # Se chegou até aqui, o Celery está disponível
            return True
        except Exception:
            return False
            
    except ImportError:
        # Celery não está instalado
        return False
    except Exception:
        # Qualquer outro erro indica que o Celery não está disponível
        return False


def execute_with_celery_fallback(task_func, *args, **kwargs):
    """
    Executa uma função com fallback para execução síncrona se o Celery falhar.
    
    Esta função verifica automaticamente se o Celery está disponível e funcionando.
    Se estiver disponível, tenta executar a task de forma assíncrona.
    Se falhar ou não estiver disponível, executa de forma síncrona.
    
    Exemplo de uso:
        # Em vez de:
        # result = minha_task.delay(arg1, arg2)
        
        # Use:
        # result = execute_with_celery_fallback(minha_task, arg1, arg2)
    
    Args:
        task_func: Função/task a ser executada (deve ser uma task do Celery)
        *args, **kwargs: Argumentos para a função
    
    Returns:
        Resultado da execução da função (mesmo resultado que a task retornaria)
    
    Raises:
        Exception: Se tanto a execução assíncrona quanto a síncrona falharem
    """
    if is_celery_available():
        try:
            # Tentar execução assíncrona com Celery
            task = task_func.delay(*args, **kwargs)
            result = task.get(timeout=30)
            return result
        except Exception as celery_error:
            # Fallback para execução síncrona
            result = task_func(*args, **kwargs)
            return result
    else:
        # Execução síncrona direta
        result = task_func(*args, **kwargs)
        return result


def has_operational_access(user):
    """Verifica se o usuário tem permissão para acessar área operacional"""
    from participante.models import UserRole
    
    user_roles = UserRole.objects.filter(user=user).values_list('role__name', flat=True)
    user_roles_list = list(user_roles)
    
    # Roles que podem acessar área operacional
    roles_operacionais = ["Operador", "Supervisor", "Gerente", "Backoffice", "Gerente Solve", "Recursos Humanos", "Suporte", "Operadores"]
    return (
        user.is_superuser or
        any(role in roles_operacionais for role in user_roles_list) or
        any(user.groups.filter(name=role).exists() for role in roles_operacionais)
    )


def verificar_jornada_ativa(user):
    """
    Verifica se o usuário tem uma jornada de trabalho atribuída para hoje E se está dentro do horário permitido
    Retorna (pode_logar, jornada_atribuida, mensagem) onde:
    - pode_logar: True/False
    - jornada_atribuida: objeto JornadaColaborador ou None
    - mensagem: explicação do resultado
    """
    from participante.models import JornadaColaborador
    from datetime import date
    
    hoje = date.today()
    jornada_atribuida = JornadaColaborador.get_jornada_ativa(user, hoje)
    
    if not jornada_atribuida:
        return False, None, "Você não possui uma jornada de trabalho atribuída para hoje. Entre em contato com o administrador."
    
    # Verificar se está dentro do horário da jornada atribuída
    pode_logar, mensagem = jornada_atribuida.tipo_jornada.pode_logar_agora()
    
    if pode_logar:
        return True, jornada_atribuida, "Dentro do horário de trabalho permitido"
    else:
        return False, jornada_atribuida, f"Fora do horário de trabalho: {mensagem}"


def verificar_registro_jornada_ativa(user):
    """
    Verifica se o usuário já tem um registro de jornada ativa (já entrou no sistema hoje)
    Retorna (tem_registro, registro_jornada) onde:
    - tem_registro: True/False
    - registro_jornada: objeto RegistroJornada ou None
    """
    from participante.models import RegistroJornada
    
    registro_jornada = RegistroJornada.get_jornada_ativa(user)
    return registro_jornada is not None, registro_jornada


def not_found_page_view(request, exception):
    data = {}
    return render(request, "not_found.html", data)


def server_error_view(request, exception):
    data = {}
    return render(request, "not_found.html", data)


def main_page(request):
    login_form = LoginForm()
    return render(
        request,
        "participante/coming_soon.html",
        {"section": "homepage", "lf": login_form},
    )


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)  # Mudança para permitir staff
def handle_invalid_participante_url(request, invalid_path):
    """
    View para tratar URLs inválidas de participantes e redirecionar para busca por CPF
    """
    # Extrai o que foi digitado após /participante/
    invalid_id = invalid_path.strip('/')
    
    # Se parece ser um CPF (contém números), sugere buscar por CPF
    if any(char.isdigit() for char in invalid_id):
        messages.warning(request, f"URL inválida: '/participante/{invalid_id}/'. Para buscar um participante, use a busca por CPF.")
    else:
        messages.warning(request, f"URL inválida: '/participante/{invalid_id}/'. Para buscar um participante, use a busca por CPF.")
    
    return redirect('participante:search_by_cpf')


@login_required
@user_passes_test(lambda u: u.is_superuser)
@permission_required("campanha.finalizar_campanha", raise_exception=True)
def finalizar_campanha(request, id):
    campanha = get_object_or_404(Campanha, id=id, ativa=True)

    if request.method == "GET":
        pode_finalizar = campanha.pode_finalizar()
        if not pode_finalizar:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "A campanha não pode ser finalizada. Verifique pendências ou a data de término.",
                }
            )
        return JsonResponse({"status": "can_finalize", "pode_finalizar": True})

    elif request.method == "POST":
        if not campanha.pode_finalizar():
            return JsonResponse(
                {
                    "status": "error",
                    "message": "A campanha não pode ser finalizada. Verifique pendências ou a data de término.",
                }
            )

        campanha.ativa = False
        campanha.finalizada_em = timezone.now()
        campanha.finalizada_por = request.user
        campanha.save()

        return JsonResponse(
            {
                "status": "success",
                "message": f'A campanha "{campanha.nome}" foi finalizada com sucesso.',
            }
        )

    return HttpResponseBadRequest("Método não permitido")


def api_root(request):
    from django.http import JsonResponse
    return JsonResponse({
        "status": "LQD Headless API is active",
        "version": "v1.0",
        "documentation": "/api-auth/",
        "endpoints": {
            "api_participante": "/api/participante/v1/",
            "api_lojista": "/api/lojista/v1/"
        }
    })


def homepage(request):
    campanha_ativa = Campanha.objects.filter(ativa=True).first()
    if request.user.is_authenticated:
        # Verificar se o usuário precisa de jornada
        from participante.models import UserRole
        user_roles = UserRole.objects.filter(user=request.user).values_list('role__name', flat=True)
        user_roles_list = list(user_roles)
        
        grupos_jornada = ["Operador", "Operadores", "Backoffice", "Supervisor", "Suporte", "Gerente Solve", "Recursos Humanos"]
        precisa_jornada = (
            any(request.user.groups.filter(name=grupo).exists() for grupo in grupos_jornada) or
            any(role in grupos_jornada for role in user_roles_list)
        )
        
        if precisa_jornada:
            # Verificar se tem jornada ativa
            pode_logar, jornada_ativa, mensagem = verificar_jornada_ativa(request.user)
            if not pode_logar:
                # Se não pode logar, fazer logout e mostrar erro
                from django.contrib.auth import logout
                logout(request)
                messages.error(request, mensagem)
                return render(request, "index-new.html", {"campanha": campanha_ativa})
        
                    # Se chegou aqui, pode acessar normalmente
            # Verificar se é staff operacional (colaborador)
            # Superusers não precisam de posto de trabalho
            if request.user.is_superuser:
                return redirect(reverse("lojista:homepage"))
            elif request.user.is_staff:
                # Para colaboradores, SEMPRE redirecionar para seleção de posto
                # (mesmo que já tenha posto, precisa selecionar novamente)
                return redirect(reverse("participante:selecionar_posto"))
            else:
                return redirect(reverse("participante:dashboard"))

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "form_login":
            login_form = LoginForm(request.POST)
            if login_form.is_valid():
                username = login_form.cleaned_data["username"]
                password = login_form.cleaned_data["password"]
                user = authenticate(username=username, password=password)

                if user is not None and user.is_active:
                    login(request, user)

                    # Limpa mensagens antigas antes de adicionar a de boas-vindas
                    storage = messages.get_messages(request)
                    for _ in storage:
                        pass

                    # Redireciona baseado no tipo de usuário
                    # Define mensagem de boas-vindas baseada no tipo de usuário
                    redirect_url = reverse("participante:dashboard")  # Default redirect

                    # Verificar roles do novo sistema (UserRole)
                    from participante.models import UserRole
                    user_roles = UserRole.objects.filter(user=user).values_list('role__name', flat=True)
                    user_roles_list = list(user_roles)
                    
                    # Check if the user needs to select a workstation (operator groups)
                    grupos_jornada = ["Operador", "Operadores", "Backoffice", "Supervisor", "Suporte", "Gerente Solve", "Recursos Humanos"]
                    # Verificar tanto grupos Django antigos quanto UserRoles novos
                    precisa_jornada = (
                        any(user.groups.filter(name=grupo).exists() for grupo in grupos_jornada) or
                        any(role in grupos_jornada for role in user_roles_list)
                    )
                    
                    
                    # Verificar se é staff operacional (tem roles do sistema)
                    roles_operacionais = ["Operador", "Supervisor", "Gerente", "Backoffice", "Gerente Solve", "Recursos Humanos", "Suporte", "Operadores"]
                    is_staff_operacional = (
                        any(role in roles_operacionais for role in user_roles_list) or
                        any(user.groups.filter(name=role).exists() for role in roles_operacionais)
                    )
                    
                    if precisa_jornada:
                        
                        # Verificar se o usuário tem uma jornada ativa atribuída e está dentro do horário
                        pode_logar, jornada_ativa, mensagem = verificar_jornada_ativa(user)
                        
                        if pode_logar:
                            messages.success(
                                request,
                                "Bem-vindo! Selecione seu posto de trabalho para iniciar a jornada.",
                            )
                            redirect_url = reverse("participante:selecionar_posto")
                        else:
                            messages.error(request, mensagem)
                            # Não fazer login - redirecionar de volta para a página de login
                            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                                return JsonResponse(
                                    {
                                        "login_error": True,
                                        "errors": {"__all__": [mensagem]}
                                    }
                                )
                            return redirect("participante:homepage")
                    else:
                        
                        # Lógica de redirecionamento melhorada
                        if user.is_superuser:
                            messages.success(request, "Bem-vindo, Administrador!")
                            redirect_url = reverse("lojista:homepage")
                        elif is_staff_operacional:  # Tem roles do sistema - vai para área operacional
                            role_name = user_roles_list[0] if user_roles_list else next(
                                (group.name for group in user.groups.all()), "Staff"
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

                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse({"redirect_url": redirect_url})
                    return redirect(redirect_url)
                else:
                    error_msg = (
                        "Credenciais inválidas. Por favor, verifique seu CPF e senha."
                    )
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse(
                            {"login_error": True, "errors": {"__all__": [error_msg]}}
                        )
                    messages.error(request, error_msg)
            else:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "login_error": True,
                            "errors": login_form.errors.get_json_data(),
                        }
                    )
                messages.error(request, "Por favor, corrija os erros no formulário.")

        elif form_type == "form_adesao":
            form_adesao = FormLojistaAdesao(request.POST)
            if form_adesao.is_valid():
                try:
                    adesao = form_adesao.save(commit=False)
                    adesao.data_contato = None
                    adesao.atendido = False
                    adesao.status = "Pendente"
                    adesao.save()

                    success_msg = "Cadastro realizado com sucesso! Em breve entraremos em contato."
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse({"success": True, "message": success_msg})
                    messages.success(request, success_msg)
                except Exception as e:
                    logger.error(f"Erro ao salvar adesão: {str(e)}")
                    error_msg = "Erro ao salvar o cadastro. Por favor, tente novamente."
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse({"error": True, "message": error_msg})
                    messages.error(request, error_msg)
            else:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "error": True,
                            "message": "Por favor, corrija os erros no formulário.",
                            "errors": form_adesao.errors,
                        }
                    )
                messages.error(request, "Por favor, corrija os erros no formulário.")

    # GET: renderiza o template com os formulários
    form_adesao = FormLojistaAdesao()
    return render(
        request,
        "participante/index.html",
        {
            "form_adesao": form_adesao,
            "campanha": campanha_ativa,  # Adiciona a campanha ao contexto
        },
    )

    return render(request, 'index-new.html', context)


@login_required
@transaction.atomic
def marcar_inconsistente(request, id):
    """
    Marca um documento fiscal como inconsistente com observação.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Log da requisição
    logger.info(f"Marcar inconsistente iniciado - ID: {id}, User: {request.user.username}")
    
    instance = get_object_or_404(DocumentoFiscal, id=id)

    if instance.status != StatusChoices.PENDENTE:
        error_msg = f"O documento {instance.numeroDocumento} não está pendente de validação."
        messages.error(request, error_msg)
        return redirect("participante:backoffice")

    if request.method == "POST":
        observacao = request.POST.get('observacao', '').strip()
        
        if not observacao:
            messages.error(request, "É obrigatório informar o motivo da inconsistência.")
            return redirect("participante:backoffice")
        
        try:
            with transaction.atomic():
                instance.status = StatusChoices.INCONSISTENTE
                instance.observacao = observacao
                instance.save()
                
                success_msg = f"Documento {instance.numeroDocumento} marcado como inconsistente com sucesso!"
                messages.success(request, success_msg)
                logger.info(f"Documento marcado como inconsistente: {instance.numeroDocumento}")
                
        except Exception as e:
            logger.error(f"Erro ao marcar documento como inconsistente: {str(e)}", exc_info=True)
            messages.error(request, f"Erro ao marcar documento como inconsistente: {str(e)}")
    
    return redirect("participante:backoffice")


@require_POST
def consulta_cep(request):
    """
    View para consulta de CEP via AJAX - retorna dados do endereço em JSON
    
    Tenta usar brazilcep (múltiplos provedores). Se não estiver disponível,
    usa fallback manual com APICEP → BrasilAPI → ViaCEP
    """
    from django.http import JsonResponse
    import re
    import logging
    import requests
    
    logger = logging.getLogger(__name__)
    
    cep = request.POST.get('cep', '').strip()
    
    if not cep:
        return JsonResponse({
            'success': False,
            'message': 'CEP não informado'
        })
    
    # Remove todos os caracteres não numéricos do CEP
    cep_limpo = re.sub(r'\D', '', cep)
    
    if len(cep_limpo) != 8:
        return JsonResponse({
            'success': False,
            'message': 'CEP deve ter 8 dígitos'
        })
    
    # Tenta usar brazilcep primeiro (se estiver instalado)
    try:
        from brazilcep import get_address_from_cep, CEPNotFound
        
        address = get_address_from_cep(cep_limpo)
        
        if address:
            address_data = {
                'logradouro': address.get('street', ''),
                'bairro': address.get('district', ''),
                'localidade': address.get('city', ''),
                'uf': address.get('state', ''),
                'cep': address.get('cep', cep_limpo)
            }
            
            logger.info(f"✅ CEP {cep_limpo} encontrado via brazilcep")
            
            return JsonResponse({
                'success': True,
                'data': address_data,
                'message': 'Endereço encontrado com sucesso'
            })
        else:
            logger.warning(f"⚠️ CEP {cep_limpo} não encontrado")
            return JsonResponse({
                'success': False,
                'message': 'CEP não encontrado'
            })
    
    except (ImportError, ModuleNotFoundError):
        # Se brazilcep não estiver instalado, usa fallback manual
        logger.info("brazilcep não disponível, usando fallback manual")
        pass
    except Exception as e:
        # Se brazilcep falhar, continua para fallback manual
        logger.warning(f"Erro no brazilcep: {str(e)}, tentando fallback manual")
        pass
    
    # Fallback manual: tenta múltiplos provedores
    providers = [
        {
            'name': 'APICEP',
            'url': f'https://cdn.apicep.com/file/apicep/{cep_limpo}.json',
            'parser': lambda data: {
                'logradouro': data.get('address', ''),
                'bairro': data.get('district', ''),
                'localidade': data.get('city', ''),
                'uf': data.get('state', ''),
                'cep': data.get('code', cep_limpo)
            }
        },
        {
            'name': 'BrasilAPI',
            'url': f'https://brasilapi.com.br/api/cep/v1/{cep_limpo}',
            'parser': lambda data: {
                'logradouro': data.get('street', ''),
                'bairro': data.get('neighborhood', ''),
                'localidade': data.get('city', ''),
                'uf': data.get('state', ''),
                'cep': data.get('cep', cep_limpo)
            }
        },
        {
            'name': 'ViaCEP',
            'url': f'https://viacep.com.br/ws/{cep_limpo}/json/',
            'parser': lambda data: {
                'logradouro': data.get('logradouro', ''),
                'bairro': data.get('bairro', ''),
                'localidade': data.get('localidade', ''),
                'uf': data.get('uf', ''),
                'cep': data.get('cep', cep_limpo)
            }
        }
    ]
    
    for provider in providers:
        try:
            response = requests.get(provider['url'], timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verifica se não é um erro
                if not data.get('erro') and not data.get('error'):
                    address_data = provider['parser'](data)
                    
                    # Verifica se tem dados válidos
                    if address_data.get('localidade'):
                        logger.info(f"✅ CEP {cep_limpo} encontrado via {provider['name']}")
                        return JsonResponse({
                            'success': True,
                            'data': address_data,
                            'message': 'Endereço encontrado com sucesso'
                        })
        
        except Exception as e:
            logger.debug(f"Tentativa {provider['name']} falhou: {str(e)}")
            continue
    
    # Se chegou aqui, nenhum provedor funcionou
    logger.warning(f"⚠️ CEP {cep_limpo} não encontrado em nenhum provedor")
    return JsonResponse({
        'success': False,
        'message': 'CEP não encontrado. Verifique o CEP e tente novamente.'
    })


@require_POST
def limpar_mensagens(request):
    list(messages.get_messages(request))  # Consome todas as mensagens
    return JsonResponse({'ok': True})


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
@require_POST
def reprint_document(request, doc_id):
    """
    View para reimprimir cupons de um documento específico
    """
    try:
        doc = get_object_or_404(DocumentoFiscal, id=doc_id)
        
        # Verificar se o documento tem cupons impressos
        cupons = Cupom.objects.filter(documentoFiscal=doc, impresso=True)
        
        if not cupons.exists():
            return JsonResponse({
                'success': False,
                'message': 'Este documento não possui cupons impressos para reimpressão.'
            }, status=400)
        
        # Redirecionar para a impressão usando a view do BCP
        return redirect('bcp:print', id_=doc_id)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao processar reimpressão: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
@transaction.atomic
def marcar_inconsistente(request, id):
    """
    Marca um documento fiscal como inconsistente com observação.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Log da requisição
    logger.info(f"Marcar inconsistente iniciado - ID: {id}, User: {request.user.username}")
    
    instance = get_object_or_404(DocumentoFiscal, id=id)

    if instance.status != StatusChoices.PENDENTE:
        error_msg = f"O documento {instance.numeroDocumento} não está pendente de validação."
        messages.error(request, error_msg)
        return redirect("participante:backoffice")

    if request.method == "POST":
        observacao = request.POST.get('observacao', '').strip()
        
        if not observacao:
            messages.error(request, "É obrigatório informar o motivo da inconsistência.")
            return redirect("participante:backoffice")
        
        try:
            with transaction.atomic():
                instance.status = StatusChoices.INCONSISTENTE
                instance.observacao = observacao
                instance.save()
                
                success_msg = f"Documento {instance.numeroDocumento} marcado como inconsistente com sucesso!"
                messages.success(request, success_msg)
                logger.info(f"Documento marcado como inconsistente: {instance.numeroDocumento}")
                
        except Exception as e:
            logger.error(f"Erro ao marcar documento como inconsistente: {str(e)}", exc_info=True)
            messages.error(request, f"Erro ao marcar documento como inconsistente: {str(e)}")
    
    return redirect("participante:backoffice")


