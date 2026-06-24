import logging
from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

logger = logging.getLogger(__name__)

@receiver(user_logged_out)
def limpar_posto_ao_logout(sender, request, user, **kwargs):
    """Limpa o posto de trabalho quando o usuário faz logout"""
    if user and hasattr(user, 'profile') and user.profile:
        if user.profile.posto_trabalho:
            logger.info(f"Limpando posto de trabalho para {user.username} ao fazer logout")
            user.profile.posto_trabalho = None
            user.profile.save(update_fields=['posto_trabalho'])
