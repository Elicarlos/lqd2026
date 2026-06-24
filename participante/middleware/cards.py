import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class CardsMiddleware:
    """
    Middleware para gerenciar os cards do sistema.
    Garante que todos os cards estejam corretamente associados e visíveis
    apenas para os usuários apropriados.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Define os cards e suas permissões
        self.cards_config = {
            'Localizações': {
                'groups': ['Administrador', 'Supervisor'],
                'url': 'lojista:lista_localizacao',
                'icon': 'fas fa-map-marker-alt',
                'description': 'Gerenciar localizações'
            },
            'Postos de Trabalho': {
                'groups': ['Administrador', 'Supervisor'],
                'url': 'lojista:listar-postos',
                'icon': 'fas fa-building',
                'description': 'Gerenciar postos de trabalho'
            },
            'Ramos de Atividade': {
                'groups': ['Administrador', 'Supervisor'],
                'url': 'lojista:listatividade',
                'icon': 'fas fa-store',
                'description': 'Gerenciar ramos de atividade'
            }
        }

    def __call__(self, request):
        response = self.get_response(request)
        
        # Processa apenas respostas HTML com contexto
        if hasattr(response, 'context_data') and response.context_data:
            self._process_cards(request, response)
            
        return response

    def _process_cards(self, request, response):
        """Processa os cards baseado nas permissões do usuário"""
        if not request.user.is_authenticated:
            return

        # Lista para armazenar cards não associados
        unassigned_cards = []
        
        # Lista para armazenar cards que o usuário tem acesso
        available_cards = []
        
        for card_name, config in self.cards_config.items():
            # Verifica se o usuário tem permissão para ver o card
            has_permission = any(
                request.user.groups.filter(name=group).exists() 
                for group in config['groups']
            )
            
            if has_permission:
                available_cards.append({
                    'name': card_name,
                    'url': config['url'],
                    'icon': config['icon'],
                    'description': config['description']
                })
            else:
                unassigned_cards.append(card_name)

        # Atualiza o contexto da resposta
        response.context_data['available_cards'] = available_cards
        response.context_data['unassigned_cards'] = unassigned_cards
        
        # Log em DEBUG
        if settings.DEBUG and unassigned_cards:
            logger.warning(
                f"⚠️  CARDS SEM ASSOCIAÇÃO: {unassigned_cards}"
            )
