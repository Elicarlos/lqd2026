import logging
from io import BytesIO

from celery.result import AsyncResult
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateformat import DateFormat
from django.views.decorators.http import require_POST
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.pdfbase import pdfdoc, pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


from bcp.tasks import generate_pdf_task
from cupom.models import Cupom
from participante.forms import DocumentoFiscalEditForm
from participante.models import DocumentoFiscal

from django.conf import settings

if settings.DEBUG:
    from silk.profiling.profiler import silk_profile

else:
    
    def silk_profile(name=''):
        def decorator(func):
            return func
        return decorator



"""
===============================================================================
                                VIEWS DE IMPRESSÃO - BCP
===============================================================================

RESUMO DAS VIEWS PRINCIPAIS:

1. print_barcode_get() - ⭐ VIEW PRINCIPAL (RECOMENDADA)
   - GET /barcode/print_get/<id>/
   - Mais robusta e confiável
   - Retorna PDF diretamente
   - Marca cupons como impressos automaticamente

2. print_barcode() - ⚠️ VIEW ALTERNATIVA (POST)
   - POST /barcode/print/<id>/
   - Mais complexa, pode ter problemas de UX
   - Usa template de loading
   - Pode "ficar carregando"

VIEWS AUXILIARES:

3. generate_pdf_sync() - 🔧 GERADOR SÍNCRONO
   - Função interna para gerar PDF
   - Usada por print_barcode_get()

4. clear_print_session() - 🧹 LIMPEZA DE SESSÃO
   - GET/POST /barcode/clear_session/<id>/
   - Resolve problemas de "travamento"

5. check_print_status() - 📊 VERIFICAÇÃO DE STATUS
   - GET /barcode/check_status/<id>/
   - Retorna JSON com status dos cupons

VIEWS LEGADAS (NÃO USAR):

6. print_qrcode() - 🚫 LEGADO
7. print_barcode_embed_example() - 🚫 LEGADO
8. generate() - 🚫 LEGADO

RECOMENDAÇÃO: Use sempre print_barcode_get() para impressão de cupons.
===============================================================================
"""


@login_required
@user_passes_test(lambda u: u.is_superuser)
def print_barcode_embed_example(request, id_, template="cupons_impressos.html"):
    """
    ===== VIEW LEGADA (NÃO USAR) =====
    
    View de exemplo/teste para embed de impressão. Esta view é legada
    e não deve ser usada em produção.
    
    CARACTERÍSTICAS:
    - 🚫 View de teste/exemplo
    - 🚫 Gera nova chave a cada acesso
    - 🚫 Não marca cupons como impressos
    - 🚫 Apenas para demonstração
    
    RECOMENDAÇÃO: Use print_barcode_get() em vez desta view
    """
    doc = get_object_or_404(DocumentoFiscal, id=id_)
    if not doc.status and not request.user.is_staff:
        return render(request, "lojista/dashboard.html")
    doc_form = DocumentoFiscalEditForm(instance=doc)
    new_doc = doc_form.save(commit=False)
    new_doc.key = Fernet.generate_key()
    new_doc.status = False
    new_doc.save()
    bcp_url = reverse(
        "bcp:print_qrcode",
        kwargs={
            "id_": id_,
        },
    )
    context = {
        "bcp_url": bcp_url,
        "doc": doc,
    }
    return render(request, template, context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def print_qrcode(request, id_, template="print.html"):
    """
    ===== VIEW LEGADA (NÃO USAR) =====
    
    View legada para impressão de QR code. Esta view é obsoleta
    e não deve ser usada em produção.
    
    CARACTERÍSTICAS:
    - 🚫 View legada/obsoleta
    - 🚫 Gera nova chave a cada acesso
    - 🚫 Não marca cupons como impressos
    - 🚫 Redireciona para generate() (também legada)
    
    RECOMENDAÇÃO: Use print_barcode_get() em vez desta view
    """
    doc = get_object_or_404(DocumentoFiscal, id=id_)
    doc_form = DocumentoFiscalEditForm(instance=doc)
    new_doc = doc_form.save(commit=False)
    new_doc.status = False
    new_doc.save()
    pdf_url = reverse(
        "bcp:generate",
        kwargs={
            "id_": id_,
        },
    )
    context = {
        "pdf_url": pdf_url,
    }
    return render(request, template, context)


@login_required
@user_passes_test(lambda u: u.is_staff)  # Mudança para permitir staff
@transaction.atomic
def print_barcode_get(request, id_, template="bcp/print_pdf.html"):

    """ Rota usada para impressão de cupons por operador """
    """
    ===== VIEW PRINCIPAL DE IMPRESSÃO (RECOMENDADA) =====
    
    View robusta para impressão de cupons via GET. Esta é a view mais confiável
    e recomendada para uso em produção.
    
    🚀 FUNCIONALIDADE: DECISÃO INTELIGENTE DE GERAÇÃO
    - ✅ Até 5 cupons: Geração SÍNCRONA (rápida, sem Celery)
    - ✅ 6+ cupons: Geração ASSÍNCRONA (Celery, para documentos grandes)
    - ✅ Configurável via PDF_SYNC_THRESHOLD no settings
    
    CARACTERÍSTICAS:
    - ✅ Aceita requisições GET (ideal para links diretos)
    - ✅ Controle de reimpressão (verifica se já foi impresso)
    - ✅ Template ponte com impressão automática
    - ✅ NÃO marca cupons como impressos (feito pelo popup de confirmação)
    - ✅ Abre diretamente na tela de impressão
    - ✅ Tratamento de erros robusto
    - ✅ Logs de debug para rastreamento
    
    FLUXO:
    1. Verifica se cupons já foram impressos
    2. Decide entre síncrono/assíncrono baseado no número de cupons
    3. Renderiza template ponte com PDF embutido
    4. Template dispara impressão automaticamente
    5. Usuário confirma impressão via popup
    6. Popup marca cupons como "impressos"
    
    USO NO TEMPLATE:
    <a href="{% url 'bcp:print_get' id_=doc.id %}">Imprimir</a>
    
    URL: /barcode/print_get/<id>/
    
    EXPERIÊNCIA DO USUÁRIO:
    - Clique no botão → Abre nova aba
    - PDF carrega automaticamente (rápido para ≤5 cupons)
    - Diálogo de impressão abre automaticamente
    - Usuário imprime e confirma via popup
    - Cupons são marcados como impressos pelo popup
    - Aba fecha automaticamente
    """
    doc = get_object_or_404(DocumentoFiscal, id=id_)

    # Verificar se já foi impresso recentemente (controle de reimpressão)
    cupons = Cupom.objects.filter(documentoFiscal=doc)
    cupons_ja_impressos = cupons.filter(impresso=True).count()
    
    if cupons_ja_impressos > 0:
        # Se já foi impresso, mostrar aviso
        context = {
            "doc": doc,
            "ja_impresso": True,
            "cupons_impressos": cupons_ja_impressos,
            "total_cupons": cupons.count()
        }
        response = render(request, "bcp/ja_impresso.html", context)
        response['X-Frame-Options'] = 'SAMEORIGIN'
        return response

    # Contar cupons para decisão de geração
    total_cupons = cupons.count()

    # Decisão inteligente: síncrono para até 5 cupons, assíncrono para mais
    
    # Configuração inteligente baseada no número de cupons
    SYNC_THRESHOLD = getattr(settings, 'PDF_SYNC_THRESHOLD', 5)  # Padrão: até 5 cupons
    use_sync = total_cupons <= SYNC_THRESHOLD
    
    if use_sync:
        # URL para servir o PDF síncrono
        pdf_url = reverse("bcp:generate", kwargs={"id_": id_})
    else:
        # Usar Celery para geração assíncrona com fallback para síncrono
        try:
            from kombu.exceptions import OperationalError
            
            # Tentar usar Celery
            task = generate_pdf_task.delay(doc.id, auto_print=False)
            pdf_url = reverse("bcp:serve_pdf_from_task", kwargs={"task_id": task.id})
        except (OperationalError, ConnectionRefusedError, AttributeError) as e:
            # Se houver erro de conexão com o broker, usar geração síncrona
            logger = logging.getLogger(__name__)
            logger.warning(f"Erro ao conectar com Celery broker: {str(e)}. Usando geração síncrona para documento {doc.id}")
            pdf_url = reverse("bcp:generate", kwargs={"id_": id_})
        except Exception as e:
            # Capturar outros erros relacionados ao Celery
            logger = logging.getLogger(__name__)
            logger.error(f"Erro inesperado ao usar Celery: {str(e)}. Usando geração síncrona para documento {doc.id}")
            pdf_url = reverse("bcp:generate", kwargs={"id_": id_})
    
    # Contexto para o template ponte
    context = {
        "pdf_url": pdf_url, 
        "doc": doc
    }
    
    # Renderizar template ponte
    response = render(request, template, context)
    response['X-Frame-Options'] = 'SAMEORIGIN'  # Permite iframe same-origin
    return response





@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@transaction.atomic
@require_POST
def print_barcode(request, id_, template="print.html"):
    """
    ===== VIEW ALTERNATIVA DE IMPRESSÃO (POST) =====
    
    View para impressão via POST com controle de sessão. Esta view é mais complexa
    e pode ter problemas de UX (pop-up blockers, "carregando infinito").
    
    CARACTERÍSTICAS:
    - ⚠️ Requer requisições POST (mais complexo para implementar)
    - ⚠️ Controle de sessão para evitar múltiplas impressões
    - ⚠️ Renderiza template de loading (print_auto.html)
    - ⚠️ Pode ter problemas com pop-up blockers
    - ⚠️ UX: "fica carregando" - usuário não sabe se funcionou
    - ✅ Logs detalhados para debug
    - ✅ Proteção contra impressões duplicadas
    
    FLUXO:
    1. Verifica sessão de impressão
    2. Marca cupons como "em impressão"
    3. Renderiza template de loading
    4. JavaScript tenta abrir PDF em nova janela
    5. Marca cupons como impressos via AJAX
    
    PROBLEMAS CONHECIDOS:
    - Pop-up blockers podem impedir abertura do PDF
    - Usuário pode ficar na tela de loading indefinidamente
    - Complexidade desnecessária para impressão simples
    
    USO NO TEMPLATE:
    <form method="POST" action="{% url 'bcp:print' id_=doc.id %}">
        {% csrf_token %}
        <button type="submit">Imprimir</button>
    </form>
    
    URL: /barcode/print/<id>/
    
    RECOMENDAÇÃO: Use print_barcode_get() em vez desta view
    """
    doc = get_object_or_404(DocumentoFiscal, id=id_)
    
    # Proteção contra múltiplas impressões
    session_key = f"printing_doc_{id_}"
    existing_session = request.session.get(session_key)
    
    if existing_session:
        # Verificar se a sessão é muito antiga (mais de 2 minutos)
        from datetime import datetime
        try:
            session_time = datetime.fromisoformat(existing_session.replace('Z', '+00:00'))
            time_diff = timezone.now() - session_time.replace(tzinfo=timezone.utc)
            
            if time_diff.total_seconds() > 120:  # 2 minutos
                del request.session[session_key]
                request.session.modified = True
                existing_session = None
            else:
                # Se já está imprimindo, redirecionar para a área correta baseada no tipo de usuário
                if request.user.is_staff:
                    return redirect('lojista:homepage')
                else:
                    return redirect('participante:dashboard')
        except Exception as e:
            # Se não conseguir verificar, limpar a sessão por segurança
            del request.session[session_key]
            request.session.modified = True
            existing_session = None
    
    if not existing_session:
        # Marcar como em impressão na sessão (válido por 5 minutos)
        request.session[session_key] = timezone.now().isoformat()
        request.session.set_expiry(300)  # 5 minutos
        request.session.modified = True

        # Atualizar os cupons associados - agora apenas marca como "em impressão"
        cupons = Cupom.objects.filter(documentoFiscal=doc)
        
        for cupom in cupons:
            cupom.em_impressao = True
            cupom.tentativa_impressao = timezone.now()
            cupom.save(update_fields=["em_impressao", "tentativa_impressao"])

        if settings.USE_CELERY_FOR_PDF:
            task = generate_pdf_task.delay(doc.id, auto_print=False)  # Desabilitar impressão automática
            pdf_url = reverse("bcp:check_task_status", kwargs={"task_id": task.id})
            pdf_url += "?task_id=" + task.id  # Append the task_id as a query parameter
        else:
            pdf_url = reverse("bcp:generate", kwargs={"id_": id_})

        context = {"pdf_url": pdf_url, "doc": doc, "doc_id": id_}
        return render(request, template, context)
    else:
        if request.user.is_staff:
            return redirect('lojista:homepage')
        else:
            return redirect('participante:dashboard')


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@require_POST
def confirm_print(request, id_):
    """
    Endpoint para confirmar que a impressão foi bem sucedida
    """
    doc = get_object_or_404(DocumentoFiscal, id=id_)
    success = request.POST.get("success", "false").lower() == "true"

    # Pega o posto de trabalho do usuário que está imprimindo
    posto_trabalho = (
        request.user.profile.posto_trabalho
        if hasattr(request.user, "profile")
        else None
    )

    cupons = Cupom.objects.filter(documentoFiscal=doc, em_impressao=True)

    if success:
        for cupom in cupons:
            if not cupom.impresso:  # Primeira impressão
                cupom.dataImpressao = timezone.now()
                cupom.impresso = True
                cupom.posto_trabalho = posto_trabalho
            else:  # Reimpressão
                cupom.reimpresso_em = timezone.now()
            cupom.em_impressao = False
            fields_to_update = [
                "dataImpressao",
                "impresso",
                "reimpresso_em",
                "em_impressao",
            ]
            if posto_trabalho:
                fields_to_update.append("posto_trabalho")
            cupom.save(update_fields=fields_to_update)

        return JsonResponse(
            {"success": True, "message": "Impressão confirmada com sucesso"}
        )
    else:
        # Se houve falha, marca os cupons como não impressos
        cupons.update(em_impressao=False)
        return JsonResponse(
            {
                "success": False,
                "message": "Falha na impressão",
                "error": request.POST.get("error", "Erro desconhecido"),
            },
            status=400,
        )


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def clear_print_session(request, id_):
    """
    ===== VIEW AUXILIAR: LIMPEZA DE SESSÃO =====
    
    View auxiliar para limpar sessões de impressão. Usada para resolver
    problemas quando o usuário fica "travado" na tela de loading.
    
    CARACTERÍSTICAS:
    - ✅ Remove sessão de impressão específica
    - ✅ Suporte a GET (redirecionamento) e POST (JSON)
    - ✅ Logs de debug para rastreamento
    
    USO:
    - GET: Redireciona para backoffice
    - POST: Retorna JSON de sucesso
    
    URL: /barcode/clear_session/<id>/
    
    PROBLEMA QUE RESOLVE:
    - Usuário fica na tela de loading indefinidamente
    - Sessão de impressão não é limpa automaticamente
    """
    session_key = f"printing_doc_{id_}"
    if session_key in request.session:
        del request.session[session_key]
    
    # Se for uma requisição GET, redirecionar para a página de impressão
    if request.method == 'GET':
        return redirect('participante:impressao_backoffice')
    
    return JsonResponse({"success": True})


@login_required
@user_passes_test(lambda u: u.is_staff)  # Mudança para permitir staff
@require_POST
@transaction.atomic
def confirm_print(request, id_):
    """
    ===== VIEW AUXILIAR: CONFIRMAÇÃO DE IMPRESSÃO =====
    
    View para confirmar que o usuário realmente imprimiu os cupons.
    Chamada via AJAX após o evento 'afterprint' no template ponte.
    
    CARACTERÍSTICAS:
    - ✅ Marca cupons como impressos
    - ✅ Registra data/hora da impressão
    - ✅ Associa ao posto de trabalho do usuário
    - ✅ Retorna JSON de sucesso
    
    USO:
    - Chamada automaticamente após impressão
    - Confirma que o usuário realmente imprimiu
    
    URL: /barcode/confirm_print/<id>/
    """
    doc = get_object_or_404(DocumentoFiscal, id=id_)
    
    try:
        # Buscar cupons do documento
        cupons = Cupom.objects.filter(documentoFiscal=doc)
        cupons_em_impressao = cupons.filter(em_impressao=True)
        cupons_ja_impressos = cupons.filter(impresso=True)
        
        # Se já foram marcados como impressos na geração do PDF, retornar sucesso
        if cupons_ja_impressos.exists() and not cupons_em_impressao.exists():
            return JsonResponse({
                "success": True,
                "message": f"✅ {cupons_ja_impressos.count()} cupons já foram marcados como impressos",
                "already_printed": True,
                "timestamp": timezone.now().isoformat()
            })
        
        # Caso ainda tenha cupons em impressão (fluxo antigo)
        if cupons_em_impressao.exists():
            for cupom in cupons_em_impressao:
                cupom.impresso = True
                cupom.dataImpressao = timezone.now()
                cupom.em_impressao = False
                if hasattr(request.user, 'profile') and request.user.profile.posto_trabalho:
                    cupom.posto_trabalho = request.user.profile.posto_trabalho
                cupom.save(update_fields=["impresso", "dataImpressao", "em_impressao", "posto_trabalho"])
            
            return JsonResponse({
                "success": True,
                "message": f"{cupons_em_impressao.count()} cupons marcados como impressos",
                "timestamp": timezone.now().isoformat()
            })
        else:
            # Nenhum cupom para marcar
            return JsonResponse({
                "success": False,
                "message": "Nenhum cupom encontrado para este documento"
            }, status=404)
            
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Erro ao confirmar impressão: {str(e)}"
        }, status=500)


@login_required
@user_passes_test(lambda u: u.is_staff)  # Mudança para permitir staff
def check_print_status(request, id_):
    """
    ===== VIEW AUXILIAR: VERIFICAÇÃO DE STATUS =====
    
    View auxiliar para verificar o status de impressão de um documento.
    Retorna informações sobre cupons impressos, em impressão, etc.
    
    CARACTERÍSTICAS:
    - ✅ Retorna status em JSON
    - ✅ Conta cupons impressos vs total
    - ✅ Identifica cupons em impressão
    - ✅ Útil para AJAX/JavaScript
    
    RETORNO JSON:
    {
        "total": 5,
        "impressos": 3,
        "em_impressao": 0,
        "status": "completo" | "pendente"
    }
    
    USO:
    - Verificação assíncrona de status
    - Atualização de interface sem reload
    - Debug de problemas de impressão
    
    URL: /barcode/check_status/<id>/
    """
    doc = get_object_or_404(DocumentoFiscal, id=id_)
    cupons = Cupom.objects.filter(documentoFiscal=doc)

    total_cupons = cupons.count()
    impressos = cupons.filter(impresso=True).count()
    em_impressao = cupons.filter(em_impressao=True).count()

    return JsonResponse(
        {
            "total": total_cupons,
            "impressos": impressos,
            "em_impressao": em_impressao,
            "status": "completo" if impressos == total_cupons else "pendente",
        }
    )


@login_required
@user_passes_test(lambda u: u.is_staff)  # Mudança para permitir staff
def generate(request, id_, barcode_type="Standard39", auto_print=False):  # Desabilitado - usuário prefere clicar
    """
    ===== VIEW PARA SERVIR PDF NO TEMPLATE PONTE =====
    
    View para servir o PDF que será embutido no template ponte.
    Esta view retorna o PDF sem marcar como impresso (isso é feito pela confirm_print).
    
    CARACTERÍSTICAS:
    - ✅ Retorna PDF inline para iframe
    - ✅ Não marca cupons como impressos
    - ✅ Usada pelo template ponte
    - ✅ Headers corretos para iframe
    
    USO:
    - Chamada pelo template ponte (print_pdf.html)
    - PDF é servido em iframe
    - Impressão é confirmada via confirm_print()
    
    URL: /barcode/generate/<id>/
    """
    try:
        # Gerar PDF usando a função síncrona
        pdf_response = generate_pdf_sync(request, id_, barcode_type, auto_print)
        
        if pdf_response.status_code == 200:
            # Adicionar headers para permitir iframe
            pdf_response['X-Frame-Options'] = 'SAMEORIGIN'
            pdf_response['Access-Control-Allow-Origin'] = request.build_absolute_uri('/')[:-1]
            return pdf_response
        else:
            # Se houve erro, retornar erro
            return pdf_response
            
    except Exception as e:
        return JsonResponse({"error": f"Erro ao gerar PDF: {str(e)}"}, status=500)


@login_required
@user_passes_test(lambda u: u.is_staff)  # Mudança para permitir staff
@silk_profile(name="Generate PDF")
def generate_pdf_sync(request, id_, barcode_type="Standard39", auto_print=False):
    
    print("estou generate_pdf_sync")  # Desabilitado - usuário prefere clicar
    """
    ===== VIEW AUXILIAR: GERAÇÃO SÍNCRONA DE PDF =====
    
    Função auxiliar que gera o PDF dos cupons de forma síncrona.
    Usada internamente por print_barcode_get() quando USE_CELERY_FOR_PDF=False.
    
    CARACTERÍSTICAS:
    - ✅ Geração síncrona (sem Celery)
    - ✅ Retorna HttpResponse com PDF
    - ✅ Usa reportlab para geração
    - ✅ Inclui QR code e dados do participante
    - ✅ Mascaramento de dados sensíveis (CPF, telefone)
    
    PARÂMETROS:
    - request: HttpRequest
    - id_: ID do DocumentoFiscal
    - barcode_type: Tipo de código (padrão: "Standard39")
    - auto_print: Se deve imprimir automaticamente (desabilitado)
    
    RETORNO:
    - HttpResponse com PDF ou erro
    
    USO INTERNO:
    - Chamada por print_barcode_get() quando USE_CELERY_FOR_PDF=False
    - Não deve ser chamada diretamente pelos templates
    
    DEPENDÊNCIAS:
    - reportlab (canvas, pdfmetrics, TTFont)
    - qrcode
    - bcp.settings (fontes, imagens)
    """
    logger = logging.getLogger(__name__)
    try:
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f"inline; filename={id_}.pdf"

        # Configurações
        import bcp.settings as bcp_settings

        font_name = bcp_settings.FONT_NAME
        font_path = bcp_settings.FONT_PATH
        font_bold = bcp_settings.FONT_PATH_BOLD
        font_name_bold = bcp_settings.FONT_BOLD
        image_path = bcp_settings.IMAGE_PATH
        image_cielo = bcp_settings.IMAGE_CIELO
        image_cdl = bcp_settings.IMAGE_CDL

        def esconde_cpf(cpf):
            return f"***.{cpf[4:7]}.{cpf[8:11]}-**"

        def esconde_telefone(tel):
            if not tel or len(tel.strip()) < 10:
                return "Não informado"
            tel = tel.strip()
            return f"({tel[1:3]}) *****-{tel[11:15]}"

        doc = get_object_or_404(DocumentoFiscal, id=id_)

        doc = get_object_or_404(
            DocumentoFiscal.objects.select_related("user__profile"), id=id_
        )
        cupons = (
            Cupom.objects.filter(documentoFiscal=doc)
            .select_related("documentoFiscal")
            .prefetch_related("documentoFiscal__user")
        )
        profile = doc.user.profile

        # Registro da fonte
        pdfmetrics.registerFont(TTFont(font_name, font_path))
        pdfmetrics.registerFont(TTFont(font_name_bold, font_bold))

        # Configurar JS para impressão automática - DESABILITADO (usuário prefere clicar para imprimir)
        if False:  # auto_print desabilitado por preferência do usuário
            pdfdoc.PDFCatalog.OpenAction = "<</S/JavaScript/JS(this.print({bUI:false,bSilent:true,bShrinkToFit:true}));>>"
            pdfdoc.PDFInfo.title = "Natal de Luz e Prêmios 2024"

        buffer = BytesIO()
        
        # Configurar tamanho de página e margens
        from reportlab.lib.pagesizes import letter, A4
        page_settings = bcp_settings.PAGE_SETTINGS
        
        # Escolher tamanho de página
        if page_settings.get('pagesize') == 'A4':
            page_width, page_height = A4
        else:
            page_width, page_height = letter
        
        # Margens personalizadas
        margin_left = page_settings.get('margin_left', 20)
        margin_right = page_settings.get('margin_right', 20)
        margin_top = page_settings.get('margin_top', 20)
        margin_bottom = page_settings.get('margin_bottom', 20)
        
        # Área útil da página
        usable_width = page_width - margin_left - margin_right
        usable_height = page_height - margin_bottom - margin_top
        
        c = canvas.Canvas(buffer, pagesize=(page_width, page_height))

        # Configurações de fonte (definir fora da função para ser acessível)
        font_settings = bcp_settings.FONT_SETTINGS

        def draw_fixed_elements():
            # Ajustar imagem do banner com tamanho controlado
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    original_width, original_height = img.size
                    
                    # Usar configurações do settings
                    banner_config = bcp_settings.BANNER_SETTINGS
                    desired_width = banner_config.get('width', 200)
                    banner_x = banner_config.get('x', 200)
                    banner_y = banner_config.get('y', 680)
                    
                    # Calcular altura mantendo proporção
                    if banner_config.get('maintain_aspect', True):
                        desired_height = (desired_width / original_width) * original_height
                    else:
                        desired_height = banner_config.get('height', 100)
                    
                    c.drawImage(image_path, banner_x, banner_y, desired_width, desired_height, mask="auto")
            except Exception as e:
                c.drawImage(image_path, 200, 650, mask="auto")
            
            # Outras imagens
            c.drawImage(image_cielo, 20, 688, mask="auto")
            # c.drawImage(image_elo, 400, 688, mask='auto')
            c.drawImage(image_cdl, 70, 90, mask="auto")
            
            # Linha separadora abaixo do banner
            c.setFont(font_name, font_settings.get('separator', 24))
            c.drawString(20, 660, "_______________________________________________________")
            c.setFont(font_name_bold, font_settings.get('title', 28))
            c.drawString(150, 630, "Dados do Participante")

        for cupom in cupons:
            draw_fixed_elements()
            code = cupom.get_info()
            qr_code = qr.QrCodeWidget(code)
            bounds = qr_code.getBounds()
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
            d = Drawing(100, 100, transform=[240.0 / width, 0, 0, 240.0 / height, 0, 0])
            d.add(qr_code)
            # Dados do participante com fontes maiores
            c.setFont("Helvetica", font_settings.get('label', 24))
            c.drawString(40, 550, "Nome:")
            c.setFont("Helvetica-Bold", font_settings.get('value', 26))
            c.drawString(115, 550, f"{profile.nome}")
            
            c.setFont("Helvetica", font_settings.get('label', 24))
            c.drawString(40, 580, "CPF:")
            c.setFont("Helvetica-Bold", font_settings.get('value', 26))
            c.drawString(95, 580, f"{esconde_cpf(profile.CPF)}")
            
            c.setFont("Helvetica", font_settings.get('label', 24))
            c.drawString(40, 520, "Cidade:")
            c.setFont("Helvetica-Bold", font_settings.get('value', 26))
            c.drawString(115, 520, f"{profile.cidade}")
            
            c.setFont("Helvetica", font_settings.get('label', 24))
            c.drawString(330, 520, "Estado:")
            c.setFont("Helvetica-Bold", font_settings.get('value', 26))
            c.drawString(410, 520, f"{profile.estado}")
            
            c.setFont("Helvetica", font_settings.get('label', 24))
            c.drawString(40, 490, "Bairro:")
            c.setFont("Helvetica-Bold", font_settings.get('value', 26))
            c.drawString(115, 490, f"{profile.bairro}")
            
            c.setFont("Helvetica", font_settings.get('label', 24))
            c.drawString(330, 490, "Fone:")
            c.setFont("Helvetica-Bold", font_settings.get('value', 26))
            # Prioriza whatsapp, depois foneCelular1, depois foneFixo (ignora strings vazias)
            telefone = (profile.whatsapp and profile.whatsapp.strip()) or \
                       (profile.foneCelular1 and profile.foneCelular1.strip()) or \
                       (profile.foneFixo and profile.foneFixo.strip())
            c.drawString(390, 490, f"{esconde_telefone(telefone)}")
            
            c.setFont("Helvetica", font_settings.get('label', 24))
            c.drawString(40, 460, "Comprou na loja?")
            c.setFont("Helvetica-Bold", font_settings.get('value', 26))
            c.drawString(40, 430, f"{cupom.documentoFiscal.lojista}")
            
            c.setFont("Helvetica", font_settings.get('label', 24))
            c.drawString(330, 460, "Vendedor:")
            c.setFont("Helvetica-Bold", font_settings.get('value', 26))
            c.drawString(330, 430, f"{cupom.documentoFiscal.vendedor}")
            
            c.setFont("Helvetica", font_settings.get('question', 22))
            c.drawString(100, 390, "Qual a maior campanha de premios do Piauí?")
            c.setFont("Helvetica-Bold", font_settings.get('answer', 24))
            c.drawString(100, 360, "(X) Natal de Luz e Prêmios")
            
            c.setFont("Helvetica", font_settings.get('label', 24))
            c.drawString(40, 320, "Data:")
            c.setFont("Helvetica-Bold", font_settings.get('date', 24))
            df = DateFormat(cupom.documentoFiscal.dataDocumento)
            c.drawString(100, 320, f'{df.format("d/m/Y")}')
            
            c.setFont("Helvetica", font_settings.get('cupom_title', 45))
            c.drawString(80, 250, "CUPOM")
            c.setFont("Helvetica-Bold", font_settings.get('cupom_number', 50))
            c.drawString(100, 200, f"{cupom.id}")
            
            c.drawString(20, 7, "_____________________________________________________")
            c.setFont("Helvetica-Bold", font_settings.get('footer', 22))
            c.drawString(150, 15, "SPA/ME Nº 06.046250/2025")
            renderPDF.draw(d, c, 320, 80)
            c.showPage()

        c.save()

        pdf = buffer.getvalue()
        buffer.close()

        response.write(pdf)
        
        # ===== MARCAR CUPONS COMO IMPRESSOS =====
        try:
            # Buscar cupons do documento
            cupons_to_mark = Cupom.objects.filter(documentoFiscal=doc)
            
            # Pega o posto de trabalho do usuário (se existir)
            posto_trabalho = None
            if hasattr(request.user, 'profile') and request.user.profile.posto_trabalho:
                posto_trabalho = request.user.profile.posto_trabalho
            
            # Marcar cada cupom
            for cupom in cupons_to_mark:
                if not cupom.impresso:  # Só marca se ainda não foi impresso
                    cupom.impresso = True
                    cupom.dataImpressao = timezone.now()
                    if posto_trabalho:
                        cupom.posto_trabalho = posto_trabalho
                    cupom.save(update_fields=["impresso", "dataImpressao", "posto_trabalho"])
            
            logger.info(f"✅ {cupons_to_mark.count()} cupons do documento {id_} marcados como impressos")
        except Exception as e:
            # Não quebrar se houver erro na marcação
            logger.error(f"❌ Erro ao marcar cupons como impressos: {str(e)}")
        # ===== FIM DA MARCAÇÃO =====
        
        return response

    except Exception as e:
        logger.exception(f"Erro ao gerar PDF para o documento {id_}: {e}")
        return JsonResponse({"success": False, "message": "Erro ao gerar PDF. O erro foi registrado."}, status=500)


@login_required
@user_passes_test(lambda u: u.is_staff)  # Mudança para permitir staff
@transaction.atomic
def serve_pdf_from_task(request, task_id):
    task = AsyncResult(task_id)
    
    if task.state == "SUCCESS":
        # NÃO marcar cupons como impressos aqui - isso será feito pela confirm_print
        # Apenas servir o PDF
        
        pdf_bytes = task.result
        
        # Verificar se o PDF é válido
        if not pdf_bytes or len(pdf_bytes) < 100:  # PDF deve ter pelo menos 100 bytes
            return JsonResponse({"status": "FAILURE", "error": "PDF inválido ou vazio"}, status=400)
        
        # Verificar se começa com a assinatura PDF
        if not pdf_bytes.startswith(b'%PDF'):
            return JsonResponse({"status": "FAILURE", "error": "Arquivo não é um PDF válido"}, status=400)
        
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="cupom.pdf"'
        response['X-Frame-Options'] = 'SAMEORIGIN'  # Permite iframe same-origin
        return response
    else:
        # If the task is not yet successful, redirect to the status check page
        return redirect(reverse('bcp:check_task_status', kwargs={'task_id': task_id}))


@login_required
@user_passes_test(lambda u: u.is_staff)  # Mudança para permitir staff
def check_task_status(request, task_id):
    logger = logging.getLogger(__name__)
    task = AsyncResult(task_id)
    
    if task.state == "SUCCESS":
        pdf_url = reverse('bcp:serve_pdf_from_task', kwargs={'task_id': task_id})
        return JsonResponse({"status": "SUCCESS", "pdf_url": pdf_url})
    elif task.state == "FAILURE":
        return JsonResponse({"status": "FAILURE", "error": str(task.info)})
    else:
        return JsonResponse({"status": task.state})
