import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ParticipanteConfig(AppConfig):
    name = "participante"

    def ready(self) -> None:
        try:
            import participante.signals  # noqa
            logger.info("Participante signals loaded successfully")
        except Exception as e:
            logger.error(f"Error loading participante signals: {str(e)}")
