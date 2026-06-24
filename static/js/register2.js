// Registration Form JavaScript
let currentStep = 1;
const totalSteps = 3;

// Initialize registration form functionality
function initializeRegistrationForm() {
    // Initialize masks
    initializeMasks();
    
    // Initialize password strength checker
    initializePasswordStrength();
    
    // Initialize CEP search
    initializeCEPSearch();
    
    // Initialize form validation
    initializeFormValidation();
}

// Initialize input masks
function initializeMasks() {
    // CPF mask
    $('.cpf-mask').mask('000.000.000-00', {
        placeholder: '000.000.000-00'
    });
    
    // CEP mask
    $('.cep-mask').mask('00000-000', {
        placeholder: '00000-000'
    });
    
    // Phone mask
    var SPMaskBehavior = function (val) {
        return val.replace(/\D/g, '').length === 11 ? '(00) 00000-0000' : '(00) 0000-00009';
    };
    var spOptions = {
        onKeyPress: function(val, e, field, options) {
            field.mask(SPMaskBehavior.apply({}, arguments), options);
        }
    };
    $('.phone-mask').mask(SPMaskBehavior, spOptions);
}

// Initialize password strength checker
function initializePasswordStrength() {
    $('#password').on('input', function() {
        const password = $(this).val();
        const strength = calculatePasswordStrength(password);
        updatePasswordStrengthIndicator(strength);
    });
    
    // Password confirmation check
    $('#password_confirm').on('input', function() {
        const password = $('#password').val();
        const confirmPassword = $(this).val();
        
        if (confirmPassword && password !== confirmPassword) {
            $(this).addClass('is-invalid');
            $('#password-confirm-error').removeClass('d-none').text('As senhas não coincidem');
        } else {
            $(this).removeClass('is-invalid');
            $('#password-confirm-error').addClass('d-none');
        }
    });
}

// Calculate password strength
function calculatePasswordStrength(password) {
    let score = 0;
    
    if (password.length >= 8) score += 1;
    if (password.match(/[a-z]/)) score += 1;
    if (password.match(/[A-Z]/)) score += 1;
    if (password.match(/[0-9]/)) score += 1;
    if (password.match(/[^a-zA-Z0-9]/)) score += 1;
    
    return score;
}

// Update password strength indicator
function updatePasswordStrengthIndicator(strength) {
    const progressBar = $('#passwordStrength');
    const strengthText = $('#strength-text');
    
    let width, color, text;
    
    switch(strength) {
        case 0:
        case 1:
            width = '20%';
            color = '#dc3545';
            text = 'Muito Fraca';
            break;
        case 2:
            width = '40%';
            color = '#fd7e14';
            text = 'Fraca';
            break;
        case 3:
            width = '60%';
            color = '#ffc107';
            text = 'Média';
            break;
        case 4:
            width = '80%';
            color = '#20c997';
            text = 'Forte';
            break;
        case 5:
            width = '100%';
            color = '#198754';
            text = 'Muito Forte';
            break;
        default:
            width = '0%';
            color = '#6c757d';
            text = 'Fraca';
    }
    
    progressBar.css({
        'width': width,
        'background-color': color
    });
    strengthText.text(text);
}

// Initialize CEP search
function initializeCEPSearch() {
    $('#buscar-cep-btn').on('click', function() {
        const cep = $('#CEP_step3').val().replace(/\D/g, '');
        
        if (cep.length !== 8) {
            alert('Por favor, insira um CEP válido');
            return;
        }
        
        // Show loading
        $('#cep-loading').addClass('show');
        $(this).prop('disabled', true);
        
        // Get CSRF token from cookie
        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
        
        // Fetch CEP data via backend Django (usa brazilcep com múltiplos provedores)
        const formData = new FormData();
        formData.append('cep', cep);
        
        fetch('/participante/consulta-cep/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
            .then(response => response.json())
            .then(result => {
                if (!result.success) {
                    alert(result.message || 'CEP não encontrado');
                } else {
                    // Fill address fields
                    $('#endereco_step3').val(result.data.logradouro);
                    $('#bairro_step3').val(result.data.bairro);
                    $('#cidade_step3').val(result.data.localidade);
                    $('#estado_step3').val(result.data.uf);
                }
            })
            .catch(error => {
                console.error('Erro ao buscar CEP:', error);
                alert('Erro ao buscar CEP. Tente novamente.');
            })
            .finally(() => {
                // Hide loading
                $('#cep-loading').removeClass('show');
                $('#buscar-cep-btn').prop('disabled', false);
	});
});

    // Auto-search on CEP input
    $('#CEP_step3').on('blur', function() {
        const cep = $(this).val().replace(/\D/g, '');
        if (cep.length === 8) {
            $('#buscar-cep-btn').click();
        }
    });
}

// Initialize form validation
function initializeFormValidation() {
    // Real-time validation
    $('input[required]').on('blur', function() {
        validateField($(this));
    });
    
    // Form submission
    $('#registrationForm').on('submit', function(e) {
        if (!validateCurrentStep()) {
            e.preventDefault();
            return false;
        }
    });
}

// Validate individual field
function validateField(field) {
    const value = field.val().trim();
    const isRequired = field.prop('required');
    
    if (isRequired && !value) {
        field.addClass('is-invalid');
        return false;
    }
    
    // Email validation
    if (field.attr('type') === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            field.addClass('is-invalid');
            return false;
        }
    }
    
    // CPF validation
    if (field.hasClass('cpf-mask') && value) {
        const cpf = value.replace(/\D/g, '');
        if (!isValidCPF(cpf)) {
            field.addClass('is-invalid');
            return false;
        }
    }
    
    field.removeClass('is-invalid');
    return true;
}

// Validate CPF
function isValidCPF(cpf) {
    if (cpf.length !== 11) return false;
    
    // Check for known invalid CPFs
    if (cpf === '00000000000' || cpf === '11111111111' || 
        cpf === '22222222222' || cpf === '33333333333' || 
        cpf === '44444444444' || cpf === '55555555555' || 
        cpf === '66666666666' || cpf === '77777777777' || 
        cpf === '88888888888' || cpf === '99999999999') {
        return false;
    }
    
    // Validate first digit
    let sum = 0;
    for (let i = 0; i < 9; i++) {
        sum += parseInt(cpf.charAt(i)) * (10 - i);
    }
    let remainder = 11 - (sum % 11);
    let digit1 = remainder < 2 ? 0 : remainder;
    
    // Validate second digit
    sum = 0;
    for (let i = 0; i < 10; i++) {
        sum += parseInt(cpf.charAt(i)) * (11 - i);
    }
    remainder = 11 - (sum % 11);
    let digit2 = remainder < 2 ? 0 : remainder;
    
    return parseInt(cpf.charAt(9)) === digit1 && parseInt(cpf.charAt(10)) === digit2;
}

// Validate current step
function validateCurrentStep() {
    const currentStepElement = $(`#step-${currentStep}`);
    const requiredFields = currentStepElement.find('input[required]');
    let isValid = true;
    
    requiredFields.each(function() {
        if (!validateField($(this))) {
            isValid = false;
        }
    });
    
    // Special validation for step 1
    if (currentStep === 1) {
        const password = $('#password').val();
        const confirmPassword = $('#password_confirm').val();
        
        if (password !== confirmPassword) {
            $('#password_confirm').addClass('is-invalid');
            $('#password-confirm-error').removeClass('d-none').text('As senhas não coincidem');
            isValid = false;
        }
    }
    
    return isValid;
}

// Navigation functions
function nextStep() {
    if (currentStep < totalSteps && validateCurrentStep()) {
        showStep(currentStep + 1);
    }
}

function prevStep() {
    if (currentStep > 1) {
        showStep(currentStep - 1);
    }
}

function showStep(step) {
    // Hide current step
    $(`#step-${currentStep}`).removeClass('active');
    
    // Show new step
    $(`#step-${step}`).addClass('active');
    
    // Update current step
    currentStep = step;
    
    // Update progress
    updateProgress();
}

function updateProgress() {
    const progress = (currentStep / totalSteps) * 100;
    const stepNames = ['', 'Dados de Acesso', 'Dados Pessoais', 'Endereço'];
    
    $('#progress-bar').css('width', `${progress}%`);
    $('#step-name').text(stepNames[currentStep]);
    $('#step-count').text(`${currentStep} de ${totalSteps}`);
}

// Initialize when document is ready
$(document).ready(function() {
    initializeRegistrationForm();
});
