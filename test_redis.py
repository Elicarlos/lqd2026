#!/usr/bin/env python
"""Script para testar conexão com Redis"""
import os
import sys
import django

def main():
    # Configurar Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'liquida2018.settings')
    django.setup()

    from decouple import config
    from celery import current_app

    print("=" * 50)
    print("TESTE DE CONFIGURACAO REDIS/CELERY")
    print("=" * 50)

    # Verificar REDIS_URL
    redis_url = config("REDIS_URL", "")
    print(f"\n1. REDIS_URL do .env: {redis_url}")

    # Verificar configuração do Celery
    print(f"\n2. Celery Broker URL: {current_app.conf.broker_url}")
    print(f"3. Celery Result Backend: {current_app.conf.result_backend}")

    # Testar conexão
    try:
        from kombu import Connection
        broker_url = current_app.conf.broker_url
        if broker_url:
            print(f"\n4. Testando conexão com: {broker_url}")
            conn = Connection(broker_url)
            conn.connect()
            print("   [OK] Conexão com Redis OK!")
            conn.close()
        else:
            print("\n4. [ERRO] Broker URL não configurado!")
    except Exception as e:
        print(f"\n4. [ERRO] Erro ao conectar: {e}")

    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
