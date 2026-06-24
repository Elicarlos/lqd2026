# Settings for barcode printer

import os

# Barcode
BAR_HEIGHT = 30
BAR_WIDTH = 0.75  # default is 0.54
BAR_QUIET = False  # include l/r whitespace padding.
BAR_CHECKSUM = True

# Label Config
FONT_SIZE = 8
FONT_NAME = "regular"
FONT_PATH = os.path.join(
    os.path.split(__file__)[0],
    "fonts",
    "lucida_sans_regular.ttf",
)

IMAGE_PATH = os.path.join(
    os.path.split(__file__)[0],
    "img",
    "bannner.png",
)

IMAGE_CIELO = os.path.join(
    os.path.split(__file__)[0],
    "img",
    "logo-Cielo.png",
)
# IMAGE_POP = os.path.join(os.path.split(__file__)[0], 'img', 'pop.png',)
IMAGE_ELO = os.path.join(
    os.path.split(__file__)[0],
    "img",
    "elo.png",
)
IMAGE_CDL = os.path.join(
    os.path.split(__file__)[0],
    "img",
    "cdl.png",
)
IMAGE_MARKO = os.path.join(
    os.path.split(__file__)[0],
    "img",
    "solution.png",
)

FONT_BOLD = "bold"
FONT_PATH_BOLD = os.path.join(
    os.path.split(__file__)[0],
    "fonts",
    "LSANS.TTF",
)
# Configurações de compressão de imagens para PDF
# 
# CONTROLES DE QUALIDADE:
# - enabled: True/False para habilitar/desabilitar compressão
# - max_width/max_height: Dimensões máximas (só redimensiona se exceder)
# - quality: Qualidade JPEG (95 = muito alta, 85 = alta, 70 = média)
# - preserve_original_size: True = mantém tamanho se já for pequeno
#
# CONFIGURAÇÕES RECOMENDADAS:
# - Alta qualidade: quality=95, max_width=500, max_height=300
# - Qualidade média: quality=85, max_width=400, max_height=250
# - Sem compressão: enabled=False
IMAGE_OPTIMIZATION = {
    'enabled': False,  # Compressão desabilitada para manter qualidade original
    'max_width': 500,
    'max_height': 300,
    'quality': 95,
    'formats': ['jpg', 'jpeg', 'png'],
    'preserve_original_size': True,  # Don't resize if image is already small
}

# Configurações específicas por imagem
IMAGE_SETTINGS = {
    'banner': {
        'max_width': 400,
        'max_height': 200,
        'quality': 95,
    },
    'cielo': {
        'max_width': 300,
        'max_height': 150,
        'quality': 95,
    },
    'cdl': {
        'max_width': 250,
        'max_height': 120,
        'quality': 95,
    },
}

# Configuração para decisão inteligente de geração de PDF
# Pode ser configurado via variável de ambiente no Heroku: PDF_SYNC_THRESHOLD
PDF_SYNC_THRESHOLD = int(os.environ.get('PDF_SYNC_THRESHOLD', 30))  # Padrão: 30 cupons  

# Configurações de posicionamento do banner
BANNER_SETTINGS = {
    'width': 200,      # Largura desejada em pontos
    'x': 200,          # Posição X (horizontal)
    'y': 650,          # Posição Y (vertical) - diminuído para descer a imagem
    'maintain_aspect': True,  # Manter proporção original
}

# Configurações de página e margens
# 
# CONTROLES DE LAYOUT:
# - pagesize: 'letter' (padrão) ou 'A4'
# - margin_*: Margens em pontos (1 ponto = 1/72 polegada)
#
# TAMANHOS DE PÁGINA:
# - letter: 612x792 pontos (8.5" x 11")
# - A4: 595x842 pontos (210mm x 297mm)
#
# AJUSTES DE MARGEM:
# - Para reduzir margem direita: diminua margin_right
# - Para centralizar conteúdo: ajuste margin_left e margin_right
# - Para mais espaço: diminua todas as margens
PAGE_SETTINGS = {
    'pagesize': 'letter',  # Tamanho da página (letter, A4, etc.)
    'margin_left': 10,     # Margem esquerda em pontos
    'margin_right': 5,    # Margem direita em pontos
    'margin_top': 20,      # Margem superior em pontos
    'margin_bottom': 20,   # Margem inferior em pontos
}

# Configurações de tamanho de fonte[padrão]
FONT_SETTINGS = {
    'title': 28,          # Título principal (Dados do Participante)
    'label': 24,          # Labels (Nome:, CPF:, etc.)
    'value': 26,          # Valores (dados do participante)
    'question': 22,       # Pergunta da campanha
    'answer': 24,         # Resposta da campanha
    'date': 24,           # Data
    'cupom_title': 45,    # Título CUPOM
    'cupom_number': 50,   # Número do cupom
    'footer': 22,         # Texto do rodapé
    'separator': 24,      # Linha separadora
}



# NB It's a better idea to put your settings in a local_settings.py overrides file.
