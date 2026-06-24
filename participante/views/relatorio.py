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
@user_passes_test(lambda u: u.is_superuser)
def dados_campanha(request):
    """View simplificada para métricas básicas da campanha"""
    # Métricas básicas
    quant_cupons = Cupom.objects.filter(impresso=True).count()
    quant_usuario = Profile.objects.filter(user__is_superuser=False).count()
    quant_lojistas = Lojista.objects.filter(status="Sim").count()
    quant_documentos = DocumentoFiscal.objects.filter(status="validado").count()

    # Métricas de documentos
    docs_validos = DocumentoFiscal.objects.filter(status="validado")
    media_docs_por_participante = round(
        quant_documentos / quant_usuario if quant_usuario > 0 else 0, 2
    )

    # Métricas de pagamento
    total_docs_rede = docs_validos.filter(compradoREDE=True).count()
    total_docs_mastercard = docs_validos.filter(compradoMASTERCARD=True).count()
    total_docs_cielo = docs_validos.filter(compradoCielo=True).count()

    perc_rede = round(
        (total_docs_rede / quant_documentos * 100) if quant_documentos > 0 else 0, 1
    )
    perc_mastercard = round(
        (total_docs_mastercard / quant_documentos * 100) if quant_documentos > 0 else 0, 1
    )
    perc_cielo = round(
        (total_docs_cielo / quant_documentos * 100) if quant_documentos > 0 else 0, 1
    )

    # Métricas de tempo
    hoje = timezone.now().date()
    registros_hoje = RegistroJornada.objects.filter(
        horario_inicio__date=hoje, horario_fim__isnull=False
    )

    total_horas_hoje = timedelta()
    for registro in registros_hoje:
        total_horas_hoje += registro.calcular_duracao()

    horas_hoje = round(total_horas_hoje.total_seconds() / 3600, 1)
    cupons_por_hora = round(quant_cupons / horas_hoje if horas_hoje > 0 else 0, 1)

    # Top 5 Lojistas por Volume
    top_lojistas = (
        DocumentoFiscal.objects.filter(status="validado")
        .values("lojista__fantasiaLojista")
        .annotate(total_docs=Count("id"), valor_total=Sum("valorDocumento"))
        .order_by("-valor_total")[:5]
    )

    # Distribuição por bairro
    distribuicao_bairros = (
        Profile.objects.exclude(bairro="")
        .values("bairro")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    # Métricas de conversão
    total_interessados = AdesaoLojista.objects.count()
    taxa_conversao = round(
        (quant_lojistas / total_interessados * 100) if total_interessados > 0 else 0, 1
    )

    context = {
        "quant_cupons": quant_cupons,
        "quant_usuario": quant_usuario,
        "quant_lojistas": quant_lojistas,
        "quant_documentos": quant_documentos,
        "media_docs_por_participante": media_docs_por_participante,
        "perc_rede": perc_rede,
        "perc_mastercard": perc_mastercard,
        "perc_cielo": perc_cielo,
        "horas_hoje": horas_hoje,
        "cupons_por_hora": cupons_por_hora,
        "top_lojistas": top_lojistas,
        "distribuicao_bairros": distribuicao_bairros,
        "taxa_conversao": taxa_conversao,
    }

    return render(request, "participante/dados_campanha.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def graficos_campanha(request):
    """View específica para gráficos da campanha"""
    # Dados para gráfico de cupons por dia
    cupons_por_dia = (
        Cupom.objects.all()
        .annotate(date=TruncDate("dataCriacao"))
        .values("date")
        .annotate(Count("dataCriacao"))
        .order_by("date")
    )

    # Dados para gráfico de faturamento por dia
    faturamento_por_dia = (
        DocumentoFiscal.objects.filter(status="validado")
        .annotate(date=TruncDate("dataCadastro"))
        .values("date")
        .annotate(valor=Sum("valorDocumento"))
        .order_by("date")
    )

    # Preparar dados para gráficos
    labels = []
    data = []
    data_faturamento = []
    valor_faturamento = []

    for fat in faturamento_por_dia:
        dt = fat["date"]
        dt = datetime.strftime(dt, "%d/%m")
        data_faturamento.append(dt)
        fat = float(fat["valor"])
        valor_faturamento.append(fat)

    for b in cupons_por_dia:
        dt = b["date"]
        dt = datetime.strftime(dt, "%d/%m")
        labels.append(dt)
        data.append(b["dataCriacao__count"])

    # Dados para gráfico de métodos de pagamento
    docs_validos = DocumentoFiscal.objects.filter(status="validado")
    
    # Contar documentos por método de pagamento
    docs_cielo = docs_validos.filter(compradoCielo=True).count()
    
    # Calcular "Outros" (documentos que não usaram Cielo)
    docs_outros = docs_validos.filter(compradoCielo=False).count()

    pagamentos = {
        "Cielo": docs_cielo,
        "Outros": docs_outros,
    }

    metodos = list(pagamentos.keys())
    valores = list(pagamentos.values())
    
    # Calcular percentuais baseados na contagem de documentos
    total_docs = docs_validos.count()
    percentuais = [
        round((v / total_docs * 100 if total_docs > 0 else 0), 1) for v in valores
    ]

    # Dados para gráfico de distribuição por bairro
    distribuicao_bairros = (
        Profile.objects.exclude(bairro="")
        .values("bairro")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    bairros = []
    totais = []
    for registro in distribuicao_bairros:
        bairros.append(registro["bairro"])
        totais.append(registro["total"])

    # Top lojistas para gráfico
    top_lojistas = (
        DocumentoFiscal.objects.filter(status="validado")
        .values("lojista__fantasiaLojista")
        .annotate(total_docs=Count("id"), valor_total=Sum("valorDocumento"))
        .order_by("-valor_total")[:5]
    )

    nomes_lojistas = [l["lojista__fantasiaLojista"] for l in top_lojistas]
    valores_lojistas = [float(l["valor_total"]) for l in top_lojistas]

    context = {
        "labels": labels,
        "data": data,
        "data_faturamento": data_faturamento,
        "valor_faturamento": valor_faturamento,
        "metodos": metodos,
        "valores": valores,
        "percentuais": percentuais,
        "bairros": bairros,
        "totais": totais,
        "nomes_lojistas": nomes_lojistas,
        "valores_lojistas": valores_lojistas,
    }

    return render(request, "participante/graficos_campanha.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def graficos(request):
    # Dados para o gráfico de cupons por dia
    cupons_por_dia = (
        Cupom.objects.annotate(data=TruncDate("dataCriacao"))
        .values("data")
        .annotate(total=Count("id"))
        .order_by("data")
    )

    # Dados para o gráfico de faturamento por dia
    faturamento_por_dia = (
        DocumentoFiscal.objects.filter(status="validado")
        .annotate(data=TruncDate("dataCadastro"))
        .values("data")
        .annotate(valor=Sum("valorDocumento"))
        .order_by("data")
    )

    # Preparar dados para os gráficos
    datas = []
    cupons = []
    faturamento = []

    for registro in cupons_por_dia:
        datas.append(registro["data"].strftime("%d/%m"))
        cupons.append(registro["total"])

    for registro in faturamento_por_dia:
        faturamento.append(float(registro["valor"]))

    # Dados para o gráfico de distribuição por bairro
    distribuicao_bairros = (
        Profile.objects.exclude(bairro="")
        .values("bairro")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    bairros = []
    totais = []

    for registro in distribuicao_bairros:
        bairros.append(registro["bairro"])
        totais.append(registro["total"])

    # Dados para o gráfico de métodos de pagamento
    docs_validos = DocumentoFiscal.objects.filter(status="validado")
    total_docs = docs_validos.count()

    pagamentos = {
        "REDE": docs_validos.filter(compradoREDE=True).count(),
        "Mastercard": docs_validos.filter(compradoMASTERCARD=True).count(),
        "Cielo": docs_validos.filter(compradoCielo=True).count(),
    }

    metodos = list(pagamentos.keys())
    valores = list(pagamentos.values())
    percentuais = [
        round((v / total_docs * 100 if total_docs > 0 else 0), 1) for v in valores
    ]

    context = {
        "datas": datas,
        "cupons": cupons,
        "faturamento": faturamento,
        "bairros": bairros,
        "totais": totais,
        "metodos": metodos,
        "valores": valores,
        "percentuais": percentuais,
    }

    return render(request, "participante/graficos_campanha.html", context)


def relatorios_camp(request):
    # Métricas gerais
    total_cupons = Cupom.objects.count()
    total_usuarios = Profile.objects.filter(user__is_superuser=False).count()
    total_lojistas = Lojista.objects.filter(status="Sim").count()
    total_documentos = DocumentoFiscal.objects.filter(
        status="validado"
    ).count()

    # Métricas de documentos
    docs_validos = DocumentoFiscal.objects.filter(status="validado")
    media_docs_por_participante = round(
        total_documentos / total_usuarios if total_usuarios > 0 else 0, 2
    )

    # Métricas de pagamento
    total_docs_rede = docs_validos.filter(compradoREDE=True).count()
    total_docs_mastercard = docs_validos.filter(compradoMASTERCARD=True).count()
    total_docs_cielo = docs_validos.filter(compradoCielo=True).count()

    perc_rede = round(
        (total_docs_rede / total_documentos * 100) if total_documentos > 0 else 0, 1
    )
    perc_mastercard = round(
        (total_docs_mastercard / total_documentos * 100) if total_documentos > 0 else 0,
        1,
    )
    perc_cielo = round(
        (total_docs_cielo / total_documentos * 100) if total_documentos > 0 else 0, 1
    )

    # Faturamento e ticket médio
    faturamento_total = (
        docs_validos.aggregate(total=Sum("valorDocumento"))["total"] or 0
    )
    ticket_medio = round(
        faturamento_total / total_documentos if total_documentos > 0 else 0, 2
    )

    # Top lojistas
    top_lojistas = (
        docs_validos.values("lojista__fantasiaLojista")
        .annotate(total_docs=Count("id"), valor_total=Sum("valorDocumento"))
        .order_by("-valor_total")[:10]
    )

    # Distribuição por bairro
    distribuicao_bairros = (
        Profile.objects.exclude(bairro="")
        .values("bairro")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    context = {
        "total_cupons": total_cupons,
        "total_usuarios": total_usuarios,
        "total_lojistas": total_lojistas,
        "total_documentos": total_documentos,
        "media_docs_por_participante": media_docs_por_participante,
        "perc_rede": perc_rede,
        "perc_mastercard": perc_mastercard,
        "perc_cielo": perc_cielo,
        "faturamento_total": f"R$ {faturamento_total:,.2f}",
        "ticket_medio": f"R$ {ticket_medio:,.2f}",
        "top_lojistas": top_lojistas,
        "distribuicao_bairros": distribuicao_bairros,
    }

    return render(request, "relatorio_dashboard/index.html", context)


@login_required
def relatorio_jornada(request):
    """
    View para relatórios de jornada de trabalho
    - Participantes veem apenas seu próprio relatório
    - RH e Gerentes veem relatório de todos
    """
    from datetime import datetime, timedelta
    from django.db.models import Q
    
    # Verificar se o usuário tem permissão para ver relatórios de todos
    pode_ver_todos = request.user.is_superuser or request.user.groups.filter(
        name__in=['Recursos Humanos', 'Gerente', 'Gerente Solve']
    ).exists()
    
    # Obter parâmetros da URL
    tipo_relatorio = request.GET.get('tipo', 'individual')  # individual ou todos
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    # Se não tem permissão para ver todos, forçar relatório individual
    if not pode_ver_todos:
        tipo_relatorio = 'individual'
    
    # Definir período padrão (últimos 30 dias)
    if not data_inicio:
        data_inicio = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not data_fim:
        data_fim = datetime.now().strftime('%Y-%m-%d')
    
    # Converter para datetime
    try:
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
    except ValueError:
        data_inicio_dt = datetime.now() - timedelta(days=30)
        data_fim_dt = datetime.now()
    
    # Filtrar jornadas
    if tipo_relatorio == 'individual':
        # Relatório individual - apenas jornadas do usuário logado
        jornadas = RegistroJornada.objects.filter(
            user=request.user,
            horario_inicio__date__range=[data_inicio_dt.date(), data_fim_dt.date()]
        ).order_by('-horario_inicio')
        
        # Estatísticas do usuário
        total_jornadas = jornadas.count()
        jornadas_finalizadas = jornadas.filter(status='FINALIZADA').count()
        total_horas = timedelta()
        
        for jornada in jornadas.filter(status='FINALIZADA'):
            if jornada.horario_fim:
                duracao = jornada.horario_fim - jornada.horario_inicio
                total_horas += duracao
        
        horas_trabalhadas = total_horas.total_seconds() / 3600
        
        # Não precisamos calcular duração manualmente, o modelo tem o método get_duracao_formatada()
        
        context = {
            'tipo_relatorio': 'individual',
            'jornadas': jornadas,
            'total_jornadas': total_jornadas,
            'jornadas_finalizadas': jornadas_finalizadas,
            'horas_trabalhadas': round(horas_trabalhadas, 2),
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'usuario': request.user,
        }
        
        return render(request, 'participante/relatorio_jornada_individual.html', context)
    
    else:
        # Relatório geral - todas as jornadas (apenas para RH/Gerentes)
        jornadas = RegistroJornada.objects.filter(
            horario_inicio__date__range=[data_inicio_dt.date(), data_fim_dt.date()]
        ).order_by('-horario_inicio')
        
        # Estatísticas gerais
        total_jornadas = jornadas.count()
        jornadas_finalizadas = jornadas.filter(status='FINALIZADA').count()
        usuarios_ativos = jornadas.values('user').distinct().count()
        
        # Jornadas por usuário
        jornadas_por_usuario = []
        for jornada in jornadas.select_related('user', 'posto_trabalho'):
            duracao = None
            if jornada.horario_fim:
                duracao = jornada.horario_fim - jornada.horario_inicio
            
            jornadas_por_usuario.append({
                'usuario': jornada.user.username,
                'nome': f"{jornada.user.first_name} {jornada.user.last_name}".strip() or jornada.user.username,
                'posto': jornada.posto_trabalho.nome if jornada.posto_trabalho else 'Não definido',
                'inicio': jornada.horario_inicio,
                'fim': jornada.horario_fim,
                'status': jornada.status,
                'duracao': duracao,
                'duracao_formatada': jornada.get_duracao_formatada() if duracao else None
            })
        
        context = {
            'tipo_relatorio': 'todos',
            'jornadas': jornadas_por_usuario,
            'total_jornadas': total_jornadas,
            'jornadas_finalizadas': jornadas_finalizadas,
            'usuarios_ativos': usuarios_ativos,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
        }
        
        return render(request, 'participante/relatorio_jornada_geral.html', context)


@login_required
def relatorio_jornada_pdf(request):
    """
    Gera o PDF individual do relatório de jornada do usuário logado,
    reutilizando o template lojista/registros_jornada_pdf.html.
    """
    from participante.models import RegistroJornada
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa
    from io import BytesIO
    from datetime import datetime
    from django.utils import timezone

    # Filtros simples de período (padrão últimos 30 dias)
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')

    data_inicio_dt = None
    data_fim_dt = None
    try:
        if data_inicio:
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        if data_fim:
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d').date()
    except ValueError:
        data_inicio_dt = None
        data_fim_dt = None

    if data_inicio_dt and data_fim_dt and data_inicio_dt > data_fim_dt:
        data_inicio_dt, data_fim_dt = data_fim_dt, data_inicio_dt

    registros = RegistroJornada.objects.select_related(
        'user__profile', 'posto_trabalho'
    ).filter(
        user=request.user
    ).order_by('horario_inicio')

    if data_inicio_dt:
        registros = registros.filter(horario_inicio__date__gte=data_inicio_dt)
    if data_fim_dt:
        registros = registros.filter(horario_inicio__date__lte=data_fim_dt)

    # Preparar durations e página única
    agora = timezone.now()
    total_segundos = 0
    registros_list = []
    for r in registros.iterator():
        if r.horario_inicio:
            fim = r.horario_fim or agora
            duracao = fim - r.horario_inicio
            if duracao.total_seconds() < 0:
                from datetime import timedelta as _td
                duracao = _td(0)
            r.duracao_exibicao = RegistroJornada.formatar_duracao(duracao)
            total_segundos += int(duracao.total_seconds())
        else:
            r.duracao_exibicao = "N/A"
        registros_list.append(r)

    from datetime import timedelta as _td
    total_str = RegistroJornada.formatar_duracao(_td(seconds=max(0, total_segundos)))

    pages = [{
        'user': request.user,
        'registros': registros_list,
        'total_duracao': total_str,
    }]

    context = {
        'pages': pages,
        'gerado_em': agora,
        'periodo_inicio': data_inicio_dt,
        'periodo_fim': data_fim_dt,
    }

    html = render_to_string('lojista/registros_jornada_pdf.html', context)
    result = BytesIO()
    pdf_status = pisa.CreatePDF(src=html, dest=result)

    if pdf_status.err:
        return HttpResponse('Erro ao gerar PDF', status=500)

    filename = f"relatorio_jornada_{request.user.username}.pdf"
    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


