# 📄 Função para Adicionar Documentos Fiscais

Esta função permite adicionar documentos fiscais automaticamente ao CPF **017.614.323-89** no lojista **92.753.095/0001-32**.

## 🚀 Como Usar

### Opção 1: Comando Django (Recomendado)

```bash
# Criar 5 documentos (padrão)
python manage.py add_documents_to_cpf

# Criar 10 documentos
python manage.py add_documents_to_cpf --quantidade 10

# Criar documentos com valores específicos
python manage.py add_documents_to_cpf --quantidade 3 --valor-min 100 --valor-max 300

# Criar documentos em período específico
python manage.py add_documents_to_cpf --quantidade 5 --data-inicio 2024-06-28 --data-fim 2024-07-07
```

### Opção 2: Shell do Django

```python
# Abrir shell do Django
python manage.py shell

# Importar e usar a função
from utils.add_documents import add_documents_to_cpf, list_user_documents

# Criar 5 documentos
add_documents_to_cpf(quantidade=5, valor_min=50, valor_max=200)

# Listar documentos do usuário
list_user_documents('01761432389')
```

### Opção 3: Executar Diretamente

```bash
# Executar o arquivo Python diretamente
python utils/add_documents.py
```

## 📋 Parâmetros

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `quantidade` | int | 5 | Quantidade de documentos a criar |
| `valor_min` | float | 50.0 | Valor mínimo dos documentos |
| `valor_max` | float | 200.0 | Valor máximo dos documentos |
| `data_inicio` | str | '2024-06-28' | Data de início (YYYY-MM-DD) |
| `data_fim` | str | '2024-07-07' | Data de fim (YYYY-MM-DD) |

## 🎯 Características dos Documentos Criados

- **CPF Fixo:** 017.614.323-89
- **CNPJ Fixo:** 92.753.095/0001-32
- **Status:** Pendente
- **Valores:** Aleatórios entre valor_min e valor_max
- **Datas:** Aleatórias dentro do período especificado
- **Números:** Únicos (formato: DOC0010011234)
- **Vendedores:** Sequenciais (Vendedor 1, Vendedor 2, etc.)
- **Cartões:** Aleatórios (REDE, MASTERCARD, Cielo)

## 🎫 Criação de Cupons

**1 cupom por documento** - independente do valor ou tipo de pagamento.

Cada documento fiscal criado gerará automaticamente 1 cupom para impressão com as seguintes características:
- **Status:** Não impresso (`impresso=False`)
- **Em impressão:** Não (`em_impressao=False`)
- **Operador:** Usuário que criou o documento
- **Pronto para impressão:** Sim

## 📊 Exemplo de Saída

```
🚀 Iniciando criação de 5 documentos...
✅ Usuário encontrado: 01761432389
✅ Lojista encontrado: LOJA EXEMPLO (92753095000132)
✅ Campanha ativa: Natal de Luz 2024
✅ Documento 1/5 criado: R$ 125.50 - DOC0010011234 - 30/06/2024
✅ Documento 2/5 criado: R$ 89.75 - DOC0010025678 - 02/07/2024
✅ Documento 3/5 criado: R$ 156.25 - DOC0010039012 - 05/07/2024
✅ Documento 4/5 criado: R$ 67.30 - DOC0010043456 - 01/07/2024
✅ Documento 5/5 criado: R$ 198.90 - DOC0010057890 - 06/07/2024

============================================================
📊 RESUMO DA CRIAÇÃO:
👤 Usuário: 01761432389
🏪 Lojista: LOJA EXEMPLO
📄 Documentos criados: 5
💰 Valor total: R$ 637.70
📅 Período: 28/06/2024 a 07/07/2024
============================================================
🎫 Cupom 26 criado para documento 15
🎫 Cupom 27 criado para documento 16
🎫 Cupom 28 criado para documento 17
🎫 Cupom 29 criado para documento 18
🎫 Cupom 30 criado para documento 19
🎫 Total de cupons criados: 5 (1 por documento)

🎉 Sucesso! 5 documentos e 5 cupons criados para o CPF 01761432389
```

## 🔍 Verificar Documentos Criados

```python
# No shell do Django
from utils.add_documents import list_user_documents

# Listar todos os documentos do usuário
list_user_documents('01761432389')
```

## ⚠️ Observações

1. **Validação:** Os documentos respeitam as regras de validação do modelo
2. **Unicidade:** Números de documento são únicos por lojista
3. **Campanha:** Verifica se há campanha ativa antes de criar
4. **Usuário/Lojista:** Verifica se existem antes de criar documentos
5. **Logs:** Exibe logs detalhados do processo

## 🛠️ Arquivos Criados

- `participante/management/commands/add_documents_to_cpf.py` - Comando Django
- `utils/add_documents.py` - Função Python
- `utils/README_add_documents.md` - Esta documentação
