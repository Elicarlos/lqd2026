# Sistema de Impressão de Cupons - Natal de Luz e Prêmios

## 🎯 FUNÇÃO PRINCIPAL (RECOMENDADA)

### `print_barcode_get` - **USE ESTA FUNÇÃO**

**Status**: ✅ **FUNCIONANDO PERFEITAMENTE**

**URL**: `/barcode/print_get/<id>/`

**Método**: GET

**Template**: `bcp/print_pdf.html` (Bridge Page)

---

## 📋 CARACTERÍSTICAS

### ✅ Vantagens
- **UX Otimizada**: Bridge page com iframe para PDF
- **Suporte Completo**: Celery + Síncrono
- **Marca Cupons**: Automaticamente após impressão
- **Debug Logs**: Logs detalhados para troubleshooting
- **Tratamento de Erros**: Robustez completa
- **X-Frame-Options**: Configurado para iframe
- **Auto-refresh**: Página recarrega após impressão

### 🔧 Configuração
- **Celery**: Controlado por `settings.USE_CELERY_FOR_PDF`
- **Síncrono**: Fallback automático se Celery falhar
- **Bridge Page**: Estratégia de impressão robusta

---

## 🚀 FLUXO DE FUNCIONAMENTO

### 1. Chamada da Função
```python
# URL: /barcode/print_get/79/
# Função: print_barcode_get(request, id_)
```

### 2. Verificação de Configuração
```python
if settings.USE_CELERY_FOR_PDF:
    # Usa Celery (assíncrono)
    task = generate_pdf_task.delay(doc.id, auto_print=False)
    pdf_url = reverse("bcp:serve_pdf_from_task", kwargs={"task_id": task.id})
else:
    # Usa síncrono
    pdf_url = reverse("bcp:generate", kwargs={"id_": id_})
```

### 3. Renderização da Bridge Page
```python
context = {
    "pdf_url": pdf_url, 
    "doc": doc
}
response = render(request, "bcp/print_pdf.html", context)
response['X-Frame-Options'] = 'SAMEORIGIN'
return response
```

### 4. Bridge Page (JavaScript)
```javascript
// Verifica se é task Celery
const isTaskUrl = '{{ pdf_url }}'.includes('serve_pdf_from_task');

if (isTaskUrl) {
    // Aguarda task completar
    waitForTaskCompletion(taskId);
} else {
    // Carrega PDF diretamente
    iframe.src = '{{ pdf_url }}';
}
```

### 5. Marcação de Cupons
```python
# Função: confirm_print
# Marca cupons como impressos após confirmação
```

---

## 📝 USO NOS TEMPLATES

### Template Principal
```html
<a href="{% url 'bcp:print_get' id_=doc.id %}" 
   class="btn btn-print-highlight btn-action" 
   target="_blank" 
   onclick="this.style.pointerEvents='none'; this.innerHTML='<i class=\'fas fa-spinner fa-spin\'></i>'; setTimeout(() => {window.location.reload();}, 3000);">
    <i class="fas fa-print me-1"></i>Imprimir
</a>
```

### Parâmetros Importantes
- **`id_=doc.id`**: Parâmetro correto (não `doc.id`)
- **`target="_blank"`**: Abre em nova aba
- **`onclick`**: Feedback visual + reload

---

## 🔗 FUNÇÕES AUXILIARES

### `serve_pdf_from_task`
**URL**: `/barcode/serve_pdf_from_task/<task_id>/`
**Função**: Serve PDF gerado pelo Celery
**Headers**: `X-Frame-Options: SAMEORIGIN`

### `confirm_print`
**URL**: `/barcode/confirm_print/<id>/`
**Função**: Marca cupons como impressos
**Método**: POST

### `check_task_status`
**URL**: `/barcode/check_task_status/<task_id>/`
**Função**: Verifica status da task Celery
**Retorno**: JSON com status e pdf_url

---

## ⚙️ CONFIGURAÇÃO

### Settings
```python
# settings.py
USE_CELERY_FOR_PDF = True  # True = Celery, False = Síncrono
```

### Celery Tasks
```python
# bcp/tasks.py
@shared_task
def generate_pdf_task(doc_id, auto_print=False):
    # Gera PDF e retorna bytes
    return pdf_bytes
```

---

## 🐛 DEBUG E TROUBLESHOOTING

### Logs Disponíveis
```python
print(f"DEBUG: Chamando generate_pdf_task.delay para documento {doc.id}")
print(f"DEBUG: Task criada com ID: {task.id}")
print(f"DEBUG: PDF URL (Celery): {pdf_url}")
print(f"DEBUG: Template ponte renderizado com sucesso")
```

### Verificação de Status
```javascript
// No console do navegador
console.log('É URL de task (Celery):', isTaskUrl);
console.log('Task ID extraído:', taskId);
console.log('Status da task:', data);
```

---

## 📊 COMPARAÇÃO COM OUTRAS FUNÇÕES

| Função | Status | UX | Complexidade | Recomendação |
|--------|--------|----|--------------|--------------|
| `print_barcode_get` | ✅ Funcionando | Excelente | Baixa | **USE ESTA** |
| `print_barcode` | ⚠️ Funcional | Ruim | Alta | Não use |
| `generate` | ✅ Funcional | Média | Média | Auxiliar |

---

## 🎯 IMPLEMENTAÇÃO EM OUTROS LOCAIS

### 1. Adicionar URL
```python
# urls.py
path("print_get/<int:id_>/", views.print_barcode_get, name="print_get"),
```

### 2. Adicionar Botão
```html
<a href="{% url 'bcp:print_get' id_=doc.id %}" 
   class="btn btn-success" 
   target="_blank">
    <i class="fas fa-print"></i> Imprimir
</a>
```

### 3. Verificar Permissões
```python
@login_required
@user_passes_test(lambda u: u.is_staff)
def print_barcode_get(request, id_):
```

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

- [ ] URL configurada com `id_` (não `id`)
- [ ] Template usa `bcp:print_get`
- [ ] Botão tem `target="_blank"`
- [ ] Permissões configuradas
- [ ] Celery configurado (opcional)
- [ ] Debug logs ativos
- [ ] X-Frame-Options configurado

---

## 🚀 RESULTADO ESPERADO

1. **Clique no botão** → Abre bridge page
2. **PDF carrega** → Síncrono ou aguarda Celery
3. **Impressão automática** → Via iframe
4. **Cupons marcados** → Automaticamente
5. **Página recarrega** → Feedback visual

**Status**: ✅ **PRONTO PARA USO EM PRODUÇÃO**
