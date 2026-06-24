#!/usr/bin/env python
"""
Script para configurar automaticamente a finalização de jornadas na produção.
Execute este script uma vez após o deploy.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'liquida2018.settings')
django.setup()

from django.core.management import call_command
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils import timezone

def configurar_finalizacao_automatica():
    """
    DESABILITADO: Configuração automática de finalização de jornadas
    Agora usa apenas o botão manual para superusuários/suporte
    """
    print("Finalização automática de jornadas DESABILITADA")
    print("   - Use o botão manual na página de gestão de jornadas")
    print("   - Disponível para superusuários e grupo Suporte")
    return True

def verificar_jornadas_abertas():
    """Verifica se há jornadas abertas que precisam ser finalizadas"""
    from participante.models import RegistroJornada
    
    jornadas_abertas = RegistroJornada.objects.filter(
        horario_fim__isnull=True,
        status='ATIVA'
    ).count()
    
    print(f"📊 Jornadas abertas encontradas: {jornadas_abertas}")
    
    if jornadas_abertas > 0:
        print("⚠️ Há jornadas abertas! Execute o comando de finalização:")
        print("   python manage.py testar_finalizacao_automatica")
    
    return jornadas_abertas

def main():
    """Função principal"""
    print("🚀 Setup de Produção - Finalização Manual de Jornadas")
    print("=" * 60)
    
    # Configurar finalização automática (DESABILITADA)
    if configurar_finalizacao_automatica():
        print("\n✅ Configuração bem-sucedida!")
    else:
        print("\n❌ Falha na configuração!")
        return
    
    # Verificar jornadas abertas
    print("\n🔍 Verificando jornadas abertas...")
    jornadas_abertas = verificar_jornadas_abertas()
    
    print("\n📝 Próximos passos:")
    print("1. Acesse a página de gestão de jornadas:")
    print("   http://127.0.0.1:8000/lojista/jornadas/")
    print("2. Use o botão 'Executar Finalização Automática'")
    print("3. Disponível para superusuários e grupo Suporte")
    
    if jornadas_abertas > 0:
        print(f"\n⚠️ IMPORTANTE: Há {jornadas_abertas} jornada(s) aberta(s)!")
        print("   Use o botão manual para finalizá-las.")

if __name__ == "__main__":
    main()
