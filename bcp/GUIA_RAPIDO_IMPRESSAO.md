# 🚀 Guia Rápido - Implementar Impressão de Cupons

## ✅ FUNÇÃO QUE FUNCIONA

**Use sempre**: `print_barcode_get`

**URL**: `/barcode/print_get/<id>/`

**Status**: ✅ **TESTADA E FUNCIONANDO**

---

## 📝 IMPLEMENTAÇÃO RÁPIDA

### 1. Adicionar URL (se não existir)
```python
# urls.py
path("print_get/<int:id_>/", views.print_barcode_get, name="print_get"),
```

### 2. Adicionar Botão no Template
```html
<!-- BOTÃO BÁSICO -->
<a href="{% url 'bcp:print_get' id_=doc.id %}" 
   class="btn btn-success" 
   target="_blank">
    <i class="fas fa-print"></i> Imprimir
</a>

<!-- BOTÃO COMPLETO (com feedback) -->
<a href="{% url 'bcp:print_get' id_=doc.id %}" 
   class="btn btn-print-highlight btn-action" 
   target="_blank" 
   onclick="this.style.pointerEvents='none'; this.innerHTML='<i class=\'fas fa-spinner fa-spin\'></i>'; setTimeout(() => {window.location.reload();}, 3000);">
    <i class="fas fa-print me-1"></i>Imprimir
</a>
```

### 3. Verificar Permissões
```python
# views.py
@login_required
@user_passes_test(lambda u: u.is_staff)
def print_barcode_get(request, id_):
    # ... código da função
```

---

## ⚠️ PONTOS CRÍTICOS

### ✅ FAÇA
- Use `id_=doc.id` (não `doc.id`)
- Use `target="_blank"`
- Use `bcp:print_get`

### ❌ NÃO FAÇA
- Use `doc.id` (erro de parâmetro)
- Use `bcp:print` (função antiga)
- Esqueça `target="_blank"`

---

## 🎯 EXEMPLOS DE USO

### Listagem de Documentos
```html
{% if doc.status == 'validado' %}
    <a href="{% url 'bcp:print_get' id_=doc.id %}" 
       class="btn btn-outline-success btn-action" 
       target="_blank">
        <i class="fas fa-print"></i>
    </a>
{% endif %}
```

### Modal de Detalhes
```html
<a href="{% url 'bcp:print_get' id_=doc.id %}" 
   class="btn btn-print-highlight" 
   target="_blank">
    <i class="fas fa-print me-2"></i>Imprimir Cupons
</a>
```

### Página de Sucesso
```html
<a href="{% url 'bcp:print_get' id_=doc.id %}" 
   class="btn btn-print-highlight btn-action" 
   target="_blank">
    <i class="fas fa-print me-1"></i>Imprimir
</a>
```

---

## 🔧 CONFIGURAÇÃO

### Settings (opcional)
```python
# settings.py
USE_CELERY_FOR_PDF = True  # True = Celery, False = Síncrono
```

### Celery (opcional)
```python
# bcp/tasks.py
@shared_task
def generate_pdf_task(doc_id, auto_print=False):
    # Gera PDF
    return pdf_bytes
```

---

## 🐛 DEBUG

### Logs Disponíveis
```python
print(f"DEBUG: Chamando generate_pdf_task.delay para documento {doc.id}")
print(f"DEBUG: Task criada com ID: {task.id}")
print(f"DEBUG: PDF URL (Celery): {pdf_url}")
print(f"DEBUG: Template ponte renderizado com sucesso")
```

### Console do Navegador
```javascript
console.log('É URL de task (Celery):', isTaskUrl);
console.log('Task ID extraído:', taskId);
console.log('Status da task:', data);
```

---

## ✅ CHECKLIST FINAL

- [ ] URL configurada: `print_get/<int:id_>/`
- [ ] Template usa: `{% url 'bcp:print_get' id_=doc.id %}`
- [ ] Botão tem: `target="_blank"`
- [ ] Permissões: `@login_required` + `@user_passes_test`
- [ ] Testado: Clique → Bridge page → PDF → Impressão

---

## 🚀 RESULTADO

1. **Clique** → Abre bridge page
2. **PDF carrega** → Síncrono ou Celery
3. **Impressão automática** → Via iframe
4. **Cupons marcados** → Automaticamente
5. **Feedback visual** → Spinner + reload

**Status**: ✅ **PRONTO PARA USO**
