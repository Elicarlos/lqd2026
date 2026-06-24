# Sistema de Avisos Elegantes

## Visão Geral

O sistema de avisos elegantes foi criado para substituir redirecionamentos com parâmetros GET por uma abordagem mais elegante e profissional. Em vez de usar URLs como `/erro?msg=Erro%20de%20login`, agora você pode usar uma página dedicada de aviso que oferece uma melhor experiência do usuário.

## Benefícios

1. **URLs mais limpas**: Não há mais parâmetros GET longos e feios
2. **Melhor UX**: Interface consistente e profissional para todos os avisos
3. **Navegação fluida**: Usuário pode navegar para outras páginas sem perder o contexto
4. **Flexibilidade**: Suporte a diferentes tipos de mensagens (erro, warning, info)
5. **Ações personalizáveis**: Botões de ação configuráveis para cada situação

## Como Usar

### 1. Função Auxiliar (Recomendado)

Use a função `redirecionar_aviso()` para criar avisos elegantes:

```python
from participante.views import redirecionar_aviso

def minha_view(request):
    try:
        # Alguma operação que pode falhar
        operacao_risco()
    except Exception as e:
        return redirecionar_aviso(
            request,
            titulo="Erro na Operação",
            mensagem="Não foi possível completar a operação solicitada.",
            tipo="error",
            acao_primaria="Tentar Novamente",
            acao_primaria_url="/minha-pagina/",
            acao_primaria_icone="refresh",
            detalhes=f"Detalhes técnicos: {str(e)}"
        )
```

### 2. Parâmetros Disponíveis

| Parâmetro | Tipo | Descrição | Exemplo |
|-----------|------|-----------|---------|
| `titulo` | string | Título da página de aviso | "Erro de Login" |
| `mensagem` | string | Mensagem principal | "Credenciais inválidas" |
| `tipo` | string | Tipo de aviso (error/warning/info) | "error" |
| `detalhes` | string | Informações adicionais | "Tente novamente em 5 minutos" |
| `acao_primaria` | string | Texto do botão principal | "Tentar Novamente" |
| `acao_primaria_url` | string | URL do botão principal | "/login/" |
| `acao_primaria_icone` | string | Ícone do botão principal | "refresh" |
| `acao_secundaria` | string | Texto do botão secundário | "Voltar" |
| `acao_secundaria_url` | string | URL do botão secundário | "/" |
| `acao_secundaria_icone` | string | Ícone do botão secundário | "arrow-left" |
| `mostrar_voltar` | boolean | Mostrar botão "Voltar" | True |

### 3. Tipos de Aviso

- **error**: Ícone vermelho, para erros críticos
- **warning**: Ícone amarelo, para avisos importantes
- **info**: Ícone azul, para informações gerais

### 4. Exemplos Práticos

#### Erro de Login
```python
return redirecionar_aviso(
    request,
    titulo="Erro de Login",
    mensagem="CPF ou senha incorretos. Verifique suas credenciais.",
    tipo="error",
    acao_primaria="Tentar Novamente",
    acao_primaria_url="/login/",
    acao_primaria_icone="sign-in-alt"
)
```

#### Aviso de Manutenção
```python
return redirecionar_aviso(
    request,
    titulo="Sistema em Manutenção",
    mensagem="O sistema está passando por manutenção programada.",
    tipo="warning",
    acao_primaria="Tentar Novamente",
    acao_primaria_url="/",
    acao_primaria_icone="refresh",
    detalhes="Manutenção programada das 02:00 às 04:00"
)
```

#### Sucesso com Ações
```python
return redirecionar_aviso(
    request,
    titulo="Operação Concluída",
    mensagem="Seu cadastro foi realizado com sucesso!",
    tipo="info",
    acao_primaria="Ir para Dashboard",
    acao_primaria_url="/dashboard/",
    acao_primaria_icone="check",
    acao_secundaria="Ver Perfil",
    acao_secundaria_url="/perfil/",
    acao_secundaria_icone="user"
)
```

## Migração de Código Existente

### Antes (Redirecionamento com GET)
```python
messages.error(request, "Erro de segurança. Recarregue a página.")
return redirect('/?error=security')
```

### Depois (Aviso Elegante)
```python
return redirecionar_aviso(
    request,
    titulo="Erro de Segurança",
    mensagem="Erro de segurança. Por favor, recarregue a página e tente novamente.",
    tipo="error",
    acao_primaria="Tentar Novamente",
    acao_primaria_url="/",
    acao_primaria_icone="refresh"
)
```

## URLs de Exemplo

Para testar a funcionalidade, você pode acessar:

- `/exemplo-aviso/?tipo=erro_validacao` - Erro de validação
- `/exemplo-aviso/?tipo=manutencao` - Aviso de manutenção
- `/exemplo-aviso/?tipo=sucesso` - Mensagem de sucesso
- `/exemplo-aviso/?tipo=acesso_negado` - Acesso negado

## Implementação Técnica

### View Principal
- **Arquivo**: `participante/views.py`
- **Função**: `exibir_aviso(request)`
- **URL**: `/aviso/`

### Template
- **Arquivo**: `participante/templates/participante/aviso.html`
- **Base**: `base-bootstrap.html`
- **Responsivo**: Sim

### Armazenamento de Dados
Os dados são armazenados temporariamente na sessão do usuário para evitar URLs muito longas. Os dados são limpos automaticamente após o uso.

## Considerações de Segurança

1. **Validação de entrada**: Todos os parâmetros são validados
2. **Limpeza de sessão**: Dados temporários são removidos após uso
3. **CSRF**: Compatível com proteção CSRF do Django
4. **XSS**: Template escapa automaticamente conteúdo HTML

## Compatibilidade

- ✅ Django 3.2+
- ✅ Bootstrap 4+
- ✅ FontAwesome 5+
- ✅ Navegadores modernos
- ✅ Dispositivos móveis
