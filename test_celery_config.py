#!/usr/bin/env python
"""Script para testar configuração do Celery"""
import os
import django

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'liquida2018.settings')
    django.setup()

    from celery import current_app
    from django.conf import settings

    print("=" * 60)
    print("TESTE DE CONFIGURACAO CELERY")
    print("=" * 60)
    print(f"\n1. Settings CELERY_BROKER_URL: {settings.CELERY_BROKER_URL}")
    print(f"2. Celery app broker_url: {current_app.conf.broker_url}")
    print(f"3. Celery app result_backend: {current_app.conf.result_backend}")

    if current_app.conf.broker_url:
        print("\n[OK] Celery está configurado corretamente!")
    else:
        print("\n[ERRO] Celery broker_url está None!")

    print("=" * 60)

if __name__ == "__main__":
    main()
