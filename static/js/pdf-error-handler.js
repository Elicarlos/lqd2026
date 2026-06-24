/**
 * PDF Error Handler - Tratamento robusto de erros do PDF viewer
 * Este arquivo contém funções para lidar com erros comuns do PDF viewer
 */

// Função para verificar se o PDF foi carregado corretamente
function isPDFLoaded(iframe) {
    try {
        if (!iframe || !iframe.contentWindow) {
            return false;
        }
        
        // Verificar se o iframe tem conteúdo
        if (iframe.contentDocument && iframe.contentDocument.readyState === 'complete') {
            return true;
        }
        
        // Verificar se há erros no console do iframe
        if (iframe.contentWindow.console && iframe.contentWindow.console.error) {
            return true; // Se tem console, provavelmente carregou
        }
        
        return false;
    } catch (error) {
        console.warn('Erro ao verificar carregamento do PDF:', error);
        return false;
    }
}

// Função para aguardar o carregamento completo do PDF
function waitForPDFLoad(iframe, callback, maxAttempts = 10) {
    let attempts = 0;
    
    const checkLoad = () => {
        attempts++;
        
        if (isPDFLoaded(iframe)) {
            console.log('PDF carregado com sucesso');
            callback();
            return;
        }
        
        if (attempts >= maxAttempts) {
            console.error('Timeout ao carregar PDF após', maxAttempts, 'tentativas');
            callback(new Error('Timeout ao carregar PDF'));
            return;
        }
        
        // Aguardar 500ms antes da próxima verificação
        setTimeout(checkLoad, 500);
    };
    
    checkLoad();
}

// Função melhorada para imprimir PDF
function safePrintPDF(iframeId, options = {}) {
    const {
        timeout = 5000,
        retryAttempts = 3,
        onSuccess = null,
        onError = null
    } = options;
    
    const iframe = document.getElementById(iframeId);
    
    if (!iframe) {
        const error = new Error('Iframe não encontrado');
        console.error(error);
        if (onError) onError(error);
        return;
    }
    
    let attempts = 0;
    
    const attemptPrint = () => {
        attempts++;
        
        try {
            if (!iframe.contentWindow) {
                throw new Error('Iframe sem contentWindow');
            }
            
            // Focar no iframe
            iframe.focus();
            
            // Tentar imprimir
            iframe.contentWindow.print();
            
            console.log('Comando de impressão enviado com sucesso');
            if (onSuccess) onSuccess();
            
        } catch (error) {
            console.warn(`Tentativa ${attempts} falhou:`, error);
            
            if (attempts < retryAttempts) {
                // Aguardar um pouco antes de tentar novamente
                setTimeout(attemptPrint, 1000);
            } else {
                console.error('Todas as tentativas de impressão falharam');
                if (onError) onError(error);
            }
        }
    };
    
    // Aguardar o carregamento do PDF antes de tentar imprimir
    waitForPDFLoad(iframe, (error) => {
        if (error) {
            if (onError) onError(error);
            return;
        }
        
        // Aguardar um pouco mais para garantir que o PDF viewer esteja pronto
        setTimeout(attemptPrint, 1000);
    });
}

// Função para detectar erros do PDF viewer
function detectPDFViewerErrors() {
    // Interceptar erros do console relacionados ao PDF viewer
    const originalError = console.error;
    console.error = function(...args) {
        const message = args.join(' ');
        
        // Verificar se é um erro do PDF viewer
        if (message.includes('Could not find page for Y position') ||
            message.includes('pdf_viewer_wrapper') ||
            message.includes('shared.rollup')) {
            
            console.warn('Erro do PDF viewer detectado, tentando recuperar...');
            
            // Aguardar um pouco e tentar recarregar
            setTimeout(() => {
                const iframes = document.querySelectorAll('iframe[src*=".pdf"], iframe[src*="check_task_status"]');
                iframes.forEach(iframe => {
                    if (iframe.src) {
                        const currentSrc = iframe.src;
                        iframe.src = '';
                        setTimeout(() => {
                            iframe.src = currentSrc;
                        }, 100);
                    }
                });
            }, 1000);
        }
        
        // Chamar o console.error original
        originalError.apply(console, args);
    };
}

// Inicializar o detector de erros quando o script for carregado
if (typeof window !== 'undefined') {
    detectPDFViewerErrors();
}

// Exportar funções para uso global
if (typeof window !== 'undefined') {
    window.PDFErrorHandler = {
        isPDFLoaded,
        waitForPDFLoad,
        safePrintPDF,
        detectPDFViewerErrors
    };
} 