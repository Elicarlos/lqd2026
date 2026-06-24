#!/usr/bin/env python
"""Script para debugar configuração do Celery"""
import os
import django

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'liquida2018.settings')
    django.setup()

    from celery import current_app
    from django.conf import settings
    from decouple import config

    print("=" * 60)
    print("DEBUG CELERY CONFIGURATION")
    print("=" * 60)

    print(f"\n1. REDIS_URL do .env: {config('REDIS_URL', 'NAO_ENCONTRADO')}")
    print(f"2. Settings CELERY_BROKER_URL: {settings.CELERY_BROKER_URL}")

    # Verifica o que o config_from_object configurou
    print(f"\n3. Celery app broker_url (antes): {current_app.conf.broker_url}")

    # Tenta configurar manualmente
    redis_url = config('REDIS_URL', '')
    if redis_url:
        current_app.conf.broker_url = redis_url
        current_app.conf.result_backend = redis_url
        print(f"4. Configurando manualmente: {redis_url}")
        print(f"5. Celery app broker_url (depois): {current_app.conf.broker_url}")

    # Verifica todas as configurações relacionadas ao broker
    print(f"\n6. Todas as configs do broker:")
    for key in dir(current_app.conf):
        if 'broker' in key.lower() or 'redis' in key.lower():
            try:
                value = getattr(current_app.conf, key)
                if not callable(value):
                    print(f"   {key}: {value}")
            except:
                pass

    print("=" * 60)

if __name__ == "__main__":
    main()
