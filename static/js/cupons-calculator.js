/**
 * Sistema Modular de Cálculo de Cupons
 * Reutilizável em qualquer parte do sistema
 * Seguro - Cálculo no servidor
 * Performático - Cache e debounce
 */

var CuponsCalculator = {
    // Cache para evitar requisições desnecessárias
    cache: {},
    timeout: null,
    
    // Função principal para calcular cupons via servidor
    calcular: function(valorCielo, valorOutros, callback, url) {
        var cacheKey = valorCielo + '_' + valorOutros;
        
        // Verificar cache primeiro (performance)
        if (this.cache[cacheKey]) {
            callback(this.cache[cacheKey]);
            return;
        }
        
        // Mostrar loading se callback for fornecido
        if (callback) {
            callback({loading: true});
        }
        
        // Fazer requisição AJAX
        $.ajax({
            url: url || "/participante/calcular-cupons-preview/",
            method: 'POST',
            data: {
                valor_cielo: valorCielo,
                valor_outros: valorOutros,
                csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()
            },
            success: function(response) {
                if (response.success) {
                    // Salvar no cache (performance)
                    CuponsCalculator.cache[cacheKey] = response;
                    callback(response);
                } else {
                    callback({error: response.error});
                }
            },
            error: function(xhr, status, error) {
                callback({error: 'Erro na conexão. Tente novamente.'});
            }
        });
    },
    
    // Função para limpar cache (útil para atualizações)
    limparCache: function() {
        this.cache = {};
    },
    
    // Função para debounce (performance)
    calcularComDebounce: function(valorCielo, valorOutros, callback, delay, url) {
        clearTimeout(this.timeout);
        this.timeout = setTimeout(function() {
            CuponsCalculator.calcular(valorCielo, valorOutros, callback, url);
        }, delay || 500);
    },
    
    // Função para formatar valores monetários
    formatMoney: function(value) {
        return value.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    },
    
    // Função para converter string de dinheiro para número
    parseMoney: function(value) {
        if (!value) return 0;
        return parseFloat(value.replace(/\./g, '').replace(',', '.')) || 0;
    }
};

// Função reutilizável para atualizar preview
function atualizarPreviewCupons(data, containerSelector) {
    var valorCielo = data.valor_cielo || 0;
    var valorOutros = data.valor_outros || 0;
    var cupons = data.cupons || 0;
    var valorTotal = data.valor_total || 0;
    
    var container = $(containerSelector || '#preview-cupons-container');
    
    if (container.length) {
        if (data.loading) {
            container.find('.cupons-total').html('<i class="fas fa-spinner fa-spin"></i>');
            return;
        }
        
        if (data.error) {
            container.removeClass('alert-info').addClass('alert-danger');
            container.find('.cupons-total').html('<i class="fas fa-exclamation-triangle"></i> Erro');
            return;
        }
        
        // Restaurar estilo normal
        container.removeClass('alert-danger').addClass('alert-info');
        container.find('.cupons-total').text(cupons);
        container.find('.valor-cielo').text('R$ ' + CuponsCalculator.formatMoney(valorCielo));
        container.find('.valor-outros').text('R$ ' + CuponsCalculator.formatMoney(valorOutros));
        container.find('.valor-total').text('R$ ' + CuponsCalculator.formatMoney(valorTotal));
        
        // Animação sutil
        container.addClass('animate__animated animate__pulse');
        setTimeout(function() {
            container.removeClass('animate__animated animate__pulse');
        }, 300);
    }
}
