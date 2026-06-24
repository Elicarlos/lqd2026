#!/usr/bin/env python
"""
Script para executar testes do Sistema de Impressão de Cupons

Uso:
    python run_tests.py                    # Executa todos os testes
    python run_tests.py --verbose          # Executa com output detalhado
    python run_tests.py --coverage         # Executa com relatório de cobertura
    python run_tests.py --specific test_name  # Executa teste específico
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'liquida2018.settings')
django.setup()

def run_tests(verbosity=1, coverage=False, specific_test=None):
    """Executa os testes do sistema de impressão"""
    
    print("🧪 EXECUTANDO TESTES DO SISTEMA DE IMPRESSÃO")
    print("=" * 50)
    
    # Configurar TestRunner
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Definir testes a executar
    if specific_test:
        test_labels = [f'bcp.tests.test_print_system.{specific_test}']
    else:
        test_labels = ['bcp.tests.test_print_system']
    
    # Executar testes
    failures = test_runner.run_tests(test_labels, verbosity=verbosity)
    
    # Relatório final
    print("\n" + "=" * 50)
    if failures:
        print("❌ TESTES FALHARAM")
        print(f"Falhas: {failures}")
        return False
    else:
        print("✅ TODOS OS TESTES PASSARAM!")
        return True

def run_with_coverage():
    """Executa testes com relatório de cobertura"""
    try:
        import coverage
    except ImportError:
        print("❌ coverage não instalado. Instale com: pip install coverage")
        return False
    
    print("📊 EXECUTANDO TESTES COM COBERTURA")
    print("=" * 50)
    
    # Iniciar cobertura
    cov = coverage.Coverage()
    cov.start()
    
    # Executar testes
    success = run_tests(verbosity=2)
    
    # Parar cobertura e gerar relatório
    cov.stop()
    cov.save()
    
    print("\n📊 RELATÓRIO DE COBERTURA")
    print("=" * 30)
    cov.report()
    
    # Gerar relatório HTML
    cov.html_report(directory='htmlcov')
    print(f"\n📁 Relatório HTML gerado em: htmlcov/index.html")
    
    return success

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Executar testes do sistema de impressão')
    parser.add_argument('--verbose', '-v', action='store_true', help='Output detalhado')
    parser.add_argument('--coverage', '-c', action='store_true', help='Executar com cobertura')
    parser.add_argument('--specific', '-s', type=str, help='Executar teste específico')
    
    args = parser.parse_args()
    
    # Executar testes
    if args.coverage:
        success = run_with_coverage()
    else:
        verbosity = 2 if args.verbose else 1
        success = run_tests(verbosity=verbosity, specific_test=args.specific)
    
    # Código de saída
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
