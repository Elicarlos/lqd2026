from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def render_dashboard_card(card, card_type=None):
    """
    Renderiza um card do dashboard com base no tipo.
    """
    if not card:
        return ""
    
    # Definir cores por tipo
    color_map = {
        'participantes': 'primary',
        'lojistas': 'info', 
        'configuracoes': 'secondary',
        'backoffice': 'purple',
        'relatorios': 'success',
        'documentos': 'warning',
        'usuarios': 'indigo',
        'campanha': 'danger',
        'ponto': 'info',
        'impressao': 'warning',
        'estatisticas': 'info',
    }
    
    # Usar cor do card ou cor padrão do tipo
    color = card.cor or color_map.get(card.tipo, 'primary')
    
    # Construir URL - verificar se é link externo ou interno
    is_external = False
    if card.url:
        if card.url.startswith(('http://', 'https://', 'www.')):
            # Link externo
            url = card.url
            is_external = True
        else:
            # URL interna do Django
            try:
                url = reverse(card.url)
            except:
                url = card.url if card.url.startswith('/') else '#'
    else:
        url = '#'
    
    # Target para links externos
    target = 'target="_blank" rel="noopener noreferrer"' if is_external else ''
    
    # Definir cores CSS personalizadas para os cards
    color_styles = {
        'primary': {'bg': '#e7f1ff', 'text': '#0d6efd', 'border': '#b3d7ff'},
        'info': {'bg': '#e7f8ff', 'text': '#0dcaf0', 'border': '#b3e8ff'},
        'secondary': {'bg': '#f8f9fa', 'text': '#6c757d', 'border': '#dee2e6'},
        'success': {'bg': '#e7f7ed', 'text': '#198754', 'border': '#b3e8c3'},
        'warning': {'bg': '#fff8e1', 'text': '#ffc107', 'border': '#ffeaa7'},
        'danger': {'bg': '#ffe7e7', 'text': '#dc3545', 'border': '#ffb3b3'}
    }
    
    # Verificar se a cor é um código hexadecimal
    if color.startswith('#'):
        # Gerar cores baseadas no hexadecimal
        hex_color = color
        # Criar versão mais clara para background (20% de opacidade)
        bg_color = hex_color + '20'  # Adicionar 20% de opacidade
        # Criar versão mais escura para border (40% de opacidade)
        border_color = hex_color + '40'  # Adicionar 40% de opacidade
        
        card_color = {
            'bg': bg_color,
            'text': hex_color,
            'border': border_color
        }
    else:
        # Usar cores predefinidas para nomes Bootstrap
        card_color = color_styles.get(color, color_styles['primary'])
    
    # HTML do card
    html = f'''
    <a href="{url}" {target} 
       class="card-link d-flex align-items-center p-3 bg-white rounded-4 border border-light-subtle text-decoration-none text-dark transition-all shadow-sm"
       style="min-height: 80px; border-color: {card_color['border']};">
        <div class="d-flex align-items-start gap-3 flex-grow-1">
            <div class="rounded-3 p-2 d-flex align-items-center justify-content-center flex-shrink-0" style="width: 40px; height: 40px; background-color: {card_color['bg']};">
                <i class="{card.icone}" style="color: {card_color['text']}; font-size: 1.1rem;"></i>
            </div>
            <div class="flex-grow-1 min-w-0 d-flex flex-column justify-content-center">
                <p class="fw-semibold text-dark mb-1 fs-6" style="word-wrap: break-word; overflow-wrap: break-word;">{card.titulo}</p>
                <p class="small text-muted mb-0 opacity-75" style="word-wrap: break-word; overflow-wrap: break-word; line-height: 1.2;">{card.descricao}</p>
            </div>
        </div>
        <div class="rounded-circle p-2 d-flex align-items-center justify-content-center flex-shrink-0 ms-auto align-self-start" style="width: 32px; height: 32px; background-color: {card_color['bg']};">
            <i class="fas fa-chevron-right small" style="color: {card_color['text']};"></i>
        </div>
    </a>
    '''
    
    return mark_safe(html)


@register.simple_tag
def render_card_section(cards, section_title, section_icon, section_color):
    """
    Renderiza uma seção completa de cards.
    """
    if not cards:
        return ""
    
    cards_html = ""
    for card in cards:
        cards_html += render_dashboard_card(card)
    
    # Se a cor é hexadecimal, usar diretamente
    if section_color.startswith('#'):
        header_bg = f'linear-gradient(135deg, {section_color} 0%, {section_color}dd 100%)'
    else:
        # Fallback para cores predefinidas
        color_styles = {
            'primary': 'linear-gradient(135deg, #0d6efd 0%, #0b5ed7 100%)',
            'info': 'linear-gradient(135deg, #0dcaf0 0%, #0aa2c0 100%)',
            'secondary': 'linear-gradient(135deg, #6c757d 0%, #5c636a 100%)',
            'success': 'linear-gradient(135deg, #198754 0%, #157347 100%)',
            'warning': 'linear-gradient(135deg, #ffc107 0%, #e0a800 100%)',
            'danger': 'linear-gradient(135deg, #dc3545 0%, #bb2d3b 100%)'
        }
        header_bg = color_styles.get(section_color, color_styles['primary'])
    
    html = f'''
    <div class="card bg-white rounded-4 shadow-sm border-0 overflow-hidden h-100">
        <div class="card-header text-white border-0 p-3" style="background: {header_bg};">
            <div class="d-flex align-items-center justify-content-between">
                <h3 class="h5 fw-bold text-white mb-0">{section_title}</h3>
                <div class="bg-white bg-opacity-20 rounded-circle p-2 d-flex align-items-center justify-content-center" style="width: 32px; height: 32px;">
                    <i class="{section_icon} text-white small"></i>
                </div>
            </div>
        </div>
        <div class="card-body p-3">
            <div class="d-flex flex-column gap-2">
                {cards_html}
            </div>
        </div>
    </div>
    '''
    
    return mark_safe(html)


@register.simple_tag
def get_dashboard_cards(card_type):
    """
    Retorna os cards baseados no tipo especificado.
    """
    # Aqui você pode implementar a lógica para retornar cards específicos
    # Por enquanto, retorna uma lista vazia para evitar erros
    return []


@register.simple_tag
def get_section_config(card_type, user=None):
    """
    Retorna a configuração de uma seção baseada no tipo de card.
    """
    from participante.models import ConfiguracaoSecao
    
    # Buscar configuração no banco de dados
    config = ConfiguracaoSecao.get_config(card_type)
    
    # Verificar se o usuário pode ver esta seção
    if user and not config.pode_ver(user):
        return None
    
    return {
        'title': config.titulo,
        'icon': config.icone,
        'color': config.cor
    }