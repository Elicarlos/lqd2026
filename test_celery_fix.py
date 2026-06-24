#!/usr/bin/env python
"""Script para testar se o Celery está configurado corretamente"""
import os
import django

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'liquida2018.settings')
    django.setup()

    from celery import current_app
    from liquida2018.celery import app
    from django.conf import settings
    from decouple import config

    print("=" * 60)
    print("TESTE DE CONFIGURACAO CELERY APOS CORRECAO")
    print("=" * 60)

    print(f"\n1. REDIS_URL do .env (decouple): {config('REDIS_URL', 'NAO_ENCONTRADO')}")
    print(f"2. Settings CELERY_BROKER_URL: {settings.CELERY_BROKER_URL}")
    print(f"3. app.broker_url: {app.conf.broker_url}")
    print(f"4. current_app.broker_url: {current_app.conf.broker_url}")
    print(f"5. app.result_backend: {app.conf.result_backend}")

    if app.conf.broker_url and app.conf.broker_url == settings.CELERY_BROKER_URL:
        print("\n[OK] SUCESSO! Celery está configurado corretamente!")
        print("   O broker_url está igual ao CELERY_BROKER_URL do settings.")
    else:
        print("\n[ERRO] PROBLEMA! Celery broker_url ainda está None ou diferente.")
        print(f"   Esperado: {settings.CELERY_BROKER_URL}")
        print(f"   Obtido (app): {app.conf.broker_url}")
        print(f"   Obtido (current_app): {current_app.conf.broker_url}")

    print("=" * 60)

if __name__ == "__main__":
    main()
