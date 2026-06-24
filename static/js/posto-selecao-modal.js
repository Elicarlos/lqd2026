// ===== POSTO SELEÇÃO MODAL JAVASCRIPT =====

class PostoSelecaoModal {
    constructor() {
        this.modal = null;
        this.form = null;
        this.submitButton = null;
        this.postoSelect = null;
        this.sessionStartTime = new Date();
        this.jornadaAtiva = false;
        this.init();
    }

    init() {
        // Aguardar DOM estar pronto
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupModal());
        } else {
            this.setupModal();
        }
    }

    setupModal() {
        this.modal = document.getElementById('postoSelecaoModal');
        this.form = document.getElementById('modalWorkstationForm');
        this.submitButton = document.getElementById('modalSubmitButton');
        this.postoSelect = document.getElementById('modal_posto_trabalho');

        if (!this.modal || !this.form) {
            console.warn('Modal de seleção de posto não encontrado');
            return;
        }

        this.setupEventListeners();
        this.updateTime();
        this.checkJornadaStatus();
    }

    setupEventListeners() {
        // Atualizar horário a cada segundo
        setInterval(() => this.updateTime(), 1000);

        // Event listener para mudança no select
        if (this.postoSelect) {
            this.postoSelect.addEventListener('change', (e) => {
                if (e.target.value) {
                    this.submitButton.classList.add('animate__animated', 'animate__pulse');
                    setTimeout(() => {
                        this.submitButton.classList.remove('animate__animated', 'animate__pulse');
                    }, 1000);
                }
            });
        }

        // Event listener para submit do formulário
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        }

        // Event listener para quando o modal é mostrado
        this.modal.addEventListener('shown.bs.modal', () => {
            this.updateJornadaStatus();
            this.postoSelect?.focus();
        });

        // Event listener para quando o modal é escondido
        this.modal.addEventListener('hidden.bs.modal', () => {
            this.resetForm();
        });
    }

    updateTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('pt-BR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });

        // Atualizar horário no modal
        const modalTimeElement = document.getElementById('modalCurrentTime');
        if (modalTimeElement) {
            modalTimeElement.textContent = timeString;
        }

        // Atualizar horário de início da sessão
        const sessionTimeElement = document.getElementById('sessionStartTime');
        if (sessionTimeElement) {
            const sessionTime = this.sessionStartTime.toLocaleTimeString('pt-BR', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
            sessionTimeElement.textContent = sessionTime;
        }
    }

    async checkJornadaStatus() {
        try {
            const response = await fetch('/api/jornada-status/', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.jornadaAtiva = data.jornada_ativa;
                this.updateJornadaStatus();
            } else {
                console.warn('Erro na resposta:', response.status, response.statusText);
            }
        } catch (error) {
            console.warn('Erro ao verificar status da jornada:', error);
        }
    }

    updateJornadaStatus() {
        const statusElement = document.getElementById('jornadaStatus');
        if (!statusElement) return;

        if (this.jornadaAtiva) {
            statusElement.innerHTML = `
                <div class="alert alert-success border-0" role="alert">
                    <div class="d-flex align-items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-check-circle text-success"></i>
                        </div>
                        <div class="flex-grow-1 ms-3">
                            <h6 class="alert-heading fw-bold mb-1">Jornada Ativa</h6>
                            <p class="mb-0 small">Você já possui uma jornada em andamento. Apenas selecione seu posto de trabalho.</p>
                        </div>
                    </div>
                </div>
            `;
        } else {
            statusElement.innerHTML = `
                <div class="alert alert-info border-0" role="alert">
                    <div class="d-flex align-items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-info-circle text-info"></i>
                        </div>
                        <div class="flex-grow-1 ms-3">
                            <h6 class="alert-heading fw-bold mb-1">Nova Jornada</h6>
                            <p class="mb-0 small">Selecione seu posto de trabalho para iniciar uma nova jornada.</p>
                        </div>
                    </div>
                </div>
            `;
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const selectedPosto = this.postoSelect ? this.postoSelect.value : '';
        if (!selectedPosto) {
            this.showToast('modalErrorToast', 'Por favor, selecione um posto de trabalho.');
            return;
        }

        // Desabilitar botão durante o envio
        const originalText = this.submitButton.innerHTML;
        this.submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processando...';
        this.submitButton.disabled = true;

        try {
            const formData = new FormData(this.form);
            
            const response = await fetch(this.form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                if (response.status === 403) {
                    window.location.reload();
                    return;
                }
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            
            if (data.csrf_error) {
                window.location.reload();
                return;
            }
            
            if (data.success) {
                this.showToast('modalSuccessToast', data.message || 'Posto selecionado com sucesso!');
                
                // Fechar modal após 1 segundo
                setTimeout(() => {
                    this.hideModal();
                    // Redirecionar após fechar o modal
                    setTimeout(() => {
                        window.location.href = data.redirect_url;
                    }, 300);
                }, 1000);
            } else {
                this.showToast('modalErrorToast', data.message || 'Erro ao selecionar posto.');
                this.submitButton.innerHTML = originalText;
                this.submitButton.disabled = false;
            }
        } catch (error) {
            console.error('Erro:', error);
            this.showToast('modalErrorToast', 'Erro de conexão. Tente novamente.');
            this.submitButton.innerHTML = originalText;
            this.submitButton.disabled = false;
        }
    }

    showToast(id, message) {
        const toastElement = document.getElementById(id);
        if (toastElement && typeof bootstrap !== 'undefined') {
            // Atualizar mensagem se fornecida
            const toastBody = toastElement.querySelector('.toast-body');
            if (toastBody && message) {
                const icon = toastBody.querySelector('i');
                toastBody.innerHTML = `${icon.outerHTML} ${message}`;
            }
            
            const toast = new bootstrap.Toast(toastElement, {
                autohide: true,
                delay: 3000
            });
            toast.show();
        }
    }

    showModal() {
        if (this.modal && typeof bootstrap !== 'undefined') {
            const modal = new bootstrap.Modal(this.modal);
            modal.show();
        }
    }

    hideModal() {
        if (this.modal && typeof bootstrap !== 'undefined') {
            const modal = bootstrap.Modal.getInstance(this.modal);
            if (modal) {
                modal.hide();
            }
        }
    }

    resetForm() {
        if (this.form) {
            this.form.reset();
        }
        if (this.submitButton) {
            this.submitButton.disabled = false;
        }
    }
}

// Inicializar quando jQuery estiver disponível
function waitForJQuery(callback) {
    if (typeof jQuery !== 'undefined' && typeof jQuery.fn.mask !== 'undefined') {
        callback();
    } else {
        setTimeout(function() {
            waitForJQuery(callback);
        }, 100);
    }
}

// Inicializar modal quando jQuery estiver pronto
waitForJQuery(function() {
    console.log('Inicializando modal de seleção de posto...');
    window.postoSelecaoModal = new PostoSelecaoModal();
});

// Função global para mostrar o modal
window.showPostoSelecaoModal = function() {
    if (window.postoSelecaoModal) {
        window.postoSelecaoModal.showModal();
    }
};
