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


from .utils import execute_with_celery_fallback

def total_horas_trabalhadas(user):
    registros = RegistroJornada.objects.filter(user=user).exclude(horario_fim=None)
    total = timedelta()
    for reg in registros:
        total += reg.calcular_duracao()
    return total


@login_required
def gerar_pdf_batidas(request):
    user_id = request.user.id

    # Chama a task para gerar o PDF
    pdf_data = gerar_pdf_batidas_task(user_id)

    # Retorna o PDF como resposta
    response = HttpResponse(pdf_data, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="registro-ponto.pdf"'
    return response


def formatar_timedelta_em_horas(duracao):
    if not duracao or duracao.total_seconds() <= 0:
        return "0 horas"

    total_horas, resto = divmod(duracao.total_seconds(), 3600)
    minutos, segundos = divmod(resto, 60)

    partes = [f"{int(total_horas)} horas"]
    if minutos > 0:
        partes.append(f"{int(minutos)} minutos")
    if segundos > 0:
        partes.append(f"{int(segundos)} segundos")

    return ", ".join(partes)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name="Gerentes").exists())
def gerar_pdf_batidas_filtros(request):
    try:
        # Captura todos os filtros aplicados
        data_inicio = request.GET.get("data_inicio", "").strip()
        data_fim = request.GET.get("data_fim", "").strip()
        posto_trabalho_id = request.GET.get("posto_trabalho", "").strip()
        search_query = request.GET.get("search", "").strip()

        # Trata valores vazios ou "None"
        if posto_trabalho_id == "None" or not posto_trabalho_id:
            posto_trabalho_id = ""

        # Cria um dicionário com todos os filtros
        filtros = {
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "posto_trabalho_id": posto_trabalho_id,
            "search_query": search_query
        }

        try:
            # Usar a função helper com fallback automático
            pdf_data = execute_with_celery_fallback(gerar_pdf_batidas_filtros_task, filtros, request.user.id)
        except Exception as e:
            # Último fallback - execução direta
            pdf_data = gerar_pdf_batidas_filtros_task(filtros, request.user.id)

        # Retorna o PDF como resposta
        response = HttpResponse(pdf_data, content_type="application/pdf")
        response["Content-Disposition"] = (
            'attachment; filename="registro_batidas_filtros.pdf"'
        )
        return response
        
    except Exception as e:
       
        import traceback
        traceback.print_exc()
        return HttpResponse(f"Erro ao gerar PDF: {str(e)}", status=500)


@login_required
@require_POST
@csrf_exempt
def update_observacao(request):
    doc_id = request.POST.get('doc_id')
    observacao = request.POST.get('observacao', '').strip()

    try:
        documento = get_object_or_404(DocumentoFiscal, id=doc_id)
        documento.observacao = observacao
        # Quando o participante atualiza, muda o status para PENDENTE
        documento.status = StatusChoices.PENDENTE
        documento.corrigido_pelo_participante = True
        documento.data_atualizacao = timezone.now()
        documento.save()
        
        messages.success(request, "Documento atualizado com sucesso! Aguarde a nova análise.")
        return JsonResponse({
            'success': True, 
            'message': 'Documento atualizado com sucesso! Aguarde a nova análise.',
            'status': documento.get_status_display()
        })
    except Exception as e:
        messages.error(request, f"Erro ao atualizar documento: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': f'Erro ao atualizar documento: {str(e)}'
        }, status=400)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name="Gerentes").exists())
def registro_ponto_filtros(request):
    try:
        # Obtém os parâmetros do filtro
        data_inicio = request.GET.get("data_inicio")
        data_fim = request.GET.get("data_fim")
        colaborador_id = request.GET.get("colaborador")
        posto_id = request.GET.get("posto")
        status = request.GET.get("status")
        jornada_id = request.GET.get("jornada")

        # Inicia a query base - apenas colaboradores
        registros = RegistroJornada.objects.filter(
            user__profile__is_colaborador=True
        ).order_by("-horario_inicio")

        # Aplica os filtros
        if data_inicio:
            try:
                data_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
                registros = registros.filter(horario_inicio__date__gte=data_inicio)
            except ValueError:
                pass

        if data_fim:
            try:
                data_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
                registros = registros.filter(horario_fim__date__lte=data_fim)
            except ValueError:
                pass

        if colaborador_id:
            registros = registros.filter(user_id=colaborador_id)

        if posto_id:
            registros = registros.filter(posto_trabalho_id=posto_id)

        if status:
            if status == "completo":
                registros = registros.filter(horario_inicio__isnull=False, horario_fim__isnull=False)
            elif status == "em_andamento":
                registros = registros.filter(horario_inicio__isnull=False, horario_fim__isnull=True)

        if jornada_id:
            registros = registros.filter(jornada_id=jornada_id)

        # Calcula o total de horas para cada registro
        for registro in registros:
            if registro.horario_fim:
                duracao = registro.horario_fim - registro.horario_inicio
                registro.duracao_formatada = formatar_timedelta_em_horas(duracao)
            else:
                registro.duracao_formatada = "Em andamento"

        # Prepara o contexto
        context = {
            "registros": registros,
            "colaboradores": User.objects.filter(profile__is_colaborador=True).order_by('profile__nome'),
            "postos": PostoTrabalho.objects.all().order_by('nome'),
            "jornadas": TipoJornada.objects.filter(ativo=True).order_by('nome'),
        }

        return render(request, "participante/registro_ponto_filtros.html", context)
        
    except Exception as e:
        
        import traceback
        traceback.print_exc()
        
        # Retorna contexto vazio em caso de erro
        context = {
            "registros": [],
            "colaboradores": User.objects.filter(profile__is_colaborador=True).order_by('profile__nome'),
            "postos": PostoTrabalho.objects.all().order_by('nome'),
            "jornadas": TipoJornada.objects.filter(ativo=True).order_by('nome'),
        }
        
        return render(request, "participante/registro_ponto_filtros.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def registro_ponto(request):
    registros = RegistroJornada.objects.filter(user=request.user).order_by(
        "-horario_inicio"
    )

    duracao_total = timedelta()
    for registro in registros:
        duracao = registro.calcular_duracao()
        if duracao:
            duracao_total += duracao
        registro.duracao_formatada = formatar_duracao(duracao)

    # Formata a duração total
    total_horas_formatado = formatar_duracao(duracao_total)

    paginator = Paginator(registros, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "total_horas_formatado": total_horas_formatado,
    }
    return render(request, "lojista/listar_batidas.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def gerenciar_colaboradores(request):
    """
    View para gerenciar colaboradores da equipe interna.
    
    Funcionalidades:
    - Alterar grupos/funções dos colaboradores
    - Ativar/desativar colaboradores
    - Redefinir senhas
    - Buscar e filtrar colaboradores
    
    Permissões: superuser, staff
    Tags: gestao, colaboradores, rh
    """
    from django.contrib.auth.models import Group
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.db.models import Q
    
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        
        try:
            user = User.objects.get(id=user_id)
            
            if action == 'change_group':
                new_group_id = request.POST.get('new_group')
                if new_group_id:
                    new_group = Group.objects.get(id=new_group_id)
                    
                    # Remove todos os grupos atuais
                    user.groups.clear()
                    
                    # Adiciona o novo grupo
                    user.groups.add(new_group)
                    
                    messages.success(request, f'Grupo do usuário {user.username} alterado para {new_group.name}')
                else:
                    messages.error(request, 'Por favor, selecione um grupo válido')
                    
            elif action == 'remover_grupo':
                # Remove apenas o grupo específico do usuário
                group_id = request.POST.get('group_id')
                if group_id:
                    try:
                        group = Group.objects.get(id=group_id)
                        user.groups.remove(group)
                        messages.success(request, f'Grupo "{group.name}" removido do usuário {user.username}')
                    except Group.DoesNotExist:
                        messages.error(request, 'Grupo não encontrado')
                else:
                    messages.error(request, 'ID do grupo não fornecido')
                
            elif action == 'toggle_status':
                # Alternar status ativo/inativo
                profile = user.profile
                profile.ativo = not profile.ativo
                profile.save()
                
                status = "ativado" if profile.ativo else "desativado"
                messages.success(request, f'Usuário {user.username} {status} com sucesso!')
                
            elif action == 'reset_password':
                # Gerar nova senha
                import random
                import string
                new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                user.set_password(new_password)
                user.save()
                
                # Marcar como senha temporária
                if hasattr(user, 'profile'):
                    user.profile.senha_temporaria = True
                    user.profile.save()
                
                messages.success(request, f'Nova senha gerada para {user.username}: {new_password}')
                
        except (User.DoesNotExist, Group.DoesNotExist):
            messages.error(request, 'Usuário ou grupo não encontrado')
        
        # Redirecionar após POST para evitar form resubmission
        return redirect('participante:gestao_colaboradores')
    
    # Filtros
    search_query = request.GET.get('search', '')
    group_filter = request.GET.get('group', '')
    status_filter = request.GET.get('status', '')
    
    # Buscar apenas usuários colaboradores (equipe interna) - exceto superuser
    users = User.objects.filter(
        is_superuser=False,
        profile__is_colaborador=True
    ).select_related('profile').prefetch_related('groups')
    
    # Aplicar filtros
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(profile__nome__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if group_filter:
        users = users.filter(groups__name=group_filter)
    
    if status_filter == 'ativo':
        users = users.filter(profile__ativo=True)
    elif status_filter == 'inativo':
        users = users.filter(profile__ativo=False)
    
    # Garantir que o grupo Suporte existe
    from django.contrib.auth.models import Group
    suporte_group, created = Group.objects.get_or_create(name="Suporte")
    if created:
        messages.success(request, "Grupo 'Suporte' criado automaticamente!")
    
    groups = Group.objects.all()
    
    # Estatísticas - apenas colaboradores
    total_users = User.objects.filter(is_superuser=False, profile__is_colaborador=True).count()
    active_users = User.objects.filter(is_superuser=False, profile__is_colaborador=True, profile__ativo=True).count()
    inactive_users = total_users - active_users
    
    context = {
        'users': users,
        'groups': groups,
        'section': 'gestao_colaboradores',
        'search_query': search_query,
        'group_filter': group_filter,
        'status_filter': status_filter,
        'stats': {
            'total': total_users,
            'active': active_users,
            'inactive': inactive_users,
        }
    }
    
    return render(request, 'participante/manage_users.html', context)


