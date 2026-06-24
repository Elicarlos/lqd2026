from __future__ import absolute_import, unicode_literals

import os

from celery import Celery

# Define the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "liquida2018.settings")

# Garante que o Django está configurado antes de carregar as configurações
import django
django.setup()

app = Celery("liquida2018")

# Load task modules from all registered Django app configs.
# Todas as configurações CELERY_* estão no settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

# Garante que o transporte seja Redis explicitamente
# Isso é necessário porque o Celery pode tentar inferir o transporte da URL
from django.conf import settings as django_settings
if hasattr(django_settings, 'CELERY_BROKER_URL') and django_settings.CELERY_BROKER_URL:
    app.conf.broker_transport = 'redis'
    app.conf.broker_url = django_settings.CELERY_BROKER_URL
    app.conf.result_backend = django_settings.CELERY_RESULT_BACKEND

# Garante que o current_app aponte para este app
# Isso é necessário para que @shared_task use a configuração correta
from celery import _state
_state.set_default_app(app)

# Autodiscover tasks in tasks.py
app.autodiscover_tasks()