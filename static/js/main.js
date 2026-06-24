// ===== MAIN JAVASCRIPT FILE =====

// Aguardar jQuery estar disponível
function waitForJQuery(callback) {
    if (typeof jQuery !== 'undefined' && jQuery.fn) {
        callback();
    } else {
        setTimeout(function() {
            waitForJQuery(callback);
        }, 100);
    }
}

// Garantir que $ esteja disponível
if (typeof $ === 'undefined') {
    window.$ = window.jQuery || function() {
        console.warn('jQuery não está disponível, usando fallback');
        return {
            ready: function(callback) {
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', callback);
                } else {
                    callback();
                }
            }
        };
    };
}

waitForJQuery(function() {
    $(document).ready(function() {
        // Inicializar máscaras
        initializeMasks();
        
        // Inicializar toasts
        initializeToasts();
        
        // Inicializar formulário de login
        initializeLoginForm();
        
        // Inicializar navegação mobile
        initializeMobileNav();
    });
});

// ===== MASK INITIALIZATION =====
function initializeMasks() {
    // CPF mask
    $('.cpf-mask').mask('000.000.000-00', {
        reverse: false,
        clearIfNotMatch: true
    });
    
    // Phone mask
    $('.phone-mask').mask('(00) 00000-0000', {
        reverse: false,
        clearIfNotMatch: true
    });
    
    // CEP mask
    $('.cep-mask').mask('00000-000', {
        reverse: false,
        clearIfNotMatch: true
    });
    
    // Money mask
    $('.money-mask').mask('#.##0.##0,00', {
        reverse: true,
        translation: {
            '#': {pattern: /[0-9]/, optional: true}
        }
    });
    
    // Date mask
    $('.date-mask').mask('00/00/0000', {
        reverse: false,
        clearIfNotMatch: true
    });
}

// ===== TOAST INITIALIZATION =====
function initializeToasts() {
    var toastElList = [].slice.call(document.querySelectorAll('.toast'));
    var toastList = toastElList.map(function(toastEl) {
        return new bootstrap.Toast(toastEl, {
            autohide: true,
            delay: 3000
        });
    });
    toastList.forEach(toast => toast.show());
}

// ===== LOGIN FORM HANDLING =====
function initializeLoginForm() {
    // Verificar se jQuery está disponível
    if (typeof $ === 'undefined') {
        console.warn('jQuery não está disponível para inicializar formulário de login');
        return;
    }
    
    $('#loginForm').on('submit', function(e) {
        e.preventDefault();
        
        const username = $('#id_username_login').val();
        const password = $('#id_password_login').val();
        
        // Limpar erros anteriores
        $('.invalid-feedback').addClass('d-none');
        $('.form-control').removeClass('is-invalid');
        
        // Validação básica
        let isValid = true;
        
        if (!username.trim()) {
            $('#id_username_login').addClass('is-invalid');
            $('#username-login-error').text('CPF é obrigatório').removeClass('d-none');
            isValid = false;
        }
        
        if (!password.trim()) {
            $('#id_password_login').addClass('is-invalid');
            $('#password-login-error').text('Senha é obrigatória').removeClass('d-none');
            isValid = false;
        }
        
        if (isValid) {
            // Enviar formulário
            $.ajax({
                url: '/login/',
                method: 'POST',
                data: {
                    username: username,
                    password: password,
                    csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()
                },
                success: function(response) {
                    if (response.success) {
                        // Redirecionar baseado no tipo de usuário
                        if (response.redirect_url) {
                            window.location.href = response.redirect_url;
                        } else {
                            window.location.reload();
                        }
                    } else {
                        // Mostrar erro
                        if (response.error_type === 'username') {
                            $('#id_username_login').addClass('is-invalid');
                            $('#username-login-error').text(response.message).removeClass('d-none');
                        } else if (response.error_type === 'password') {
                            $('#id_password_login').addClass('is-invalid');
                            $('#password-login-error').text(response.message).removeClass('d-none');
                        } else {
                            $('#id_username_login').addClass('is-invalid');
                            $('#username-login-error').text(response.message).removeClass('d-none');
                        }
                    }
                },
                error: function() {
                    $('#id_username_login').addClass('is-invalid');
                    $('#username-login-error').text('Erro ao fazer login. Tente novamente.').removeClass('d-none');
                }
            });
        }
    });

    // Limpar erros quando o modal é fechado
    $('#loginModal').on('hidden.bs.modal', function() {
        $('.invalid-feedback').addClass('d-none');
        $('.form-control').removeClass('is-invalid');
        $('#loginForm')[0].reset();
    });
}

// ===== MOBILE NAVIGATION =====
function initializeMobileNav() {
    const mobileNavToggle = document.querySelector('.navbar-toggler');
    const navMenu = document.querySelector('.navbar-nav');
    
    if (mobileNavToggle && navMenu) {
        mobileNavToggle.addEventListener('click', function() {
            navMenu.classList.toggle('show');
        });
        
        // Fechar menu ao clicar em um link
        const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                navMenu.classList.remove('show');
            });
        });
    }
}

// ===== UTILITY FUNCTIONS =====

// Função para mostrar toast dinâmico
function showToast(message, type = 'info', duration = 3000) {
    const toastContainer = document.createElement('div');
    toastContainer.className = 'position-fixed top-0 end-0 p-3';
    toastContainer.style.zIndex = '1080';

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    const iconMap = {
        'success': 'check-circle',
        'danger': 'times-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body d-flex align-items-center">
                <i class="fas fa-${iconMap[type] || 'info-circle'} me-2 text-center" style="width: 16px;"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);
    document.body.appendChild(toastContainer);

    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: duration
    });

    bsToast.show();

    toast.addEventListener('hidden.bs.toast', () => {
        toastContainer.remove();
    });
}

// Função para formatar CPF
function formatCPF(cpf) {
    return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/g, '$1.$2.$3-$4');
}

// Função para validar CPF
function validateCPF(cpf) {
    cpf = cpf.replace(/[^\d]/g, '');
    
    if (cpf.length !== 11) return false;
    
    // Verifica se todos os dígitos são iguais
    if (/^(\d)\1{10}$/.test(cpf)) return false;
    
    // Validação do primeiro dígito verificador
    let sum = 0;
    for (let i = 0; i < 9; i++) {
        sum += parseInt(cpf.charAt(i)) * (10 - i);
    }
    let remainder = 11 - (sum % 11);
    let digit1 = remainder < 2 ? 0 : remainder;
    
    // Validação do segundo dígito verificador
    sum = 0;
    for (let i = 0; i < 10; i++) {
        sum += parseInt(cpf.charAt(i)) * (11 - i);
    }
    remainder = 11 - (sum % 11);
    let digit2 = remainder < 2 ? 0 : remainder;
    
    return parseInt(cpf.charAt(9)) === digit1 && parseInt(cpf.charAt(10)) === digit2;
}

// Função para formatar moeda
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

// Função para formatar data
function formatDate(date) {
    return new Intl.DateTimeFormat('pt-BR').format(new Date(date));
}

// ===== REGISTRATION FORM FUNCTIONS =====

// Multi-step form functionality
let currentStep = 1;
const totalSteps = 3;

function updateProgress() {
    const progress = (currentStep / totalSteps) * 100;
    const progressBar = document.getElementById('progress-bar');
    const stepCount = document.getElementById('step-count');
    const stepName = document.getElementById('step-name');
    
    if (progressBar) progressBar.style.width = progress + '%';
    if (stepCount) stepCount.textContent = currentStep + ' de ' + totalSteps;
    
    const stepNames = ['', 'Dados de Acesso', 'Dados Pessoais', 'Endereço'];
    if (stepName) stepName.textContent = stepNames[currentStep];
}

function showStep(step) {
    // Hide all steps
    for (let i = 1; i <= totalSteps; i++) {
        const stepElement = document.getElementById('step-' + i);
        if (stepElement) stepElement.classList.add('d-none');
    }
    
    // Show current step
    const currentStepElement = document.getElementById('step-' + step);
    if (currentStepElement) currentStepElement.classList.remove('d-none');
    
    updateProgress();
}

function nextStep() {
    if (validateCurrentStep()) {
        if (currentStep < totalSteps) {
            currentStep++;
            showStep(currentStep);
        }
    }
}

function prevStep() {
    if (currentStep > 1) {
        currentStep--;
        showStep(currentStep);
    }
}

function validateCurrentStep() {
    const currentStepElement = document.getElementById('step-' + currentStep);
    if (!currentStepElement) return true;
    
    const inputs = currentStepElement.querySelectorAll('input[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    // Special validation for step 1 (password confirmation)
    if (currentStep === 1) {
        const passwordInput = document.getElementById('password');
        const confirmPasswordInput = document.getElementById('password_confirm');
        
        if (passwordInput && confirmPasswordInput && passwordInput.value !== confirmPasswordInput.value) {
            confirmPasswordInput.classList.add('is-invalid');
            const confirmError = document.getElementById('password-confirm-error');
            if (confirmError) {
                confirmError.textContent = 'As senhas não coincidem';
                confirmError.classList.remove('d-none');
            }
            isValid = false;
        }
    }
    
    return isValid;
}

// Password strength checker
function initializePasswordStrength() {
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('password_confirm');
    const strengthBar = document.getElementById('passwordStrength');
    const strengthText = document.getElementById('strength-text');
    const confirmError = document.getElementById('password-confirm-error');
    
    if (!passwordInput) return;
    
    passwordInput.addEventListener('input', function() {
        const password = this.value;
        let strength = 0;
        
        if (password.length >= 8) strength++;
        if (/[a-z]/.test(password)) strength++;
        if (/[A-Z]/.test(password)) strength++;
        if (/[0-9]/.test(password)) strength++;
        if (/[^A-Za-z0-9]/.test(password)) strength++;
        
        const percentage = (strength / 5) * 100;
        if (strengthBar) strengthBar.style.width = percentage + '%';
        
        if (strength <= 2) {
            if (strengthBar) strengthBar.className = 'progress-bar bg-danger';
            if (strengthText) strengthText.textContent = 'Fraca';
        } else if (strength <= 3) {
            if (strengthBar) strengthBar.className = 'progress-bar bg-warning';
            if (strengthText) strengthText.textContent = 'Média';
        } else {
            if (strengthBar) strengthBar.className = 'progress-bar bg-success';
            if (strengthText) strengthText.textContent = 'Forte';
        }
        
        // Check password confirmation
        checkPasswordMatch();
    });
    
    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', function() {
            checkPasswordMatch();
        });
    }
    
    function checkPasswordMatch() {
        if (!passwordInput || !confirmPasswordInput) return;
        
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        
        if (confirmPassword && password !== confirmPassword) {
            confirmPasswordInput.classList.add('is-invalid');
            if (confirmError) {
                confirmError.textContent = 'As senhas não coincidem';
                confirmError.classList.remove('d-none');
            }
        } else {
            confirmPasswordInput.classList.remove('is-invalid');
            if (confirmError) confirmError.classList.add('d-none');
        }
    }
}

// CEP Search functionality
function initializeCepSearch() {
    const buscarCepBtn = document.getElementById('buscar-cep-btn');
    if (!buscarCepBtn) return;
    
    buscarCepBtn.addEventListener('click', function() {
        const cepInput = document.getElementById('cep');
        if (!cepInput) return;
        
        const cep = cepInput.value.replace(/\D/g, ''); // Remove non-digits
        
        if (cep.length !== 8) {
            showCepError('CEP deve ter 8 dígitos');
            return;
        }
        
        // Show loading
        buscarCepBtn.classList.add('d-none');
        const cepLoading = document.getElementById('cep-loading');
        if (cepLoading) cepLoading.classList.remove('d-none');
        hideCepError();
        
        // Make AJAX request to search CEP
        $.ajax({
            url: '/consulta-cep/',
            method: 'POST',
            data: {
                cep: cep,
                csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()
            },
            success: function(response) {
                if (response.success) {
                    // Fill address fields with retrieved data
                    fillAddressWithData(response.data);
                    showCepSuccess('Endereço encontrado!');
                } else {
                    showCepError(response.message || 'CEP não encontrado');
                }
            },
            error: function(xhr, status, error) {
                showCepError('Erro ao buscar CEP. Tente novamente.');
            },
            complete: function() {
                // Hide loading
                buscarCepBtn.classList.remove('d-none');
                if (cepLoading) cepLoading.classList.add('d-none');
            }
        });
    });
}

function showCepError(message) {
    // Create error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show mt-2';
    errorDiv.innerHTML = `
        <i class="bi bi-exclamation-triangle me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert after CEP field
    const cepField = document.querySelector('.cep-mask').closest('.form-floating');
    if (cepField) {
        cepField.parentNode.insertBefore(errorDiv, cepField.nextSibling);
    }
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.remove();
        }
    }, 5000);
}

function hideCepError() {
    // Remove any existing error messages
    const existingErrors = document.querySelectorAll('.alert-danger');
    existingErrors.forEach(error => error.remove());
}

function showCepSuccess(message) {
    // Create success message
    const successDiv = document.createElement('div');
    successDiv.className = 'alert alert-success alert-dismissible fade show mt-2';
    successDiv.innerHTML = `
        <i class="bi bi-check-circle me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert after CEP field
    const cepField = document.querySelector('.cep-mask').closest('.form-floating');
    if (cepField) {
        cepField.parentNode.insertBefore(successDiv, cepField.nextSibling);
    }
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (successDiv.parentNode) {
            successDiv.remove();
        }
    }, 3000);
}

function fillAddressWithData(data) {
    // Fill address fields with retrieved data
    const fields = {
        'endereco': data.logradouro,
        'bairro': data.bairro,
        'cidade': data.localidade,
        'estado': data.uf
    };
    
    Object.keys(fields).forEach(fieldName => {
        const input = document.getElementById(fieldName);
        if (input && fields[fieldName] && !input.value) {
            input.value = fields[fieldName];
        }
    });
}

// Initialize registration form
function initializeRegistrationForm() {
    // Initialize password strength
    initializePasswordStrength();
    
    // Initialize CEP search
    initializeCepSearch();
    
    // Initialize progress
    updateProgress();
    
    // Form submission
    const registrationForm = document.getElementById('registrationForm');
    if (registrationForm) {
        registrationForm.addEventListener('submit', function(e) {
            if (!validateCurrentStep()) {
                e.preventDefault();
                return false;
            }
        });
    }
}

// Função para abrir o modal de login
function openLoginModal() {
    const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
    loginModal.show();
}

// Expor funções globalmente
window.showToast = showToast;
window.formatCPF = formatCPF;
window.validateCPF = validateCPF;
window.formatCurrency = formatCurrency;
window.formatDate = formatDate;
window.nextStep = nextStep;
window.prevStep = prevStep;
window.updateProgress = updateProgress;
window.showStep = showStep;
window.validateCurrentStep = validateCurrentStep;
window.initializeRegistrationForm = initializeRegistrationForm;
window.openLoginModal = openLoginModal;
