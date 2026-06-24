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


from .utils import limpar_posto_trabalho

def iniciar_jornada(request, posto_id):
    posto_trabalho = get_object_or_404(PostoTrabalho, id=posto_id)

    RegistroJornada.objects.create(
        operador=request.user,
        posto_trabalho=posto_trabalho,
        horario_inicio=timezone.now(),
    )

    return redirect("pagina_incial_operado")


@login_required
def finalizar_jornada(request):
    """Finaliza a jornada ativa do usuário ou uma jornada específica"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Verificar se foi passado um ID específico de jornada
        jornada_id = request.POST.get('jornada_id')
        
        if jornada_id:
            # Finalizar jornada específica (para administradores)
            jornada = get_object_or_404(RegistroJornada, id=jornada_id)
            
            # Verificar se o usuário tem permissão para finalizar esta jornada
            if not (request.user.is_superuser or request.user.is_staff):
                messages.error(request, "Você não tem permissão para finalizar jornadas de outros usuários.")
                return redirect('lojista:jornadas_gestao')
        else:
            # Finalizar jornada ativa do usuário atual
            jornada = RegistroJornada.get_jornada_ativa(request.user)
            
            if not jornada:
                messages.warning(request, "Você não possui uma jornada ativa para finalizar.")
                return redirect('participante:dashboard')
        
        # Finaliza a jornada
        jornada.finalizar(
            finalizada_por=request.user,
            observacoes="Finalizada pelo usuário"
        )
        
        # Atualiza a data da última jornada no profile (apenas para jornada própria)
        if not jornada_id:
            request.user.profile.ultima_jornada_data = timezone.localdate()
            request.user.profile.save(update_fields=['ultima_jornada_data'])
        
        messages.success(
            request, 
            f"Jornada finalizada com sucesso! Duração: {jornada.get_duracao_formatada()}"
        )
        
        # Redirecionar baseado no contexto
        if jornada_id:
            return redirect('lojista:jornadas_gestao')
        else:
            return redirect('participante:dashboard')
        
    except Exception as e:
        logger.error(f"Erro ao finalizar jornada: {str(e)}")
        messages.error(request, "Erro ao finalizar jornada. Tente novamente.")
        
        # Redirecionar baseado no contexto
        if request.POST.get('jornada_id'):
            return redirect('lojista:jornadas_gestao')
        else:
            return redirect('participante:dashboard')


@login_required
def selecionar_posto(request):
    
    from django.middleware.csrf import get_token    
    get_token(request)    
    
    requer_controle = request.user.profile.requer_controle_jornada()

   
    
    if not requer_controle:        
        messages.info(request, "Você não precisa de controle de jornada.")        
        if request.user.is_superuser or request.user.is_staff:           
            return redirect('lojista:homepage')
        else:
            return redirect('participante:dashboard')    
    
    from participante.models import RegistroJornada
    jornada_iniciada = RegistroJornada.objects.filter(
        user=request.user,
        horario_fim__isnull=True,
        status='ATIVA'
    ).first()  
    
    if jornada_iniciada:      
        # Só mostrar mensagem se não for um POST (para evitar duplicação)
        if request.method != "POST":
            messages.info(request, "Você já possui uma jornada ativa. Selecione ou altere seu posto de trabalho.")
    
    # Verificar se o usuário pode iniciar jornada OU se já tem jornada ativa
    # (lógica removida para simplificar)
    
    pode_iniciar, motivo = request.user.profile.pode_iniciar_jornada()
    tem_jornada_ativa = request.user.profile.tem_jornada_ativa()    
    
    if not pode_iniciar and not tem_jornada_ativa:     
        # Limpar posto de trabalho antes do logout
        limpar_posto_trabalho(request.user)
        # Fazer logout do usuário
        from django.contrib.auth import logout
        logout(request)        
        
        messages.error(request, f"Acesso negado: {motivo}")        
        
        return redirect('/')   

   
  
    # REMOVIDO: Verificação que redirecionava se já tinha posto
    # if not (request.user.is_superuser or request.user.is_staff):
    #     if hasattr(request.user, 'profile') and request.user.profile.posto_trabalho:
    #         return redirect('participante:dashboard')
    
    if request.method == "POST":
        # Verificar token CSRF
        from django.middleware.csrf import get_token
        get_token(request)  # Regenerar token se necessário
        
        posto_id = request.POST.get("posto_trabalho")      
        
        if posto_id:
            posto_trabalho = get_object_or_404(PostoTrabalho, id=posto_id)
            
            
            # Verificar se já existe uma jornada ativa
            jornada_ativa = RegistroJornada.objects.filter(
                user=request.user, 
                horario_fim__isnull=True,
                status='ATIVA'
            ).first()
            
            
            if jornada_ativa:           
                
                # Se já tem jornada ativa, apenas atualizar o posto
                if hasattr(request.user, 'profile'):
                    request.user.profile.posto_trabalho = posto_trabalho
                    request.user.profile.save(update_fields=['posto_trabalho'])
                
                # Atualizar o posto na jornada ativa
                jornada_ativa.posto_trabalho = posto_trabalho
                jornada_ativa.save(update_fields=['posto_trabalho'])
                
                
                messages.success(
                    request, f"Posto alterado com sucesso: {posto_trabalho.nome}"
                )
            else:
               
                
                # Verificar se há jornadas não finalizadas e finalizá-las
                jornadas_nao_finalizadas = RegistroJornada.objects.filter(
                    user=request.user, 
                    horario_fim__isnull=True,
                    status='ATIVA'
                )             
                
                
                if jornadas_nao_finalizadas.exists():               
                    # Finalizar todas as jornadas não finalizadas
                    jornadas_nao_finalizadas.update(
                        horario_fim=timezone.now(),
                        status='FINALIZADA'
                    )
                
                # Atualiza o profile com o novo posto
                if hasattr(request.user, 'profile'):                    
                    request.user.profile.posto_trabalho = posto_trabalho
                    request.user.profile.save(update_fields=['posto_trabalho'])
                
                
                try:
                    with transaction.atomic():
                        
                        jornada_ativa_check = RegistroJornada.objects.filter(
                            user=request.user,
                            horario_fim__isnull=True,
                            status='ATIVA'
                        ).first()
                        
                        if jornada_ativa_check:    
                            
                            jornada_ativa_check.posto_trabalho = posto_trabalho
                            jornada_ativa_check.save(update_fields=['posto_trabalho'])                        
                            
                            messages.success(
                                request, f"Posto atualizado na jornada ativa: {posto_trabalho.nome}"
                            )
                        else:
                            horario_inicio = timezone.now()
                            
                            nova_jornada = RegistroJornada.objects.create(
                                user=request.user,
                                posto_trabalho=posto_trabalho,
                                horario_inicio=horario_inicio,
                                horario_fim=None,  # Garantir que não seja finalizada
                                status='ATIVA'  # Garantir status correto
                            )                            
                            messages.success(
                                request, f"Jornada iniciada no posto: {posto_trabalho.nome}"
                            )
                except Exception as e:
                    
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse({
                            "success": False,
                            "message": f"Erro ao criar jornada: {str(e)}"
                        })
                    else:
                        messages.error(request, f"Erro ao criar jornada: {str(e)}")
                        return redirect('participante:selecionar_posto')
           
            
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "success": True,
                    "message": f"Posto selecionado com sucesso: {posto_trabalho.nome}"
                })
            else:
                if request.user.is_superuser or request.user.is_staff:
                    redirect_url = reverse("lojista:homepage")               
                else:  # Participante comum
                    redirect_url = reverse("participante:dashboard")      
            
            return redirect(redirect_url)
        else:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "success": False,
                    "message": "Por favor, selecione um posto de trabalho."
                })
            else:
                messages.error(request, "Por favor, selecione um posto de trabalho.")
                return redirect('participante:selecionar_posto')

    postos = PostoTrabalho.objects.all()
    context = {
        'postos': postos,
        'current_time': timezone.now(),
    }   
    return render(request, "participante/selecionar_posto_clean.html", context)


@login_required
def jornada_status(request):
    """View para verificar o status da jornada do usuário via AJAX"""
    from participante.models import RegistroJornada
    
    # Verificar se há jornada ativa
    jornada_ativa = RegistroJornada.objects.filter(
        user=request.user,
        horario_fim__isnull=True
    ).first()
    
    return JsonResponse({
        'jornada_ativa': jornada_ativa is not None,
        'jornada_id': jornada_ativa.id if jornada_ativa else None,
        'posto_atual': jornada_ativa.posto_trabalho.nome if jornada_ativa and jornada_ativa.posto_trabalho else None,
        'horario_inicio': jornada_ativa.horario_inicio.isoformat() if jornada_ativa else None
    })


@login_required
def finalizar_jornada_colaborador(request):
    """View para finalizar a jornada do colaborador"""
    if request.method == "POST":
        from participante.models import RegistroJornada
        
        # Verificar se tem jornada ativa para finalizar
        jornada_ativa = RegistroJornada.objects.filter(
            user=request.user,
            status='ATIVA',
            horario_fim__isnull=True
        ).first()
        
        if not jornada_ativa:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "success": False,
                    "message": "Você não possui uma jornada ativa para finalizar."
                })
            else:
                messages.warning(request, "Você não possui uma jornada ativa para finalizar.")
                return redirect('participante:dashboard')
        
        # Usar a jornada ativa já encontrada
        if jornada_ativa:
            try:
                # Finalizar a jornada
                jornada_ativa.horario_fim = timezone.now()
                jornada_ativa.status = 'FINALIZADA'
                jornada_ativa.save()
                
                # Limpar posto de trabalho do profile
                limpar_posto_trabalho(request.user)
                
                
                # Fazer logout do usuário após finalizar jornada
                from django.contrib.auth import logout
                logout(request)
                
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({
                        "success": True,
                        "message": "Jornada finalizada com sucesso! Você foi desconectado.",
                        "redirect": "/"
                    })
                else:
                    messages.success(request, "Jornada finalizada com sucesso! Você foi desconectado.")
                    return redirect('/')
                    
            except Exception as e:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({
                        "success": False,
                        "message": f"Erro ao finalizar jornada: {str(e)}"
                    })
                else:
                    messages.error(request, f"Erro ao finalizar jornada: {str(e)}")
                    return redirect('lojista:homepage')
        else:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "success": False,
                    "message": "Nenhuma jornada ativa encontrada."
                })
            else:
                messages.warning(request, "Nenhuma jornada ativa encontrada.")
                return redirect('lojista:homepage')
    
    return redirect('lojista:homepage')


@login_required
@csrf_exempt
def confirmar_jornada(request):
    if request.method == "POST":
        acao = request.POST.get("acao")
        posto_trabalho = request.user.profile.posto_trabalho

        if acao == "iniciar":

            jornada_ativa = RegistroJornada.objects.filter(
                user=request.user, horario_fim__isnull=True
            ).exists()

            if jornada_ativa:

                return JsonResponse(
                    {"error": "Já existe uma jornada ativa para o usuário"}, status=400
                )

            # Se não há jornada ativa, iniciar uma nova jornada
            RegistroJornada.objects.create(
                user=request.user,
                posto_trabalho=posto_trabalho,
                horario_inicio=timezone.now(),
            )
            return JsonResponse({"status": "iniciado"})

        elif acao == "finalizar":

            jornada = RegistroJornada.objects.filter(
                user=request.user, horario_fim__isnull=True
            ).first()

            if jornada:
                jornada.horario_fim = timezone.now()
                jornada.save()

                logout(request)
                return JsonResponse({"status": "finalizado"})
            else:

                return JsonResponse(
                    {"error": "Nenhuma jornada ativa encontrada para finalizar"},
                    status=400,
                )

    return JsonResponse({"error": "Ação inválida ou método não permitido"}, status=400)


