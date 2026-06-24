import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class DebugMiddleware:
    """
    Middleware para gerenciar logs e debug do sistema.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Executa antes da view
        if settings.DEBUG:
            self._log_request_info(request)

        response = self.get_response(request)

        # Executa depois da view
        if settings.DEBUG:
            self._log_response_info(response)

        return response

    def _log_request_info(self, request):
        """Registra informações da requisição"""
        logger.debug(f"[REQUEST] {request.method} {request.path}")
        
        if request.user.is_authenticated:
            logger.debug(f"[USER] {request.user.username}")
            if hasattr(request.user, 'profile') and request.user.profile:
                logger.debug(f"[PROFILE] Exists: True")
                logger.debug(f"[PROFILE] Temporary Password: {request.user.profile.senha_temporaria}")
            else:
                logger.debug("[PROFILE] Exists: False")

        # Log CSRF token apenas em DEBUG
        if request.method == "POST":
            csrf_token = request.META.get('CSRF_COOKIE', None)
            if csrf_token:
                logger.debug("[CSRF] Token present in cookie")
            else:
                logger.warning("[CSRF] Token missing from cookie")

    def _log_response_info(self, response):
        """Registra informações da resposta"""
        logger.debug(f"[RESPONSE] Status: {response.status_code}")
        
        # Log de cards não associados
        if hasattr(response, 'context_data') and response.context_data:
            unassigned_cards = response.context_data.get('unassigned_cards', [])
            if unassigned_cards:
                logger.warning(f"[CARDS] Unassigned: {', '.join(unassigned_cards)}")
