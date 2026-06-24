default_app_config = "participante.apps.ParticipanteConfig"

# Importar o signal para limpar posto de trabalho ao logout
from .middleware.logout import limpar_posto_ao_logout
