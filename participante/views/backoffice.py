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


# backoffice
@login_required
@user_passes_test(lambda u: u.is_staff)
def backoffice(request):
    # Filtrar apenas documentos enviados pelos participantes (não pelos operadores)
    docs_list = (
        DocumentoFiscal.objects
        .filter(enviado_por_operador=False)
        .select_related("lojista", "user", "user__profile")
    )

    # Get filter parameters
    status_filter = request.GET.get('status_filter')
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    lojista_cnpj = request.GET.get('lojista_cnpj')
    lojista_nome = request.GET.get('lojista_nome')
    participante_cpf = request.GET.get('participante_cpf')
    participante_nome = request.GET.get('participante_nome')
    numero_documento = request.GET.get('numero_documento')
    has_observation = request.GET.get('has_observation')
    observacao = request.GET.get('observacao')
    global_search = request.GET.get('global_search')

    # Sanitize 'None' string or empty values
    def valid_param(val):
        return val not in (None, '', 'None')

    # Verificar se é primeira visita real (sem nenhum parâmetro GET)
    is_first_visit = len(request.GET) == 0

    # Apply global search if provided
    if valid_param(global_search):
        docs_list = docs_list.filter(
            Q(user__profile__CPF__icontains=global_search) |
            Q(user__profile__nome__icontains=global_search) |
            Q(lojista__fantasiaLojista__icontains=global_search) |
            Q(lojista__CNPJLojista__icontains=global_search) |
            Q(numeroDocumento__icontains=global_search) |
            Q(observacao__icontains=global_search)
        )

    # Apply status filter
    if status_filter == 'pendente':
        docs_list = docs_list.filter(status=StatusChoices.PENDENTE)
    elif status_filter == 'validado':
        docs_list = docs_list.filter(status=StatusChoices.VALIDADO)
    elif status_filter == 'inconsistente':
        docs_list = docs_list.filter(status=StatusChoices.INCONSISTENTE)
    elif is_first_visit and len(request.GET) == 0:
        # Apenas na primeira visita real (sem nenhum parâmetro): mostrar pendentes
        docs_list = docs_list.filter(status=StatusChoices.PENDENTE)
        status_filter = 'pendente'
    # Se status_filter for vazio mas não é primeira visita (usuário escolheu "Todos"), não filtra por status

    if valid_param(lojista_cnpj):
        docs_list = docs_list.filter(lojista__CNPJLojista__icontains=lojista_cnpj)
    if valid_param(lojista_nome):
        docs_list = docs_list.filter(lojista__fantasiaLojista__icontains=lojista_nome)

    if valid_param(participante_cpf):
        docs_list = docs_list.filter(user__profile__CPF__icontains=participante_cpf)
    if valid_param(participante_nome):
        docs_list = docs_list.filter(user__profile__nome__icontains=participante_nome)

    # Apply date filters
    if valid_param(data_inicio_str):
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            docs_list = docs_list.filter(dataDocumento__gte=data_inicio)
        except ValueError:
            pass  # Ignore invalid date format
    
    if valid_param(data_fim_str):
        try:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            docs_list = docs_list.filter(dataDocumento__lte=data_fim)
        except ValueError:
            pass  # Ignore invalid date format

    if valid_param(numero_documento):
        docs_list = docs_list.filter(numeroDocumento__icontains=numero_documento)

    if has_observation == 'on':
        docs_list = docs_list.exclude(observacao__isnull=True).exclude(observacao__exact='')
    if valid_param(observacao):
        docs_list = docs_list.filter(observacao__icontains=observacao)

    # Order by dataCadastro (oldest first)
    docs_list = docs_list.order_by("dataCadastro")

    # Paginate results
    paginator = Paginator(docs_list, 100)
    page = request.GET.get("page", 1)
    docs = paginator.get_page(page)

    # Build querystring without the page parameter to avoid duplication in links
    qs = request.GET.copy()
    if 'page' in qs:
        try:
            qs.pop('page')
        except Exception:
            # Fallback in case QueryDict is immutable or pop fails
            qs.__delitem__('page') if 'page' in qs else None
    # Ensure default-applied status filter persists across pagination when first visit
    if status_filter:
        qs['status_filter'] = status_filter
    pagination_querystring = qs.urlencode()

    context = {
        "section": "backoffice",
        "docs": docs,
        "page_obj": docs,
        "status_filter": status_filter,
        "data_inicio": data_inicio_str,
        "data_fim": data_fim_str,
        "lojista_cnpj": lojista_cnpj,
        "lojista_nome": lojista_nome,
        "participante_cpf": participante_cpf,
        "participante_nome": participante_nome,
        "numero_documento": numero_documento,
        "has_observation": has_observation,
        "observacao": observacao,
        "global_search": global_search,
        "pagination_querystring": pagination_querystring,
    }
    return render(
        request,
        "participante/participante_backoffice.html",
        context,
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
@transaction.atomic
def editar_documento_backoffice(request, id):
    """Permite ao operador/backoffice editar um DocumentoFiscal e apenas salvar, sem validar ou gerar cupons."""
    instance = get_object_or_404(DocumentoFiscal.objects.select_for_update(), id=id)

    if request.method == "POST":
        form = DocumentoFiscalEditFormOp(instance=instance, data=request.POST, files=request.FILES)
        if form.is_valid():
            documento_editado = form.save()

            # Registrar auditoria de edição simples
            try:
                from participante.models import Auditoria
                Auditoria.registrar_acao(
                    usuario=request.user,
                    tipo_acao='edicao_documento',
                    descricao=f'Documento {documento_editado.numeroDocumento} editado no backoffice (edição simples, sem validação).',
                    documento_fiscal=documento_editado,
                    request=request,
                )
            except Exception:
                # Auditoria não deve bloquear o fluxo
                pass

            messages.success(request, "Documento atualizado com sucesso.")
            return redirect("participante:backoffice")
        else:
            messages.error(request, "Corrija os erros do formulário e tente novamente.")
    else:
        form = DocumentoFiscalEditFormOp(instance=instance)

    context = {
        "documentofiscal_form": form,
        "documento": instance,
        "section": "edit_document",
    }
    return render(request, "participante/doc_fiscal_edit_participante.html", context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def documentos_participante(request, user_id: int):
    """Lista documentos de um participante específico (por usuário), para uso do backoffice.

    Mantém paginação e carrega relações necessárias para evitar N+1.
    """
    participante_user = get_object_or_404(User, id=user_id)

    docs_qs = (
        DocumentoFiscal.objects.filter(user=participante_user)
        .select_related("lojista", "user", "user__profile")
        .order_by("-dataCadastro")
    )

    paginator = Paginator(docs_qs, 100)
    page = request.GET.get("page", 1)
    docs = paginator.get_page(page)

    context = {
        "section": "backoffice",
        "docs": docs,
        "participant_user": participante_user,
    }
    return render(request, "participante/participante_documentos.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def documentos_equivalentes_suspeitos(request):
    """Lista grupos de documentos equivalentes por participante/lojista (potencial fraude).

    Critério: mesmo participante + mesmo lojista + mesmo número normalizado (apenas dígitos, sem zeros à esquerda),
    mas com números originais diferentes em pelo menos um caso.
    """
    from collections import defaultdict

    def normalize_document_number(raw_value: str) -> str:
        text = str(raw_value or "").strip()
        digits_only = "".join(ch for ch in text if ch.isdigit())
        if digits_only:
            try:
                return str(int(digits_only))
            except ValueError:
                pass
        return text.lower()

    # Filtros opcionais
    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")
    origem = request.GET.get("origem")  # None | 'participante' | 'operador'
    status_filter = request.GET.get("status")
    q = request.GET.get("q", "").strip()
    lojista_cnpj = request.GET.get("lojista_cnpj", "").strip()
    lojista_nome = request.GET.get("lojista_nome", "").strip()
    cadastrado_por = request.GET.get("cadastrado_por", "").strip()

    qs = (
        DocumentoFiscal.objects.select_related("user", "user__profile", "lojista")
        .only(
            "id",
            "user_id",
            "lojista_id",
            "numeroDocumento",
            "dataDocumento",
            "status",
            "valorDocumento",
            "valorCielo",
            "valorOutros",
            "enviado_por_operador",
        )
    )

    # Filtro por origem (quem cadastrou)
    if origem == "participante":
        qs = qs.filter(enviado_por_operador=False)
    elif origem == "operador":
        qs = qs.filter(enviado_por_operador=True)

    # Filtro por texto (participante)
    if q:
        qs = qs.filter(Q(user__profile__CPF__icontains=q) | Q(user__profile__nome__icontains=q) | Q(user__username__icontains=q))

    # Filtro por lojista
    if lojista_cnpj:
        qs = qs.filter(lojista__CNPJLojista__icontains=lojista_cnpj)
    if lojista_nome:
        qs = qs.filter(lojista__fantasiaLojista__icontains=lojista_nome)

    # Filtro por cadastrado_por (nome de usuário ou nome do perfil se existir)
    if cadastrado_por:
        qs = qs.filter(
            Q(cadastrado_por__username__icontains=cadastrado_por)
            | Q(cadastrado_por__profile__nome__icontains=cadastrado_por)
        )

    # Filtro por status
    if status_filter in [StatusChoices.PENDENTE, StatusChoices.VALIDADO, StatusChoices.INCONSISTENTE]:
        qs = qs.filter(status=status_filter)

    # Filtro por data
    def parse_date(value):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except Exception:
            return None

    d_ini = parse_date(data_inicio)
    d_fim = parse_date(data_fim)
    if d_ini:
        qs = qs.filter(dataDocumento__gte=d_ini)
    if d_fim:
        qs = qs.filter(dataDocumento__lte=d_fim)

    # Agrupar por (user, lojista, normalized)
    groups = defaultdict(list)
    for doc in qs.iterator():
        norm = normalize_document_number(doc.numeroDocumento)
        key = (doc.user_id, doc.lojista_id, norm)
        groups[key].append(doc)

    # Filtrar grupos suspeitos (2+ docs e pelo menos 2 números originais diferentes)
    suspicious_groups = []
    total_docs_suspeitos = 0
    for (user_id, lojista_id, norm), docs_list in groups.items():
        if len(docs_list) < 2:
            continue
        originals = {d.numeroDocumento for d in docs_list}
        if len(originals) >= 2:
            # pegar user/lojista de um doc
            sample = docs_list[0]
            # janela de tempo
            datas = [d.dataDocumento for d in docs_list if d.dataDocumento]
            data_min = min(datas) if datas else None
            data_max = max(datas) if datas else None
            janela_dias = (data_max - data_min).days if data_min and data_max else None
            # severidade simples: (qtd originais - 1) + bônus se janela <= 1 dia
            severity = (len(originals) - 1) + (1 if (janela_dias is not None and janela_dias <= 1) else 0)
            suspicious_groups.append(
                {
                    "user": sample.user,
                    "profile": getattr(sample.user, "profile", None),
                    "lojista": sample.lojista,
                    "normalized": norm,
                    "docs": sorted(docs_list, key=lambda x: x.dataDocumento or datetime.min),
                    "originals": sorted(originals),
                    "count": len(docs_list),
                    "data_min": data_min,
                    "data_max": data_max,
                    "janela_dias": janela_dias,
                    "severity": severity,
                }
            )
            total_docs_suspeitos += len(docs_list)

    # Ordenar por quantidade desc e depois por user
    suspicious_groups.sort(key=lambda g: (-g["count"], g["user"].id, g["lojista"].id))

    # Paginação por grupos
    # Export CSV
    if request.GET.get("export") == "csv":
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=docs_suspeitos.csv"
        writer = csv.writer(response)
        writer.writerow(["user_id", "nome", "cpf", "lojista_id", "lojista", "cnpj", "normalizado", "originais", "qtd", "data_min", "data_max", "janela_dias", "severity"])
        for g in suspicious_groups:
            writer.writerow([
                g["user"].id,
                getattr(g["profile"], "nome", g["user"].username),
                getattr(g["profile"], "CPF", ""),
                g["lojista"].id,
                g["lojista"].fantasiaLojista,
                g["lojista"].CNPJLojista,
                g["normalized"],
                "; ".join(g["originals"]),
                g["count"],
                g["data_min"],
                g["data_max"],
                g["janela_dias"],
                g["severity"],
            ])
        return response

    paginator = Paginator(suspicious_groups, 10)
    page = request.GET.get("page", 1)
    page_obj = paginator.get_page(page)

    context = {
        "section": "backoffice",
        "groups": page_obj,
        "page_obj": page_obj,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "origem": origem or "",
        "q": q,
        "lojista_cnpj": lojista_cnpj,
        "lojista_nome": lojista_nome,
        "cadastrado_por": cadastrado_por,
        "status": status_filter or "",
        "total_groups": len(suspicious_groups),
        "total_docs": total_docs_suspeitos,
    }
    return render(request, "participante/documentos_suspeitos.html", context)


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)  # Mudança para permitir staff
def impressao_backoffice(request):
    # Debug: Verificar total de documentos
    total_docs = DocumentoFiscal.objects.count()
    docs_validados = DocumentoFiscal.objects.filter(status=StatusChoices.VALIDADO).count()
    docs_participantes = DocumentoFiscal.objects.filter(enviado_por_operador=False).count()
    
    # Filtra documentos validados PELO BACKOFFICE (apenas de participantes, não operadores)
    docs_list = (
        DocumentoFiscal.objects.filter(
            status=StatusChoices.VALIDADO,  # Apenas documentos validados
            enviado_por_operador=False,     # Apenas de participantes (validados pelo backoffice)
        )
        .filter(
            # Documentos que não têm cupons OU têm cupons não impressos
            Q(rel_cupom_doc__isnull=True) |  # Não têm cupons
            Q(rel_cupom_doc__impresso=False)  # Têm cupons não impressos
        )
        .distinct()
        .order_by("-dataCadastro")
    )
    
    docs_final = docs_list.count()
    
    
    # Debug adicional: verificar documentos sem cupons
    docs_sem_cupons = DocumentoFiscal.objects.filter(
        status=StatusChoices.VALIDADO,
        enviado_por_operador=False,
        rel_cupom_doc__isnull=True
    ).count()
    
    
    # Debug adicional: verificar documentos com cupons não impressos
    docs_cupons_nao_impressos = DocumentoFiscal.objects.filter(
        status=StatusChoices.VALIDADO,
        enviado_por_operador=False,
        rel_cupom_doc__impresso=False
    ).count()
   
    
    # Debug adicional: verificar status dos documentos
    docs_pendentes = DocumentoFiscal.objects.filter(status=StatusChoices.PENDENTE).count()
    docs_inconsistentes = DocumentoFiscal.objects.filter(status=StatusChoices.INCONSISTENTE).count()
    docs_operadores = DocumentoFiscal.objects.filter(enviado_por_operador=True).count()
    
   
    
    # Debug adicional: listar todos os documentos
    
   

    # Paginação
    docs_list = Paginator(docs_list, 100)
    page = docs_list.page(request.GET.get("page", "1"))
    

    # Contexto para reversão e cancelamento de impressão
    from participante.models import ReversaoImpressao, CancelamentoImpressao
    documentos_revertidos_ids = list(ReversaoImpressao.objects.filter(
        documento__in=docs_list.object_list,
        usuario__groups=request.user.groups.first()
    ).values_list('documento_id', flat=True))
    
    # Adicionar documentos cancelados para controle
    documentos_cancelados_ids = list(CancelamentoImpressao.objects.filter(
        documento__in=docs_list.object_list
    ).values_list('documento_id', flat=True))

    return render(
        request, "participante/print_detail_backoffice.html", {
            "section": "people", 
            "docs": page,
            "documentos_revertidos_ids": documentos_revertidos_ids,
            "documentos_cancelados_ids": documentos_cancelados_ids
        }
    )


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
@transaction.atomic
def reverter_impressao_cupons(request, id):


    
    """
    Reverte a impressão de cupons de um documento fiscal.
    - Apaga todos os cupons impressos
    - Coloca o documento em status PENDENTE
    - Permite nova validação e impressão
    
    Controle de permissões:
    - Operador e Backoffice: apenas 1 vez por documento
    - Suporte: ilimitado
    - Outros grupos: não podem reverter
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Log da requisição
    logger.info(f"Reversão de impressão iniciada - ID: {id}, User: {request.user.username}")
    
    instance = get_object_or_404(DocumentoFiscal, id=id)
    
    # Verificar se o documento está validado e tem cupons
    cupons = Cupom.objects.filter(documentoFiscal=instance)
    total_cupons = cupons.count()
    
    if instance.status != StatusChoices.VALIDADO:
        error_msg = f"O documento {instance.numeroDocumento} não está validado."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': error_msg
            })
        else:
            messages.error(request, error_msg)
        return redirect("participante:backoffice")
    
    if total_cupons == 0:
        error_msg = f"O documento {instance.numeroDocumento} não possui cupons para reverter."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': error_msg
            })
        else:
            messages.error(request, error_msg)
        return redirect("participante:backoffice")
    
    if request.method == "POST":
        # Verificar permissões de reversão apenas no POST
        from participante.models import ReversaoImpressao
        
        pode_reverter, motivo = ReversaoImpressao.pode_reverter(request.user, instance)
        
        if not pode_reverter:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f"Não é possível reverter a impressão: {motivo}"
                })
            else:
                messages.error(request, f"Não é possível reverter a impressão: {motivo}")
                return redirect("participante:backoffice")
        
        try:
            with transaction.atomic():
                # Apagar todos os cupons do documento
                cupons_deletados = cupons.count()
                cupons.delete()
                
                # Colocar documento em pendente
                instance.status = StatusChoices.PENDENTE
                instance.save()
                
                # Registrar a reversão
                motivo_reversao = request.POST.get('motivo', '').strip()
                
                # Validar se a justificativa foi fornecida
                if not motivo_reversao:
                    raise ValueError("Justificativa da reversão é obrigatória")
                
                ReversaoImpressao.registrar_reversao(
                    usuario=request.user,
                    documento=instance,
                    cupons_removidos=cupons_deletados,
                    motivo=motivo_reversao
                )
                
                # Registrar na auditoria
                from participante.models import Auditoria
                Auditoria.registrar_acao(
                    usuario=request.user,
                    tipo_acao='reversao_impressao',
                    descricao=f"Reversão de impressão do documento {instance.numeroDocumento}. {cupons_deletados} cupons removidos.",
                    documento_fiscal=instance,
                    justificativa=motivo_reversao,
                    request=request
                )
                
                success_msg = f"Impressão revertida com sucesso! {cupons_deletados} cupon(s) removido(s). Documento {instance.numeroDocumento} colocado em pendente para nova validação."
                logger.info(f"Reversão bem-sucedida: {success_msg}")
                
                # Verificar se é uma requisição AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': success_msg
                    })
                else:
                    messages.success(request, success_msg)
                
        except Exception as e:
            # Verificar se é erro de constraint unique
            if "UNIQUE constraint failed" in str(e) and "participante_reversaoimpressao" in str(e):
                error_msg = "Você já reverteu a impressão deste documento. Não é possível reverter novamente. Solicite ao suporte se necessário."
                logger.warning(f"Tentativa de reversão duplicada - User: {request.user.username}, Documento: {instance.numeroDocumento}")
            else:
                error_msg = f"Erro ao reverter impressão: {str(e)}"
                logger.error(f"Erro na reversão: {str(e)}", exc_info=True)
            
            # Verificar se é uma requisição AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_msg
                })
            else:
                messages.error(request, error_msg)
    
    # Verificar se é uma requisição AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'message': 'Método não permitido'
        })
    else:
        return redirect("participante:backoffice")


def _executar_reversao_interna(usuario, documento):

    

    """ Quando da errro em uma impressao, a reversão é feita por view de registrar_cancelamento_impressao que chama esta função """
    """
    Função interna para executar reversão sem problemas de segurança.
    Usada pelo cancelamento para evitar importação circular e request falso.
    """
    
    if not (usuario.is_staff or usuario.is_superuser):
        return False, "Usuário não tem permissão para executar esta ação"
    
    from cupom.models import Cupom
    from participante.models import ReversaoImpressao, StatusChoices
    
    try:
        # Verificar se tem cupons
        cupons = Cupom.objects.filter(documentoFiscal=documento)
        if not cupons.exists():
            return False, "Não há cupons para reverter"       
        
        # Apagar cupons antigos
        cupons_deletados = cupons.count()
        cupons.delete()
        
        ReversaoImpressao.registrar_reversao(
            usuario=usuario,
            documento=documento,
            cupons_removidos=cupons_deletados,
            motivo="Reversão automática após cancelamento"
        )
        
        # Voltar para PENDENTE
        documento.status = StatusChoices.PENDENTE
        documento.save()
        
        return True, f"Cancelamento realizado: {cupons_deletados} cupons removidos. Documento em PENDENTE para edição."
        
    except Exception as e:
        return False, f"Erro na reversão: {str(e)}"


@require_http_methods(["POST"])
@ensure_csrf_cookie
def reverter_impressao_simple(request, id):

    """
    Versão simplificada da reversão de impressão para teste.
    """
    # Imports necessários
    from cupom.models import Cupom
    from participante.models import ReversaoImpressao, CancelamentoImpressao
    
   
    
    # Verificar autenticação
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Usuário não autenticado'
        }, status=401)
    
    # Verificar permissões básicas
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({
            'success': False,
            'message': 'Sem permissão para esta ação'
        }, status=403)
    
    try:
        # Processar dados da requisição
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            motivo = data.get('motivo', 'Reversão automática')
        else:
            motivo = request.POST.get('motivo', 'Reversão automática')
        
        # Buscar documento
        documento = DocumentoFiscal.objects.get(id=id)
        
        # Verificar se tem cupons
        cupons = Cupom.objects.filter(documentoFiscal=documento)
        
        if not cupons.exists():
            return JsonResponse({
                'success': False,
                'message': 'Não há cupons para reverter'
            })
        
        # Verificar se pode reverter (limitação por grupos)
        pode_reverter, mensagem = ReversaoImpressao.pode_reverter(request.user, documento)
        
        if not pode_reverter:
            return JsonResponse({
                'success': False,
                'message': f'Não é possível reverter: {mensagem}'
            }, status=403)
        
        # Apagar cupons antigos
        cupons_deletados = cupons.count()
        cupons.delete()
        
        # Gerar novos cupons automaticamente
        # Calcular quantos cupons gerar
        total_cupons = documento.get_cupons()      
        
        # Registrar a reversão
        ReversaoImpressao.registrar_reversao(
            usuario=request.user,
            documento=documento,
            cupons_removidos=cupons_deletados,
            motivo=motivo
        )
        
        # IMPORTANTE: Voltar documento para PENDENTE para permitir edição
        documento.status = StatusChoices.PENDENTE
        documento.save()
        
        # IMPORTANTE: Remover cancelamentos antigos para permitir nova impressão
        cancelamentos_antigos = CancelamentoImpressao.objects.filter(documento=documento)
        if cancelamentos_antigos.exists():
            cancelamentos_removidos = cancelamentos_antigos.count()
            cancelamentos_antigos.delete()
            
        else:
            cancelamentos_removidos = 0
        documento.status = StatusChoices.PENDENTE
        documento.save()
        
        # IMPORTANTE: Remover cancelamentos antigos para permitir nova impressão
        cancelamentos_antigos = CancelamentoImpressao.objects.filter(documento=documento)
        if cancelamentos_antigos.exists():
            cancelamentos_removidos = cancelamentos_antigos.count()
            cancelamentos_antigos.delete()
            
        else:
            cancelamentos_removidos = 0
        documento.status = StatusChoices.PENDENTE
        documento.save()
        
        
        return JsonResponse({
            'success': True,
            'message': f'Reversão realizada com sucesso! {cupons_deletados} cupon(s) removido(s) e {total_cupons} novo(s) cupon(s) gerado(s). Documento voltou para pendente para permitir edição.',
            'documento': documento.numeroDocumento
        })
        
    except DocumentoFiscal.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': f'Documento {id} não encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_POST
def calcular_cupons_preview(request):
    """
    Endpoint seguro e reutilizável para calcular cupons em tempo real.
    Pode ser usado em qualquer parte do sistema.
    """
    try:
        # Extrair e validar dados com logging para debug
        valor_cielo_raw = request.POST.get('valor_cielo', '0')
        valor_outros_raw = request.POST.get('valor_outros', '0')
        
        
        
        # Converter para float com validação
        try:
            valor_cielo = float(valor_cielo_raw)
        except (ValueError, TypeError):
           
            return JsonResponse({
                'success': False, 
                'error': f'Valor Cielo inválido: {valor_cielo_raw}'
            }, status=400)
        
        try:
            valor_outros = float(valor_outros_raw)
        except (ValueError, TypeError):
           
            return JsonResponse({
                'success': False, 
                'error': f'Valor Outros inválido: {valor_outros_raw}'
            }, status=400)
        
        # Validações de segurança
        if valor_cielo < 0 or valor_outros < 0:
            return JsonResponse({
                'success': False, 
                'error': 'Valores negativos não permitidos'
            }, status=400)
        
        if valor_cielo + valor_outros > 50000:  # Limite máximo aumentado para R$ 50.000,00
            return JsonResponse({
                'success': False, 
                'error': 'Valor muito alto (máximo R$ 50.000,00)'
            }, status=400)
        
        # Usar a mesma lógica do modelo (garante consistência)
        valor_documento = valor_cielo + valor_outros
        
        # Criar documento temporário para cálculo
        from participante.models import DocumentoFiscal, StatusChoices
        
        doc_temp = DocumentoFiscal(
            valorCielo=valor_cielo,
            valorOutros=valor_outros,
            valorDocumento=valor_documento,
            status=StatusChoices.VALIDADO  # Para permitir cálculo
        )
        
        cupons = doc_temp.get_cupons()
        
        # Calcular breakdown correto dos cupons
        cupons_cielo = 0
        cupons_outros = 0
        
        if valor_cielo > valor_outros:
            # Regra 1: Cielo > Outros
            cupons_cielo_base = int(valor_cielo // 50)
            resto_cielo = valor_cielo % 50
            
            if resto_cielo > 0:
                valor_outros_ajustado = valor_outros + resto_cielo
            else:
                valor_outros_ajustado = valor_outros
            
            cupons_cielo = cupons_cielo_base * 3
            cupons_outros = int(valor_outros_ajustado // 50)
        else:
            # Regra 2: Cielo <= Outros
            cupons_outros_base = int(valor_outros // 50)
            resto_outros = valor_outros % 50
            
            if resto_outros > 0:
                valor_cielo_ajustado = valor_cielo + resto_outros
            else:
                valor_cielo_ajustado = valor_cielo
            
            cupons_outros = cupons_outros_base
            cupons_cielo = int(valor_cielo_ajustado // 50) * 3
        
        result = {
            'success': True,
            'cupons': cupons,
            'cupons_cielo': cupons_cielo,
            'cupons_outros': cupons_outros,
            'valor_total': valor_documento,
            'valor_cielo': valor_cielo,
            'valor_outros': valor_outros,
            'timestamp': timezone.now().isoformat()  # Para cache
        }
        
        
        return JsonResponse(result)
        
    except ValueError as e:        
        return JsonResponse({
            'success': False, 
            'error': f'Valores inválidos: {str(e)}'
        }, status=400)
    except Exception as e:        
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': f'Erro interno do servidor: {str(e)}'
        }, status=500)


