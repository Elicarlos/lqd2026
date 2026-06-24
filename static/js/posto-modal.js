// Posto Modal Controller - Versão Corrigida
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔍 POSTO MODAL: Script carregado');
    
    const postoModal = document.getElementById('postoModal');
    if (!postoModal) {
        console.log('❌ POSTO MODAL: Modal não encontrado no DOM');
        return;
    }
    
    console.log('✅ POSTO MODAL: Modal encontrado');
    
    const modal = new bootstrap.Modal(postoModal);
    const postoSelect = document.getElementById('posto_trabalho');
    const confirmarBtn = document.getElementById('confirmarPosto');
    const form = document.getElementById('postoModalForm');
    
    // Verificar se todos os elementos necessários existem
    if (!postoSelect || !confirmarBtn || !form) {
        console.error('❌ POSTO MODAL: Elementos necessários não encontrados:', {
            postoSelect: !!postoSelect,
            confirmarBtn: !!confirmarBtn,
            form: !!form
        });
        return;
    }
    
    console.log('🔍 POSTO MODAL: Data attributes:', {
        isStaff: document.body.dataset.isStaff,
        hasOperationalGroup: document.body.dataset.hasOperationalGroup
    });
    
    // Função para obter o CSRF token
    function getCsrfToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        
        if (!cookieValue) {
            // Tentar obter do meta tag
            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            if (csrfMeta) {
                return csrfMeta.getAttribute('content');
            }
            
            // Tentar obter do input hidden
            const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
            if (csrfInput) {
                return csrfInput.value;
            }
        }
        
        return cookieValue;
    }
    
    // Verificar se precisa mostrar o modal
    function checkPostoNecessario() {
        const isStaff = document.body.dataset.isStaff === 'true';
        const hasOperationalGroup = document.body.dataset.hasOperationalGroup === 'true';
        const hasPosto = postoSelect.value && postoSelect.value.trim() !== '';
        
        console.log('🔍 POSTO MODAL: Verificações:', {
            isStaff,
            hasOperationalGroup,
            hasPosto,
            postoSelectValue: postoSelect.value
        });
        
        // Mostrar modal para staff com grupo operacional SEM posto
        if (isStaff && hasOperationalGroup && !hasPosto) {
            console.log('POSTO MODAL: Mostrando modal (sem posto)');
            modal.show();
        } else if (isStaff && hasOperationalGroup && hasPosto) {
            console.log('POSTO MODAL: Modal não será mostrado (já tem posto)');
        } else {
            console.log('POSTO MODAL: Modal não será mostrado (não é staff ou não tem grupo operacional)');
        }
    }
    
    // Mostrar modal se necessário
    checkPostoNecessario();
    
    // Modal não pode ser fechado, então não precisamos re-mostrar
    
    // Confirmar seleção
    confirmarBtn.addEventListener('click', function() {
        // Validar seleção
        if (!postoSelect.value || postoSelect.value.trim() === '') {
            alert('Por favor, selecione um posto de trabalho.');
            postoSelect.focus();
            return;
        }
        
        // Desabilitar botão durante a requisição
        confirmarBtn.disabled = true;
        confirmarBtn.textContent = 'Salvando...';
        
        const formData = new FormData(form);
        
        // Log FormData para debug
        console.log('🔍 POSTO MODAL: FormData contents:');
        for (let [key, value] of formData.entries()) {
            console.log(`  ${key}: ${value}`);
        }
        
        // Obter CSRF token
        const csrfToken = getCsrfToken();
        if (!csrfToken) {
            console.error('❌ POSTO MODAL: CSRF token não encontrado');
            alert('Erro de segurança. Recarregue a página e tente novamente.');
            resetButton();
            return;
        }
        
        console.log('🔍 POSTO MODAL: Enviando requisição AJAX...');
        
        fetch('/participante/selecionar-posto/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => {
            console.log('🔍 POSTO MODAL: Response status:', response.status);
            
            // Verificar se a resposta é ok
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Verificar content-type
            const contentType = response.headers.get('content-type');
            console.log('🔍 POSTO MODAL: Content-Type:', contentType);
            
            if (!contentType || !contentType.includes('application/json')) {
                // Se não é JSON, pegar o texto para ver o que estamos recebendo
                return response.text().then(text => {
                    console.error('❌ POSTO MODAL: Response não é JSON:', text.substring(0, 500));
                    throw new Error('Resposta inválida do servidor');
                });
            }
            
            return response.json();
        })
        .then(data => {
            console.log('🔍 POSTO MODAL: Response data:', data);
            
            if (data.success) {
                console.log('✅ POSTO MODAL: Posto salvo com sucesso');
                console.log('🔍 POSTO MODAL: Escondendo modal e recarregando página...');
                modal.hide();
                
                // Aguardar o modal fechar antes de recarregar
                setTimeout(() => {
                    console.log('🔍 POSTO MODAL: Recarregando página...');
                    window.location.reload();
                }, 300);
            } else {
                const errorMessage = data.error || data.message || 'Erro ao salvar posto de trabalho.';
                console.error('❌ POSTO MODAL: Erro do servidor:', errorMessage);
                alert(errorMessage);
                resetButton();
            }
        })
        .catch(error => {
            console.error('❌ POSTO MODAL: Erro na requisição:', error);
            alert('Erro ao comunicar com o servidor. Tente novamente.');
            resetButton();
        });
        
        // Função para resetar o botão
        function resetButton() {
            confirmarBtn.disabled = false;
            confirmarBtn.textContent = 'Confirmar';
        }
    });
});