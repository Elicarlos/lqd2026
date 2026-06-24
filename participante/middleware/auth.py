import logging
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)

class ForcePasswordChangeMiddleware:
    """
    Middleware para forçar usuários com senha temporária a trocar a senha.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Verificar se o usuário tem senha temporária
            logger.debug(f"[AUTH] User: {request.user.username}")
            logger.debug(f"[AUTH] Has profile: {hasattr(request.user, 'profile')}")
            
            if hasattr(request.user, 'profile') and request.user.profile:
                logger.debug(f"[AUTH] Temporary Password: {request.user.profile.senha_temporaria}")
            
            if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.senha_temporaria:
                # URLs que não precisam de troca de senha
                allowed_urls = [
                    '/change-password/',
                    '/participante/change-password/',
                    '/participante/logout/',
                    '/static/',
                    '/media/',
                ]
                
                # Verifica se a URL atual está na lista de permitidas
                if not any(request.path.startswith(url) for url in allowed_urls):
                    logger.warning(f"[AUTH] Redirecting user {request.user.username} to change password")
                    return redirect('participante:password_change')

        return self.get_response(request)

class RoleBasedRedirectionMiddleware:
    """
    Middleware para gerenciar redirecionamentos baseados em papéis de usuário.
    Garante que cada tipo de usuário acesse apenas as áreas permitidas.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.async_mode = False

        # URLs que requerem autenticação
        self.protected_urls = [
            "/dashboard/",
            "/backoffice/",
            "/docsfiscais/",
            "/coupons/",
            "/premios/",
            "/edit/",
            "/adddocfiscal/",
            "/editdocfiscal/",
            "/validadocfiscal/",
            "/marcar_inconsistente/",
        ]
        
        # URLs que são sempre permitidas (APIs)
        self.api_urls = [
            "/api/participante/confirmar_impressao/",
            "/api/participante/confirmar_impressao_simple/",
            "/api/participante/reverter_impressao_simple/",
            "/api/participante/test/",
            "/api/jornada-status/",
            "/participante/reverter_impressao/",
        ]

    def __call__(self, request):
        # Ignora arquivos estáticos e admin
        if request.path.startswith(('/static/', '/admin/', '/media/')):
            return self.get_response(request)

        # Verifica se é uma URL da API (sempre permitida)
        is_api_url = any(request.path.startswith(url) for url in self.api_urls)
        if is_api_url:
            logger.debug(f"[AUTH] API URL detected: {request.path}")
            return self.get_response(request)

        # Verifica se é uma URL protegida
        is_protected = any(request.path.startswith(url) for url in self.protected_urls)
        
        if is_protected and not request.user.is_authenticated:
            logger.warning(f"[AUTH] Unauthorized access attempt to {request.path}")
            return redirect('participante:login')

        response = self.get_response(request)
        return response

class JornadaControlMiddleware:
    """
    Middleware para controlar acesso baseado em jornadas de trabalho.
    Bloqueia login de colaboradores fora do horário de trabalho atribuído.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs que devem ser sempre permitidas
        self.always_allowed_urls = [
            '/admin/',
            '/login/',
            '/logout/',
            '/accounts/login/',
            '/accounts/logout/',
            '/static/',
            '/media/',
            '/barcode/',  # URLs de impressão
            '/bcp/print/',  # URLs específicas de impressão
            '/api/jornada-status/',  # URL para verificar status da jornada
            '/api/participante/confirmar_impressao/',  # API de confirmação de impressão
            '/api/participante/confirmar_impressao_simple/',  # API simplificada
            '/participante/reverter_impressao/',  # API de reversão
            '/bcp/check_task_status/',  # Verificação de status
            '/password-change/',
            '/password-reset/',
            '/selecionar_posto/',  # Página de seleção de posto
            '/participante/selecionar-posto/',  # URL completa para seleção de posto

            '/',  # Homepage - sempre permitida para evitar loops
        ]

    def __call__(self, request):
        # Log da URL atual
        logger.debug(f"[JORNADA] Path: {request.path}")
        
        # Verifica se é uma URL sempre permitida
        if any(request.path.startswith(url) for url in self.always_allowed_urls):
            logger.debug("[JORNADA] ✅ URL sempre permitida")
            return self.get_response(request)

        # Fast path para usuários não autenticados
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Verifica se o usuário precisa de controle de jornada
        if not self.requer_controle_jornada(request.user):
            logger.debug(f"[JORNADA] ✅ Usuário {request.user.username} não requer controle de jornada")
            return self.get_response(request)

        # Verifica se o usuário tem jornada ativa
        if self.tem_jornada_ativa(request.user):
            logger.debug(f"[JORNADA] ✅ Usuário {request.user.username} tem jornada ativa")
            return self.get_response(request)

        # Verifica se pode iniciar jornada OU se já tem jornada ativa
        pode_iniciar, motivo = self.pode_iniciar_jornada(request.user)
        tem_jornada_ativa = self.tem_jornada_ativa(request.user)
        
        if pode_iniciar or tem_jornada_ativa:
            if pode_iniciar:
                logger.debug(f"[JORNADA] ✅ Usuário {request.user.username} pode iniciar jornada: {motivo}")
            else:
                logger.debug(f"[JORNADA] ✅ Usuário {request.user.username} já possui jornada ativa")
            
            # Staff com grupo operacional deve ir para o dashboard (modal aparecerá se necessário)
            if request.user.is_staff:
                grupos_operacionais = ['Operador', 'Gerente', 'Backoffice', 'Supervisor', 'Gerente Solve', 'Recursos Humanos', 'Suporte']
                tem_grupo_operacional = request.user.groups.filter(name__in=grupos_operacionais).exists()
                
                if tem_grupo_operacional:
                    logger.debug(f"[JORNADA] ✅ Staff com grupo operacional - permitindo acesso ao dashboard")
                    # O modal aparecerá automaticamente se necessário
            
            # Para staff com grupo operacional, permitir acesso ao dashboard
            # O modal aparecerá automaticamente se necessário
            return self.get_response(request)
        else:
            logger.warning(f"[JORNADA] ❌ Usuário {request.user.username} não pode iniciar jornada: {motivo}")
            # Só adiciona mensagem de erro se não estiver na homepage para evitar spam
            if request.path != '/':
                messages.error(request, f"Acesso negado: {motivo}")
                return redirect('/')
            else:
                # Se já está na homepage, apenas processa a requisição
                logger.debug(f"[JORNADA] Usuário já está na homepage, processando requisição")
                return self.get_response(request)

        # Processa a requisição
        response = self.get_response(request)
        return response

    def requer_controle_jornada(self, user):
        """Verifica se o usuário precisa de controle de jornada"""
        try:
            # Verifica exceções individuais primeiro
            from participante.models import ExcecaoJornada
            excecao = ExcecaoJornada.objects.filter(
                usuario=user,
                tipo='SEM_JORNADA',
                ativo=True
            ).filter(
                models.Q(data_fim__isnull=True) | models.Q(data_fim__gte=timezone.localdate())
            ).first()
            
            if excecao and excecao.is_vigente():
                return False
            
            # Verifica configuração do grupo
            from participante.models import ConfiguracaoJornada
            for grupo in user.groups.all():
                config = ConfiguracaoJornada.objects.filter(
                    grupo=grupo,
                    ativo=True
                ).first()
                
                if config and not config.requer_jornada:
                    return False
            
            # Verifica configuração individual
            if hasattr(user, 'profile') and user.profile:
                return user.profile.requer_jornada
            
            return True
        except Exception as e:
            logger.error(f"[JORNADA] Erro ao verificar controle de jornada: {str(e)}")
            return True

    def tem_jornada_ativa(self, user):
        """Verifica se o usuário tem uma jornada ativa"""
        try:
            from participante.models import RegistroJornada
            return RegistroJornada.get_jornada_ativa(user) is not None
        except Exception as e:
            logger.error(f"[JORNADA] Erro ao verificar jornada ativa: {str(e)}")
            return False

    def pode_iniciar_jornada(self, user):
        """Verifica se o usuário pode iniciar uma nova jornada"""
        try:
            # Se não requer jornada, não pode iniciar
            if not self.requer_controle_jornada(user):
                return False, "Usuário não requer controle de jornada"
            
            # Se já tem jornada ativa, não pode iniciar outra
            if self.tem_jornada_ativa(user):
                return False, "Usuário já possui jornada ativa"
            
            # Se tem jornada flexível, pode iniciar a qualquer momento
            if self.tem_jornada_flexivel(user):
                return True, "Jornada flexível permitida"
            
            # Verifica se está no horário permitido
            from participante.models import JornadaColaborador
            jornada_colaborador = JornadaColaborador.get_jornada_ativa(user)
            if jornada_colaborador:
                pode_logar, motivo = jornada_colaborador.tipo_jornada.pode_logar_agora()
                if pode_logar:
                    return True, "Horário permitido"
                else:
                    return False, motivo
            
            return False, "Nenhuma jornada configurada para hoje"
        except Exception as e:
            logger.error(f"[JORNADA] Erro ao verificar se pode iniciar jornada: {str(e)}")
            return False, "Erro ao verificar permissões"

    def tem_jornada_flexivel(self, user):
        """Verifica se o usuário tem jornada flexível"""
        try:
            # Verifica exceções individuais primeiro
            from participante.models import ExcecaoJornada
            excecao = ExcecaoJornada.objects.filter(
                usuario=user,
                tipo='JORNADA_FLEXIVEL',
                ativo=True
            ).filter(
                models.Q(data_fim__isnull=True) | models.Q(data_fim__gte=timezone.localdate())
            ).first()
            
            if excecao and excecao.is_vigente():
                return True
            
            # Verifica configuração do grupo
            from participante.models import ConfiguracaoJornada
            for grupo in user.groups.all():
                config = ConfiguracaoJornada.objects.filter(
                    grupo=grupo,
                    ativo=True
                ).first()
                
                if config and config.jornada_flexivel:
                    return True
            
            # Verifica configuração individual
            if hasattr(user, 'profile') and user.profile:
                return user.profile.jornada_flexivel
            
            return False
        except Exception as e:
            logger.error(f"[JORNADA] Erro ao verificar jornada flexível: {str(e)}")
            return False
