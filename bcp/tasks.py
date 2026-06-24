from io import BytesIO
import os
import logging

from celery import shared_task
from django.shortcuts import get_object_or_404
from django.utils.dateformat import DateFormat
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.pdfbase import pdfdoc, pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import bcp.settings as bcp_settings
from cupom.models import Cupom
from participante.models import DocumentoFiscal

logger = logging.getLogger(__name__)





@shared_task
def generate_pdf_task(doc_id, auto_print=True):  # Desabilitado - usuário prefere clicar
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
    
    logger.info(f"Página configurada: {page_width}x{page_height}, margens: {margin_left}/{margin_right}/{margin_top}/{margin_bottom}")
    
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))

    # Configurações
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

    doc = get_object_or_404(
        DocumentoFiscal.objects.select_related("user__profile"), id=doc_id
    )
    cupons = (
        Cupom.objects.filter(documentoFiscal=doc)
        .select_related("documentoFiscal")
        .prefetch_related("documentoFiscal__user")
    )
    profile = doc.user.profile

    pdfmetrics.registerFont(TTFont(font_name, font_path))
    pdfmetrics.registerFont(TTFont(font_name_bold, font_bold))

    # Configurar JS para impressão automática - DESABILITADO (usuário prefere clicar para imprimir)
    if False:  # auto_print desabilitado por preferência do usuário
        pdfdoc.PDFCatalog.OpenAction = "<</S/JavaScript/JS(this.print({bUI:false,bSilent:true,bShrinkToFit:true}));>>"
        pdfdoc.PDFInfo.title = "Natal de Luz e Prêmios"

    # Configurações de fonte - movido para escopo principal
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
                logger.info(f"Banner ajustado: {original_width}x{original_height} -> {desired_width:.0f}x{desired_height:.0f}")
        except Exception as e:
            logger.warning(f"Erro ao ajustar banner, usando tamanho original: {e}")
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
        vendedor = cupom.documentoFiscal.vendedor
        vendedor_str = vendedor if vendedor is not None else "N/A"
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
        c.drawString(330, 430, f"{vendedor_str}")
        
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
    
    # ===== MARCAR CUPONS COMO IMPRESSOS =====
    try:
        from django.utils import timezone
        
        doc_to_mark = DocumentoFiscal.objects.get(id=doc_id)
        cupons_to_mark = Cupom.objects.filter(documentoFiscal=doc_to_mark)
        
        # Marcar cada cupom
        for cupom in cupons_to_mark:
            if not cupom.impresso:  # Só marca se ainda não foi impresso
                cupom.impresso = True
                cupom.dataImpressao = timezone.now()
                cupom.save(update_fields=["impresso", "dataImpressao"])
        
        logger.info(f"✅ {cupons_to_mark.count()} cupons do documento {doc_id} marcados como impressos (Celery)")
    except Exception as e:
        # Não quebrar se houver erro na marcação
        logger.error(f"❌ Erro ao marcar cupons como impressos (Celery): {str(e)}")
    # ===== FIM DA MARCAÇÃO =====

    return pdf



