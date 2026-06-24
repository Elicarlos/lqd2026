# 🧪 Testes do Sistema de Impressão de Cupons

## 📋 Visão Geral

Este diretório contém testes abrangentes para o sistema de impressão de cupons, cobrindo:

- ✅ **Função principal**: `print_barcode_get`
- ✅ **Funções auxiliares**: `confirm_print`, `serve_pdf_from_task`
- ✅ **Integração Celery**: Tasks e status
- ✅ **Tratamento de erros**: Cenários de falha
- ✅ **Fluxos completos**: End-to-end testing

## 🚀 Como Executar

### 1. Usando Django Test Runner
```bash
# Executar todos os testes
python manage.py test bcp.tests.test_print_system

# Executar com output detalhado
python manage.py test bcp.tests.test_print_system --verbosity=2

# Executar teste específico
python manage.py test bcp.tests.test_print_system.PrintSystemTestCase.test_print_barcode_get_success_sync
```

### 2. Usando Script Personalizado
```bash
# Executar todos os testes
python bcp/run_tests.py

# Executar com output detalhado
python bcp/run_tests.py --verbose

# Executar com relatório de cobertura
python bcp/run_tests.py --coverage

# Executar teste específico
python bcp/run_tests.py --specific test_print_barcode_get_success_sync
```

### 3. Usando Coverage (opcional)
```bash
# Instalar coverage
pip install coverage

# Executar com cobertura
coverage run --source='.' manage.py test bcp.tests.test_print_system
coverage report
coverage html
```

## 📊 Cobertura de Testes

### Testes Unitários (`PrintSystemTestCase`)

| Função | Testes | Status |
|--------|--------|--------|
| `print_barcode_get` | 6 testes | ✅ Completo |
| `confirm_print` | 2 testes | ✅ Completo |
| `serve_pdf_from_task` | 3 testes | ✅ Completo |
| `check_task_status` | 2 testes | ✅ Completo |
| `generate_pdf_sync` | 1 teste | ✅ Completo |

### Testes de Integração (`PrintSystemIntegrationTestCase`)

| Cenário | Testes | Status |
|---------|--------|--------|
| Fluxo síncrono completo | 1 teste | ✅ Completo |
| Fluxo Celery completo | 1 teste | ✅ Completo |
| Recuperação de erros | 1 teste | ✅ Completo |

## 🎯 Cenários Testados

### ✅ Acesso e Permissões
- [x] Usuário não autenticado → Redirecionamento
- [x] Usuário não-staff → Acesso negado
- [x] Documento inexistente → 404
- [x] Usuário staff → Acesso permitido

### ✅ Impressão Síncrona
- [x] Configuração `USE_CELERY_FOR_PDF=False`
- [x] Template correto renderizado
- [x] Headers X-Frame-Options configurados
- [x] Contexto com pdf_url e doc

### ✅ Impressão com Celery
- [x] Configuração `USE_CELERY_FOR_PDF=True`
- [x] Task criada com ID correto
- [x] URL contém task_id
- [x] Integração com AsyncResult

### ✅ Confirmação de Impressão
- [x] Cupons marcados como impressos
- [x] Status em_impressao atualizado
- [x] Resposta JSON correta
- [x] Tratamento de cupons inexistentes

### ✅ Servir PDF de Task
- [x] PDF válido servido corretamente
- [x] Headers Content-Type e X-Frame-Options
- [x] Redirecionamento para task pendente
- [x] Tratamento de PDF inválido

### ✅ Verificação de Status
- [x] Status SUCCESS retornado
- [x] Status PENDING retornado
- [x] URL do PDF incluída na resposta

### ✅ Cenários de Erro
- [x] Documento não encontrado
- [x] Cupons não em impressão
- [x] Task falhou
- [x] PDF inválido

### ✅ Múltiplos Cupons
- [x] Impressão com vários cupons
- [x] Contagem correta de cupons impressos
- [x] Status atualizado para todos

## 🔧 Configuração dos Testes

### Setup Automático
Os testes criam automaticamente:
- ✅ Usuário staff para testes
- ✅ Perfil do usuário
- ✅ Lojista válido
- ✅ Documento fiscal validado
- ✅ Cupons para impressão

### Mocks Utilizados
- ✅ `settings.USE_CELERY_FOR_PDF`
- ✅ `generate_pdf_task.delay`
- ✅ `AsyncResult` (Celery)
- ✅ `generate_pdf_sync`

### Dados de Teste
```python
# Usuário
username: 'testuser'
password: 'testpass123'
is_staff: True

# Documento
numeroDocumento: '123456789'
valorDocumento: 100.00
status: 'validado'

# Cupons
quantidade: 3
impresso: False
em_impressao: False
```

## 📈 Métricas de Qualidade

### Cobertura Esperada
- **Linhas de código**: >90%
- **Funções**: 100%
- **Branches**: >85%

### Performance
- **Tempo de execução**: <30 segundos
- **Memória**: <100MB
- **Testes isolados**: Sim

### Confiabilidade
- **Testes determinísticos**: Sim
- **Sem dependências externas**: Sim
- **Rollback automático**: Sim

## 🐛 Debugging

### Logs de Teste
```python
# Ativar logs detalhados
python manage.py test bcp.tests.test_print_system --verbosity=3
```

### Teste Específico
```python
# Executar apenas um teste
python manage.py test bcp.tests.test_print_system.PrintSystemTestCase.test_print_barcode_get_success_sync --verbosity=2
```

### Verificar Estado
```python
# Verificar cupons após teste
Cupom.objects.filter(documentoFiscal=documento).values('impresso', 'em_impressao')
```

## 🔄 Integração Contínua

### GitHub Actions (exemplo)
```yaml
- name: Run Print System Tests
  run: |
    python manage.py test bcp.tests.test_print_system --verbosity=2
```

### Pre-commit Hook
```bash
# Adicionar ao .pre-commit-config.yaml
- repo: local
  hooks:
    - id: print-system-tests
      name: Print System Tests
      entry: python manage.py test bcp.tests.test_print_system
      language: system
      pass_filenames: false
```

## 📝 Manutenção

### Adicionar Novo Teste
1. Criar método `test_nome_do_teste` na classe apropriada
2. Usar `setUp()` para dados necessários
3. Usar mocks quando necessário
4. Verificar assertions específicas
5. Documentar o cenário testado

### Atualizar Testes Existentes
1. Verificar se mudanças quebram testes
2. Atualizar mocks se necessário
3. Adicionar novos cenários
4. Manter documentação atualizada

## ✅ Checklist de Qualidade

- [x] Todos os cenários principais testados
- [x] Mocks configurados corretamente
- [x] Assertions específicas e claras
- [x] Setup e teardown adequados
- [x] Documentação completa
- [x] Scripts de execução funcionando
- [x] Cobertura de código adequada
- [x] Testes isolados e determinísticos

## 🚀 Status Final

**✅ SISTEMA DE TESTES COMPLETO E FUNCIONAL**

- **Cobertura**: Abrangente
- **Qualidade**: Alta
- **Manutenibilidade**: Excelente
- **Documentação**: Completa
- **Automação**: Pronta para CI/CD
