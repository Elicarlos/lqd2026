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


@login_required
def dashboard(request):
    """
    Dashboard adaptativo que mostra informações relevantes baseadas no papel do usuário.
    Agora inclui listagem dos documentos fiscais do participante e métricas para os cards do dashboard.
    """
    
    # Cards do dashboard agora são gerenciados pelo sistema CardDinamico
    # Não é mais necessário chamar setup_dashboard_cards_auto()
    context = {
        "section": "dashboard",
        "user_roles": get_user_roles(request.user),
        "is_gerente": is_gerente(request.user),
        "is_supervisor": is_supervisor(request.user),
        "is_backoffice": is_backoffice(request.user),
        "is_operador": is_operador(request.user),
        "is_gerente_solve": is_gerente_solve(request.user),
        "is_recursos_humanos": is_recursos_humanos(request.user),
    }

    if request.user.is_superuser:
        return redirect("lojista:homepage")

    # Buscar documentos fiscais do participante logado
    docs_list = DocumentoFiscal.objects.filter(user=request.user).order_by("-dataCadastro")

    # Métricas para os cards
    total_docs = docs_list.count()
    validated_docs = docs_list.filter(status=StatusChoices.VALIDADO).count()
    pending_docs = docs_list.filter(status=StatusChoices.PENDENTE).count()

    # Participante comum
    if not request.user.is_staff:
        docs_list = DocumentoFiscal.objects.filter(user=request.user).annotate(
            has_unprinted_cupons=Exists(
                Cupom.objects.filter(
                    documentoFiscal=OuterRef("id"),
                    impresso=False,  # Apenas cupons não impressos
                )
            )
        ).order_by("-dataCadastro")
        
        # Paginação
        paginator = Paginator(docs_list, 10)  # 10 documentos por página
        page_number = request.GET.get('page')
        docs = paginator.get_page(page_number)
        
        # Calcular total de cupons
        total_cupons = 0
        for doc in docs_list:
            if doc.status == StatusChoices.VALIDADO:
                total_cupons += doc.get_cupons()
        
        context.update(
            {
                "docs": docs,
                "total_docs": total_docs,
                "validated_docs": validated_docs,
                "pending_docs": pending_docs,
                "total_cupons": total_cupons,
            }
        )
        return render(request, "participante/dashboard-new.html", context)

    # Métricas comuns para staff
    
    if any([context["is_gerente"], context["is_supervisor"], context["is_backoffice"]]):
        hoje = timezone.now().date()
        context.update(
            {
                "total_users": User.objects.count(),
                "total_docs": DocumentoFiscal.objects.count(),
                "docs_hoje": DocumentoFiscal.objects.filter(
                    dataCadastro__date=hoje
                ).count(),
                "docs_pendentes": DocumentoFiscal.objects.filter(status=StatusChoices.PENDENTE).count(),
                "total_lojas": Lojista.objects.count(),
                "lojas_ativas": Lojista.objects.filter(status="Sim").count(),
            }
        )

    # Informações específicas por papel
    if context["is_operador"]:
        hoje = timezone.now().date()
        docs_hoje = DocumentoFiscal.objects.filter(
            dataCadastro__date=hoje, user=request.user
        ).order_by("-dataCadastro")

        context.update(
            {
                "docs_hoje": docs_hoje,
                "total_docs_hoje": docs_hoje.count(),
                        "docs_pendentes": docs_hoje.filter(status=StatusChoices.PENDENTE).count(),
        "docs_aprovados": docs_hoje.filter(status="validado").count(),
            }
        )

    if context["is_backoffice"]:
        docs_pendentes = DocumentoFiscal.objects.filter(status=StatusChoices.PENDENTE, enviado_por_operador=False).order_by(
            "-dataCadastro"
        )
        
        context.update(
            {
                "docs_pendentes_list": docs_pendentes[:50],  # Limita a 50 mais recentes
                "total_pendentes": docs_pendentes.count(),
            }
        )

    if context["is_gerente"] or context["is_supervisor"]:
        # Adiciona métricas avançadas
        context.update(
            {
                "media_docs_dia": DocumentoFiscal.objects.filter(
                    dataCadastro__date=timezone.now().date()
                ).count()
                / max(User.objects.filter(is_staff=True).count(), 1),
                "operadores_ativos": User.objects.filter(
                    groups__name="Operador", is_active=True
                ).count(),
            }
        )

    # Registro de ponto (para todos os funcionários)
    if request.user.is_staff:
        jornada_atual = RegistroJornada.objects.filter(
            user=request.user, horario_fim__isnull=True
        ).first()

        context.update(
            {
                "jornada_atual": jornada_atual,
                "posto_trabalho": request.user.profile.posto_trabalho,
            }
        )

    return render(request, "participante/dashboard.html", context)


# Funções auxiliares para o dashboard
def get_dashboard_reports():
    """Retorna relatórios e estatísticas do dashboard."""
    # Implementar lógica de relatórios aqui
    return {}


def get_users_metrics():
    """Retorna métricas de usuários."""
    # Implementar lógica de métricas aqui
    return {}


def get_pending_documents():
    """Retorna documentos pendentes."""
    # Implementar lógica de documentos pendentes aqui
    return {}


def get_pending_requests():
    """Retorna solicitações pendentes."""
    # Implementar lógica de solicitações pendentes aqui
    return {}


@login_required
def lojista(request):
    return render(request, "not_found.html", {"section": "coupons"})


@login_required
def coupons(request):
    return render(request, "participante/coupons.html", {"section": "coupons"})


@login_required
def premios(request):
    return render(request, "participante/premios.html", {"section": "premios"})


def resumo_lojistas(request):
    # documento = Momde
    return render(request, "dash/tables.html")


@login_required
@user_passes_test(lambda u: u.is_superuser)
def manage_roles(request):
    """
    View para gerenciar funções e permissões do sistema.
    Apenas superusuários podem acessar esta view.
    """
    # Estrutura de permissões disponíveis
    available_permissions = {
        "Dashboard": [
            {"id": "view_dashboard", "name": "Visualizar Dashboard"},
            {"id": "view_reports", "name": "Visualizar Relatórios"},
            {"id": "manage_users", "name": "Gerenciar Usuários"},
        ],
        "Documentos": [
            {"id": "add_document", "name": "Adicionar Documentos"},
            {"id": "edit_document", "name": "Editar Documentos"},
            {"id": "delete_document", "name": "Excluir Documentos"},
            {"id": "validate_document", "name": "Validar Documentos"},
        ],
        "Lojistas": [
            {"id": "view_stores", "name": "Visualizar Lojistas"},
            {"id": "add_store", "name": "Adicionar Lojista"},
            {"id": "edit_store", "name": "Editar Lojista"},
            {"id": "delete_store", "name": "Excluir Lojista"},
        ],
        "Sistema": [
            {"id": "manage_settings", "name": "Gerenciar Configurações"},
            {"id": "view_logs", "name": "Visualizar Logs"},
            {"id": "manage_roles", "name": "Gerenciar Funções"},
        ],
    }

    # Recursos do sistema disponíveis
    available_resources = [
        {"id": "dashboard", "name": "Dashboard", "icon": "fas fa-tachometer-alt"},
        {"id": "documents", "name": "Documentos", "icon": "fas fa-file-alt"},
        {"id": "reports", "name": "Relatórios", "icon": "fas fa-chart-bar"},
        {"id": "users", "name": "Usuários", "icon": "fas fa-users"},
        {"id": "stores", "name": "Lojistas", "icon": "fas fa-store"},
        {"id": "settings", "name": "Configurações", "icon": "fas fa-cogs"},
        {"id": "logs", "name": "Logs do Sistema", "icon": "fas fa-clipboard-list"},
    ]

    # Exemplo de funções (em produção, viriam do banco de dados)
    roles = [
        {
            "id": 1,
            "name": "Operador",
            "is_system_role": True,
            "permissions": ["view_dashboard", "add_document", "edit_document"],
            "resources": [
                {"name": "Dashboard", "icon": "fas fa-tachometer-alt"},
                {"name": "Documentos", "icon": "fas fa-file-alt"},
            ],
            "users": [
                {"name": "João Silva", "initials": "JS"},
                {"name": "Maria Santos", "initials": "MS"},
            ],
        },
        {
            "id": 2,
            "name": "Gerente",
            "is_system_role": True,
            "permissions": [
                "view_dashboard",
                "view_reports",
                "manage_users",
                "validate_document",
            ],
            "resources": [
                {"name": "Dashboard", "icon": "fas fa-tachometer-alt"},
                {"name": "Relatórios", "icon": "fas fa-chart-bar"},
                {"name": "Usuários", "icon": "fas fa-users"},
            ],
            "users": [
                {"name": "Carlos Oliveira", "initials": "CO"},
            ],
        },
        {
            "id": 3,
            "name": "Backoffice",
            "is_system_role": True,
            "permissions": ["view_dashboard", "validate_document", "view_stores"],
            "resources": [
                {"name": "Dashboard", "icon": "fas fa-tachometer-alt"},
                {"name": "Documentos", "icon": "fas fa-file-alt"},
                {"name": "Lojistas", "icon": "fas fa-store"},
            ],
            "users": [
                {"name": "Ana Paula", "initials": "AP"},
                {"name": "Pedro Santos", "initials": "PS"},
                {"name": "Lucia Ferreira", "initials": "LF"},
            ],
        },
    ]

    context = {
        "roles": roles,
        "available_permissions": available_permissions,
        "available_resources": available_resources,
    }

    return render(request, "participante/role_management.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def funcionalidades_list(request):
    """Lista todas as funcionalidades do sistema"""
    from participante.models import Funcionalidade
    from django.contrib.auth.models import Group
    
    # Filtros
    tipo_filter = request.GET.get('tipo')
    grupo_filter = request.GET.get('grupo')
    status_filter = request.GET.get('status')
    search = request.GET.get('search')
    
    funcionalidades = Funcionalidade.objects.all()
    
    # Aplicar filtros
    if tipo_filter:
        funcionalidades = funcionalidades.filter(tipo=tipo_filter)
    
    if grupo_filter:
        funcionalidades = funcionalidades.filter(grupos_permitidos__name=grupo_filter)
    
    if status_filter == 'ativo':
        funcionalidades = funcionalidades.filter(ativo=True)
    elif status_filter == 'inativo':
        funcionalidades = funcionalidades.filter(ativo=False)
    
    if search:
        funcionalidades = funcionalidades.filter(
            Q(nome__icontains=search) | 
            Q(codigo__icontains=search) | 
            Q(descricao__icontains=search)
        )
    
    # Paginação
    paginator = Paginator(funcionalidades, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estatísticas
    total_funcionalidades = funcionalidades.count()
    ativas = funcionalidades.filter(ativo=True).count()
    inativas = funcionalidades.filter(ativo=False).count()
    
    # Opções para filtros
    grupos = Group.objects.all().order_by('name')
    tipos = Funcionalidade.TIPO_CHOICES
    
    context = {
        'page_obj': page_obj,
        'total_funcionalidades': total_funcionalidades,
        'ativas': ativas,
        'inativas': inativas,
        'grupos': grupos,
        'tipos': tipos,
        'filtros': {
            'tipo': tipo_filter,
            'grupo': grupo_filter,
            'status': status_filter,
            'search': search,
        },
        'section': 'funcionalidades'
    }
    
    return render(request, 'participante/funcionalidades_list.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def funcionalidade_create(request):
    """Criar nova funcionalidade"""
    from participante.models import Funcionalidade
    from django.contrib.auth.models import Group
    
    if request.method == 'POST':
        try:
            # Criar funcionalidade
            funcionalidade = Funcionalidade.objects.create(
                nome=request.POST.get('nome'),
                descricao=request.POST.get('descricao', ''),
                codigo=request.POST.get('codigo'),
                tipo=request.POST.get('tipo'),
                modelo=request.POST.get('modelo', ''),
                ativo=request.POST.get('ativo') == 'on'
            )
            
            # Adicionar grupos permitidos
            grupos_ids = request.POST.getlist('grupos_permitidos')
            if grupos_ids:
                grupos = Group.objects.filter(id__in=grupos_ids)
                funcionalidade.grupos_permitidos.set(grupos)
            
            # Adicionar usuários permitidos
            usuarios_ids = request.POST.getlist('usuarios_permitidos')
            if usuarios_ids:
                usuarios = User.objects.filter(id__in=usuarios_ids)
                funcionalidade.usuarios_permitidos.set(usuarios)
            
            # Adicionar usuários excluídos
            usuarios_excluidos_ids = request.POST.getlist('usuarios_excluidos')
            if usuarios_excluidos_ids:
                usuarios_excluidos = User.objects.filter(id__in=usuarios_excluidos_ids)
                funcionalidade.usuarios_excluidos.set(usuarios_excluidos)
            
            messages.success(request, f'Funcionalidade "{funcionalidade.nome}" criada com sucesso!')
            return redirect('participante:funcionalidades_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao criar funcionalidade: {str(e)}')
    
    # Dados para o formulário
    grupos = Group.objects.all().order_by('name')
    usuarios = User.objects.filter(is_active=True, is_staff=True).order_by('username')
    tipos = Funcionalidade.TIPO_CHOICES
    
    context = {
        'grupos': grupos,
        'usuarios': usuarios,
        'tipos': tipos,
        'section': 'funcionalidades'
    }
    
    return render(request, 'participante/funcionalidade_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def funcionalidade_edit(request, pk):
    """Editar funcionalidade existente"""
    from participante.models import Funcionalidade
    from django.contrib.auth.models import Group
    
    funcionalidade = get_object_or_404(Funcionalidade, pk=pk)
    
    if request.method == 'POST':
        try:
            # Atualizar funcionalidade
            funcionalidade.nome = request.POST.get('nome')
            funcionalidade.descricao = request.POST.get('descricao', '')
            funcionalidade.codigo = request.POST.get('codigo')
            funcionalidade.tipo = request.POST.get('tipo')
            funcionalidade.modelo = request.POST.get('modelo', '')
            funcionalidade.ativo = request.POST.get('ativo') == 'on'
            funcionalidade.save()
            
            # Atualizar grupos permitidos
            grupos_ids = request.POST.getlist('grupos_permitidos')
            grupos = Group.objects.filter(id__in=grupos_ids)
            funcionalidade.grupos_permitidos.set(grupos)
            
            # Atualizar usuários permitidos
            usuarios_ids = request.POST.getlist('usuarios_permitidos')
            usuarios = User.objects.filter(id__in=usuarios_ids)
            funcionalidade.usuarios_permitidos.set(usuarios)
            
            # Atualizar usuários excluídos
            usuarios_excluidos_ids = request.POST.getlist('usuarios_excluidos')
            usuarios_excluidos = User.objects.filter(id__in=usuarios_excluidos_ids)
            funcionalidade.usuarios_excluidos.set(usuarios_excluidos)
            
            messages.success(request, f'Funcionalidade "{funcionalidade.nome}" atualizada com sucesso!')
            return redirect('participante:funcionalidades_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao atualizar funcionalidade: {str(e)}')
    
    # Dados para o formulário
    grupos = Group.objects.all().order_by('name')
    usuarios = User.objects.filter(is_active=True, is_staff=True).order_by('username')
    tipos = Funcionalidade.TIPO_CHOICES
    
    context = {
        'funcionalidade': funcionalidade,
        'grupos': grupos,
        'usuarios': usuarios,
        'tipos': tipos,
        'section': 'funcionalidades'
    }
    
    return render(request, 'participante/funcionalidade_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def funcionalidade_delete(request, pk):
    """Excluir funcionalidade"""
    from participante.models import Funcionalidade
    
    funcionalidade = get_object_or_404(Funcionalidade, pk=pk)
    
    if request.method == 'POST':
        try:
            nome = funcionalidade.nome
            funcionalidade.delete()
            messages.success(request, f'Funcionalidade "{nome}" excluída com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao excluir funcionalidade: {str(e)}')
    
    return redirect('participante:funcionalidades_list')


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def cards_list(request):
    """Lista todos os cards do sistema"""
    from participante.models import CardDinamico
    from django.contrib.auth.models import Group
    
    # Filtros
    tipo_filter = request.GET.get('tipo')
    grupo_filter = request.GET.get('grupo')
    status_filter = request.GET.get('status')
    search = request.GET.get('search')
    
    cards = CardDinamico.objects.all()
    
    # Aplicar filtros
    if tipo_filter:
        cards = cards.filter(tipo=tipo_filter)
    
    if grupo_filter:
        cards = cards.filter(grupos_permitidos__name=grupo_filter)
    
    if status_filter == 'ativo':
        cards = cards.filter(ativo=True)
    elif status_filter == 'inativo':
        cards = cards.filter(ativo=False)
    
    if search:
        cards = cards.filter(
            Q(nome__icontains=search) | 
            Q(titulo__icontains=search) | 
            Q(descricao__icontains=search)
        )
    
    # Paginação
    paginator = Paginator(cards, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estatísticas
    total_cards = cards.count()
    ativos = cards.filter(ativo=True).count()
    inativos = cards.filter(ativo=False).count()
    
    # Opções para filtros
    grupos = Group.objects.all().order_by('name')
    tipos = CardDinamico.TIPO_CHOICES
    
    context = {
        'page_obj': page_obj,
        'total_cards': total_cards,
        'ativos': ativos,
        'inativos': inativos,
        'grupos': grupos,
        'tipos': tipos,
        'filtros': {
            'tipo': tipo_filter,
            'grupo': grupo_filter,
            'status': status_filter,
            'search': search,
        },
        'section': 'cards'
    }
    
    return render(request, 'participante/cards_list.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def card_create(request):
    """Criar novo card"""
    from participante.models import CardDinamico
    from django.contrib.auth.models import Group
    
    if request.method == 'POST':
        try:
            # DEBUG: Log dos dados recebidos
       
            
            # Criar card
            card = CardDinamico.objects.create(
                nome=request.POST.get('nome'),
                titulo=request.POST.get('titulo'),
                descricao=request.POST.get('descricao', ''),
                tipo=request.POST.get('tipo'),
                icone=request.POST.get('icone'),
                cor=request.POST.get('cor', 'primary'),
                url=request.POST.get('url', ''),
                ordem=int(request.POST.get('ordem', 0)),
                ativo=request.POST.get('ativo') == 'on',
                mostrar_apenas_admin=request.POST.get('mostrar_apenas_admin') == 'on',
                mostrar_apenas_staff=request.POST.get('mostrar_apenas_staff') == 'on'
            )
            
       
            
            # Adicionar grupos permitidos
            grupos_ids = request.POST.getlist('grupos_permitidos')
            if grupos_ids:
                grupos = Group.objects.filter(id__in=grupos_ids)
                card.grupos_permitidos.set(grupos)
            
            # Adicionar usuários permitidos
            usuarios_ids = request.POST.getlist('usuarios_permitidos')
            if usuarios_ids:
                usuarios = User.objects.filter(id__in=usuarios_ids)
                card.usuarios_permitidos.set(usuarios)
            
            # Adicionar usuários excluídos
            usuarios_excluidos_ids = request.POST.getlist('usuarios_excluidos')
            if usuarios_excluidos_ids:
                usuarios_excluidos = User.objects.filter(id__in=usuarios_excluidos_ids)
                card.usuarios_excluidos.set(usuarios_excluidos)
            
            # Configurar seção do dashboard
            secao_dashboard = request.POST.get('secao_dashboard')
            if secao_dashboard:
                from participante.models import ConfiguracaoSecao
                secao, created = ConfiguracaoSecao.objects.get_or_create(
                    tipo=secao_dashboard,
                    defaults={
                        'titulo': secao_dashboard.title(),
                        'icone': 'fas fa-cog',
                        'cor': 'primary',
                        'ativo': True,
                        'ordem': 0
                    }
                )
                
                # Atualizar configurações da seção se fornecidas
                secao_cor = request.POST.get('secao_cor')
                if secao_cor:
                    secao.cor = secao_cor
                
                secao_grupos_ids = request.POST.getlist('secao_grupos_permitidos')
                if secao_grupos_ids:
                    secao_grupos = Group.objects.filter(id__in=secao_grupos_ids)
                    secao.grupos_permitidos.set(secao_grupos)
                
                secao.save()
            
            messages.success(request, f'Card "{card.nome}" criado com sucesso!')
            return redirect('participante:cards_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao criar card: {str(e)}')
    
    # Dados para o formulário
    grupos = Group.objects.all().order_by('name')
    usuarios = User.objects.filter(is_active=True, is_staff=True).order_by('username')
    tipos = CardDinamico.TIPO_CHOICES
    icones = CardDinamico.ICONE_CHOICES
    
    context = {
        'grupos': grupos,
        'usuarios': usuarios,
        'tipos': tipos,
        'icones': icones,
        'section': 'cards'
    }
    
    return render(request, 'participante/card_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def card_edit(request, pk):
    """Editar card existente"""
    from participante.models import CardDinamico
    from django.contrib.auth.models import Group
    
    card = get_object_or_404(CardDinamico, pk=pk)
    
    if request.method == 'POST':
        try:
            # DEBUG: Log dos dados recebidos
            
            # Atualizar card
            card.nome = request.POST.get('nome')
            card.titulo = request.POST.get('titulo')
            card.descricao = request.POST.get('descricao', '')
            card.tipo = request.POST.get('tipo')
            card.icone = request.POST.get('icone')
            card.cor = request.POST.get('cor', 'primary')
            card.url = request.POST.get('url', '')
            card.ordem = int(request.POST.get('ordem', 0))
            card.ativo = request.POST.get('ativo') == 'on'
            card.mostrar_apenas_admin = request.POST.get('mostrar_apenas_admin') == 'on'
            card.mostrar_apenas_staff = request.POST.get('mostrar_apenas_staff') == 'on'
            card.save()
            
           
            
            # Atualizar grupos permitidos
            grupos_ids = request.POST.getlist('grupos_permitidos')
            grupos = Group.objects.filter(id__in=grupos_ids)
            card.grupos_permitidos.set(grupos)
            
            # Atualizar usuários permitidos
            usuarios_ids = request.POST.getlist('usuarios_permitidos')
            usuarios = User.objects.filter(id__in=usuarios_ids)
            card.usuarios_permitidos.set(usuarios)
            
            # Atualizar usuários excluídos
            usuarios_excluidos_ids = request.POST.getlist('usuarios_excluidos')
            usuarios_excluidos = User.objects.filter(id__in=usuarios_excluidos_ids)
            card.usuarios_excluidos.set(usuarios_excluidos)
            
            # Configurar seção do dashboard
            secao_dashboard = request.POST.get('secao_dashboard')
            if secao_dashboard:
                from participante.models import ConfiguracaoSecao
                secao, created = ConfiguracaoSecao.objects.get_or_create(
                    tipo=secao_dashboard,
                    defaults={
                        'titulo': secao_dashboard.title(),
                        'icone': 'fas fa-cog',
                        'cor': 'primary',
                        'ativo': True,
                        'ordem': 0
                    }
                )
                
                # Atualizar configurações da seção se fornecidas
                secao_cor = request.POST.get('secao_cor')
                if secao_cor:
                    secao.cor = secao_cor
                
                secao_grupos_ids = request.POST.getlist('secao_grupos_permitidos')
                if secao_grupos_ids:
                    secao_grupos = Group.objects.filter(id__in=secao_grupos_ids)
                    secao.grupos_permitidos.set(secao_grupos)
                
                secao.save()
            
            messages.success(request, f'Card "{card.nome}" atualizado com sucesso!')
            return redirect('participante:cards_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao atualizar card: {str(e)}')
    
    # Dados para o formulário
    grupos = Group.objects.all().order_by('name')
    usuarios = User.objects.filter(is_active=True, is_staff=True).order_by('username')
    tipos = CardDinamico.TIPO_CHOICES
    icones = CardDinamico.ICONE_CHOICES
    
    context = {
        'card': card,
        'grupos': grupos,
        'usuarios': usuarios,
        'tipos': tipos,
        'icones': icones,
        'section': 'cards'
    }
    
    return render(request, 'participante/card_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def card_delete(request, pk):
    """Excluir card"""
    from participante.models import CardDinamico
    
    card = get_object_or_404(CardDinamico, pk=pk)
    
    if request.method == 'POST':
        try:
            nome = card.nome
            card.delete()
            messages.success(request, f'Card "{nome}" excluído com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao excluir card: {str(e)}')
    
    return redirect('participante:cards_list')


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def reorder_cards(request):
    """Reordenar cards via AJAX"""
    if request.method == 'POST':
        try:
            card_orders = request.POST.getlist('card_orders[]')
            
            for order_data in card_orders:
                card_id, new_order = order_data.split(':')
                from participante.models import CardDinamico
                card = CardDinamico.objects.get(id=card_id)
                card.ordem = int(new_order)
                card.save()
            
            return JsonResponse({'success': True, 'message': 'Ordem dos cards atualizada!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def secoes_list(request):
    """Lista todas as configurações de seções"""
    from participante.models import ConfiguracaoSecao
    from django.contrib.auth.models import Group
    
    secoes = ConfiguracaoSecao.objects.all().order_by('ordem')
    grupos = Group.objects.all().order_by('name')
    
    context = {
        'secoes': secoes,
        'grupos': grupos,
        'section': 'secoes'
    }
    
    return render(request, 'participante/secoes_list.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def secao_edit(request, pk):
    """Editar configuração de seção"""
    from participante.models import ConfiguracaoSecao
    from django.contrib.auth.models import Group
    
    secao = get_object_or_404(ConfiguracaoSecao, pk=pk)
    
    if request.method == 'POST':
        try:
            # Atualizar seção
            secao.titulo = request.POST.get('titulo')
            secao.icone = request.POST.get('icone')
            secao.cor = request.POST.get('cor')
            secao.ordem = int(request.POST.get('ordem', 0))
            secao.ativo = request.POST.get('ativo') == 'on'
            secao.save()
            
            # Atualizar grupos permitidos
            grupos_ids = request.POST.getlist('grupos_permitidos')
            grupos = Group.objects.filter(id__in=grupos_ids)
            secao.grupos_permitidos.set(grupos)
            
            messages.success(request, f'Seção "{secao.titulo}" atualizada com sucesso!')
            return redirect('participante:secoes_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao atualizar seção: {str(e)}')
    
    grupos = Group.objects.all().order_by('name')
    
    context = {
        'secao': secao,
        'grupos': grupos,
        'section': 'secoes'
    }
    
    return render(request, 'participante/secao_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def secao_toggle(request, pk):
    """Ativar/desativar seção"""
    from participante.models import ConfiguracaoSecao
    
    secao = get_object_or_404(ConfiguracaoSecao, pk=pk)
    secao.ativo = not secao.ativo
    secao.save()
    
    status = "ativada" if secao.ativo else "desativada"
    messages.success(request, f'Seção "{secao.titulo}" {status}!')
    
    return redirect('participante:secoes_list')


