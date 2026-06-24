// Header Responsivo - JavaScript para melhorar a interação

document.addEventListener('DOMContentLoaded', function() {
    
    // Referências aos elementos
    const navbar = document.querySelector('.navbar');
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    const dropdownMenus = document.querySelectorAll('.dropdown-menu');
    
    // Função para adicionar classe scrolled ao header
    function handleScroll() {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    }
    
    // Função para fechar menu mobile ao clicar fora
    function handleClickOutside(event) {
        if (navbarCollapse && navbarCollapse.classList.contains('show')) {
            if (!navbar.contains(event.target)) {
                const bsCollapse = new bootstrap.Collapse(navbarCollapse, {
                    hide: true
                });
            }
        }
    }
    
    // Função para melhorar a animação do botão hambúrguer
    function animateHamburger() {
        const togglerIcon = navbarToggler.querySelector('.navbar-toggler-icon');
        if (navbarCollapse.classList.contains('show')) {
            togglerIcon.style.transform = 'rotate(90deg)';
        } else {
            togglerIcon.style.transform = 'rotate(0deg)';
        }
    }
    
    // Função para melhorar dropdowns
    function enhanceDropdowns() {
        dropdownMenus.forEach(dropdown => {
            const dropdownToggle = dropdown.previousElementSibling;
            
            // Adicionar animação ao abrir
            dropdownToggle.addEventListener('show.bs.dropdown', function() {
                dropdown.style.opacity = '0';
                dropdown.style.transform = 'translateY(-10px) scale(0.95)';
                
                setTimeout(() => {
                    dropdown.style.opacity = '1';
                    dropdown.style.transform = 'translateY(0) scale(1)';
                }, 10);
            });
            
            // Melhorar hover dos itens
            const dropdownItems = dropdown.querySelectorAll('.dropdown-item');
            dropdownItems.forEach(item => {
                item.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateX(5px)';
                });
                
                item.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateX(0)';
                });
            });
        });
    }
    
    // Função para melhorar botões mobile
    function enhanceMobileButtons() {
        const mobileButtons = document.querySelectorAll('.btn-mobile, .list-group-item');
        
        mobileButtons.forEach(button => {
            button.addEventListener('touchstart', function() {
                this.style.transform = 'scale(0.98)';
            });
            
            button.addEventListener('touchend', function() {
                this.style.transform = 'scale(1)';
            });
            
            button.addEventListener('click', function() {
                // Fechar menu mobile após clicar em um item
                if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                    setTimeout(() => {
                        const bsCollapse = new bootstrap.Collapse(navbarCollapse, {
                            hide: true
                        });
                    }, 100);
                }
            });
        });
    }
    
    // Função para melhorar acessibilidade
    function enhanceAccessibility() {
        // Melhorar navegação por teclado
        const focusableElements = navbar.querySelectorAll('button, a, input, select, textarea, [tabindex]:not([tabindex="-1"])');
        
        focusableElements.forEach(element => {
            element.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.click();
                }
            });
        });
        
        // Melhorar ARIA labels
        if (navbarToggler) {
            navbarToggler.setAttribute('aria-label', 'Alternar navegação');
        }
    }
    
    // Função para otimizar performance
    function optimizePerformance() {
        // Usar Intersection Observer para otimizar scroll
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                    }
                });
            }, {
                threshold: 0.1
            });
            
            // Observar elementos que podem ser animados
            const animatedElements = document.querySelectorAll('.navbar-brand, .navbar-nav');
            animatedElements.forEach(el => observer.observe(el));
        }
    }
    
    // Função para melhorar responsividade
    function enhanceResponsiveness() {
        // Detectar mudanças de orientação
        window.addEventListener('orientationchange', function() {
            setTimeout(() => {
                // Fechar menu mobile ao mudar orientação
                if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                    const bsCollapse = new bootstrap.Collapse(navbarCollapse, {
                        hide: true
                    });
                }
            }, 100);
        });
        
        // Detectar mudanças de tamanho de tela
        let resizeTimer;
        window.addEventListener('resize', function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                // Ajustar comportamento baseado no tamanho da tela
                if (window.innerWidth > 991) {
                    // Desktop: remover classes mobile
                    navbar.classList.remove('mobile-open');
                } else {
                    // Mobile: adicionar classes mobile
                    if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                        navbar.classList.add('mobile-open');
                    }
                }
            }, 250);
        });
    }
    
    // Função para melhorar UX
    function enhanceUX() {
        // Adicionar feedback visual ao scroll
        let scrollTimer;
        window.addEventListener('scroll', function() {
            clearTimeout(scrollTimer);
            scrollTimer = setTimeout(handleScroll, 10);
        });
        
        // Melhorar transições
        if (navbarToggler) {
            navbarToggler.addEventListener('click', animateHamburger);
        }
        
        // Melhorar fechamento do menu
        document.addEventListener('click', handleClickOutside);
        
        // Melhorar dropdowns
        enhanceDropdowns();
        
        // Melhorar botões mobile
        enhanceMobileButtons();
        
        // Melhorar acessibilidade
        enhanceAccessibility();
        
        // Otimizar performance
        optimizePerformance();
        
        // Melhorar responsividade
        enhanceResponsiveness();
    }
    
    // Inicializar melhorias
    if (navbar) {
        enhanceUX();
        
        // Adicionar classe inicial
        handleScroll();
        
        // Melhorar carregamento inicial
        setTimeout(() => {
            navbar.classList.add('loaded');
        }, 100);
    }
    
    // Melhorar performance em dispositivos móveis
    if ('ontouchstart' in window) {
        // Otimizações específicas para touch
        document.body.classList.add('touch-device');
        
        // Melhorar scroll em iOS
        document.addEventListener('touchmove', function(e) {
            if (e.target.closest('.navbar-collapse')) {
                e.preventDefault();
            }
        }, { passive: false });
    }
    
    // Melhorar acessibilidade para leitores de tela
    if (navbar) {
        navbar.setAttribute('role', 'navigation');
        navbar.setAttribute('aria-label', 'Navegação principal');
    }
    
    // Log para debug (remover em produção)
    console.log('Header responsivo carregado com sucesso!');
});

// Função global para finalizar jornada (mantida para compatibilidade)
window.finalizarJornada = function() {
    // Verificar se o modal existe
    const modal = document.getElementById('modalFinalizarJornada');
    if (modal) {
        // Usar modal Bootstrap se disponível
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    } else {
        // Fallback para confirm nativo
        if (confirm('Tem certeza que deseja finalizar sua jornada de trabalho?')) {
            // Implementar lógica de finalização de jornada
            console.log('Finalizando jornada...');
        }
    }
};
