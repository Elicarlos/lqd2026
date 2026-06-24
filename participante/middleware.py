from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils.timezone import now
from django.urls import reverse
from .models import RegistroJornada, Campanha
import logging
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

logger = logging.getLogger(__name__)


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        frame_ancestors = "'self' https://lqd2024-ff3963465f8b.herokuapp.com https://teste-teste-lqd2024-fdb4a1ec713e.herokuapp.com"
        response["Content-Security-Policy"] = f"frame-ancestors {frame_ancestors}"
        return response


class VerificarCampanhaAtivaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exclui as páginas públicas
        if request.path.startswith(reverse("participante:login")):
            return self.get_response(request)

        # Verifica se há uma campanha ativa
        campanha_ativa = Campanha.objects.filter(ativa=True).first()
        if campanha_ativa and not campanha_ativa.esta_ativa():
            return redirect("participante:dashboard")

        return self.get_response(request)


class UpdateJornadaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ignora arquivos estáticos, APIs, requisições AJAX e páginas de login
        if (request.path.startswith("/static/") or 
            request.path.startswith("/media/") or 
            request.path.startswith("/login/") or
            request.path.startswith("/admin/") or
            request.headers.get("X-Requested-With") == "XMLHttpRequest"):
            return self.get_response(request)

        if request.user.is_authenticated:
            # Verifica grupos que precisam de jornada
            grupos_jornada = ["Operador", "Operadores", "Backoffice", "Supervisor", "Recursos Humanos"]
            precisa_jornada = any(request.user.groups.filter(name=grupo).exists() for grupo in grupos_jornada)
            
            if precisa_jornada:
                try:
                    # Atualiza o ultimo_update apenas para jornadas abertas
                    jornada_ativa = RegistroJornada.objects.filter(
                        user=request.user, horario_fim__isnull=True
                    ).first()

                    if jornada_ativa:
                        # Atualiza último acesso
                        jornada_ativa.ultimo_update = now()
                        jornada_ativa.save(update_fields=["ultimo_update"])
                        request.session["last_activity"] = now().timestamp()
                        
                        # Adiciona informações da jornada ao request
                        request.jornada_ativa = jornada_ativa
                        
                        # Log apenas a cada 5 minutos para não sobrecarregar
                        last_log = request.session.get("last_jornada_log", 0)
                        now_timestamp = now().timestamp()
                        if now_timestamp - last_log > 300:  # 5 minutos
                            logger.info(
                                f"Jornada {jornada_ativa.id} ativa para {request.user.username} em {jornada_ativa.posto_trabalho}"
                            )
                            request.session["last_jornada_log"] = now_timestamp

                except Exception as e:
                    logger.error(f"Erro ao atualizar jornada: {str(e)}")

        response = self.get_response(request)
        return response


class FinalizaJornadaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ignora páginas de login e admin
        if (request.path.startswith("/login/") or 
            request.path.startswith("/admin/")):
            return self.get_response(request)
            
        if request.user.is_authenticated:
            # Verifica grupos que precisam de jornada
            grupos_jornada = ["Operador", "Operadores", "Backoffice", "Supervisor"]
            precisa_jornada = any(request.user.groups.filter(name=grupo).exists() for grupo in grupos_jornada)
            
            if precisa_jornada:
                try:
                    # Verifica timeout de inatividade (30 minutos)
                    last_activity = request.session.get("last_activity")
                    if last_activity:
                        now_timestamp = now().timestamp()
                        if now_timestamp - last_activity > 1800:  # 30 minutos
                            jornada_ativa = RegistroJornada.objects.filter(
                                user=request.user, horario_fim__isnull=True
                            ).first()

                            if jornada_ativa:
                                # Finaliza a jornada
                                jornada_ativa.horario_fim = now()
                                jornada_ativa.save()
                                
                                # Registra no log
                                duracao = jornada_ativa.calcular_duracao()
                                logger.info(
                                    f"Jornada {jornada_ativa.id} finalizada por inatividade para {request.user.username}. "
                                    f"Duração: {duracao}. Posto: {jornada_ativa.posto_trabalho}"
                                )
                                
                                # Faz logout e redireciona
                                messages.warning(
                                    request,
                                    "Sua sessão expirou por inatividade. A jornada foi finalizada automaticamente."
                                )
                                logout(request)
                                return redirect("/")
                except Exception as e:
                    logger.error(f"Erro ao verificar inatividade: {str(e)}")

        response = self.get_response(request)

        # Verifica se é um logout
        grupos_jornada = ["Operador", "Operadores", "Backoffice", "Supervisor"]
        precisa_jornada = any(request.user.groups.filter(name=grupo).exists() for grupo in grupos_jornada)
        
        if (
            request.path == "/logout/"
            and request.user.is_authenticated
            and precisa_jornada
        ):
            try:
                jornada_ativa = RegistroJornada.objects.filter(
                    user=request.user, horario_fim__isnull=True
                ).first()

                if jornada_ativa:
                    # Finaliza a jornada
                    jornada_ativa.horario_fim = now()
                    jornada_ativa.save()
                    
                    # Registra no log
                    duracao = jornada_ativa.calcular_duracao()
                    logger.info(
                        f"Jornada {jornada_ativa.id} finalizada por logout para {request.user.username}. "
                        f"Duração: {duracao}. Posto: {jornada_ativa.posto_trabalho}"
                    )
                    
                    # Adiciona mensagem de sucesso
                    messages.success(
                        request,
                        f"Jornada finalizada com sucesso! Duração: {duracao}"
                    )
            except Exception as e:
                logger.error(f"Erro ao finalizar jornada no logout: {str(e)}")

        return response


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
            "/dados_campanha/",
            "/registro_ponto/",
            "/registro_ponto_filtros/",
        ]
        
        # URLs que não devem ser redirecionadas
        self.no_redirect_urls = [
            "/selecionar-posto/",
            "/participante/selecionar-posto/",
            "/change-password/",
            "/participante/change-password/",
            "/logout/",
            "/participante/logout/",
            "/cadastros/",
            "/participante/cadastros/",
            "/cadastro-participante-operador/",
            "/participante/cadastro-participante-operador/",
        ]

        # Mapeamento de grupos para seus dashboards
        self.role_dashboards = {
            "Operador": "lojista:homepage",
            "Gerente": "lojista:homepage",
            "Backoffice": "lojista:homepage",
            "Supervisor": "lojista:homepage",
            "Suporte": "lojista:homepage",
            "Gerente Solve": "lojista:homepage",
            "Recursos Humanos": "lojista:homepage",
            "Operadores": "lojista:homepage",
        }

    def __call__(self, request):
        """Handle the request and return the response."""
        
        # Check for a welcome message, which indicates a user was just created
        storage = messages.get_messages(request)
        welcome_message_present = any('Bem-vindo(a)' in str(m) for m in storage)
        storage.used = False # Make messages available for the view

        # Verificar se usuário logado precisa selecionar posto de trabalho
        if request.user.is_authenticated and not welcome_message_present:
            # Verificar se é staff e tem grupo operacional
            if request.user.is_staff:
                grupos_operacionais = ['Operador', 'Gerente', 'Backoffice', 'Supervisor', 'Gerente Solve', 'Recursos Humanos', 'Suporte']
                tem_grupo_operacional = request.user.groups.filter(name__in=grupos_operacionais).exists()
                
                if tem_grupo_operacional:
                    # Sempre redirecionar para o dashboard, que mostrará o modal se necessário
                    if not request.path_info.startswith('/lojista/'):
                        return redirect('lojista:homepage')

        if self._needs_auth(request.path_info) and not welcome_message_present:
            response = self._handle_auth(request)
            if response:
                return response
        
        return self.get_response(request)

    def _needs_auth(self, path):
        """Verifica se a URL requer autenticação"""
        
        # Não redirecionar URLs específicas
        if any(path.startswith(url) for url in self.no_redirect_urls):
            return False
        
        needs_auth = any(path.startswith(url) for url in self.protected_urls)
        return needs_auth

    def _get_user_dashboard(self, user):
        """Determina o dashboard correto baseado no tipo de usuário"""
        
        # Verifica grupos do usuário primeiro
        for group, dashboard in self.role_dashboards.items():
            if user.groups.filter(name=group).exists():
                return dashboard

        # Se não tem grupo específico, verificar se é superuser ou staff
        if user.is_superuser or user.is_staff:
            return "lojista:homepage"

        # Participante comum
        return "participante:dashboard"

    def _handle_auth(self, request):
        """
        Gerencia autenticação e redirecionamentos.
        Retorna uma resposta se precisar redirecionar, None caso contrário.
        """
        path = request.path_info.lstrip("/")

        # Se não estiver logado, redireciona para homepage
        if not request.user.is_authenticated:
            # Não adiciona mensagem para requisições AJAX
            if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
                messages.warning(request, "Por favor, faça login para continuar.")
            return redirect("/")

        # Verifica se o usuário está tentando acessar uma área restrita
        if "lojista" in path and not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect(self._get_user_dashboard(request.user))

        # Verifica se staff está tentando acessar área de participante
        if path.startswith("participante/") and not request.user.is_staff:
            # Verifica se tem grupos operacionais que podem acessar área de participante
            grupos_operacionais = ['Operador', 'Gerente', 'Backoffice', 'Supervisor', 'Gerente Solve', 'Recursos Humanos', 'Suporte']
            if not any(
                request.user.groups.filter(name=group).exists()
                for group in grupos_operacionais
            ):
                messages.error(request, "Área restrita para staff.")
                return redirect(self._get_user_dashboard(request.user))

        return None


class JornadaControlMiddleware:
    """
    Middleware para controlar acesso baseado em jornadas de trabalho.
    Bloqueia login de colaboradores fora do horário de trabalho atribuído.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs que devem ser sempre permitidas (login, logout, etc.)
        self.always_allowed_urls = [
            '/admin/',
            '/login/',
            '/logout/',
            '/accounts/login/',
            '/accounts/logout/',
            '/static/',
            '/media/',
            '/barcode/',  # URLs de impressão devem ser sempre permitidas
            '/bcp/print/',  # URLs específicas de impressão
            '/bcp/check_task_status/',  # Verificação de status de tarefas
            '/bcp/serve_pdf_from_task/',  # Servir PDFs
            '/bcp/confirm_print/',  # Confirmação de impressão
            '/bcp/clear_print_session/',  # Limpeza de sessão
        ]
        
        # URLs que devem ser bloqueadas para colaboradores fora do horário
        self.restricted_urls = [
            '/lojista/',
            '/participante/',
            '/validadocfiscal/',
            '/marcar_inconsistente/',
            '/cupom/',
        ]
    
    def __call__(self, request):
        # Ignora páginas sempre permitidas
        path = request.path_info
        
        if any(path.startswith(url) for url in self.always_allowed_urls):
            return self.get_response(request)
        
        # Para páginas de login, não interferir no processo de autenticação
        if path.startswith('/login/') or path.startswith('/accounts/login/'):
            return self.get_response(request)
        
        # Para requisições POST em páginas de login, não interferir
        if request.method == 'POST' and (path.startswith('/login/') or path.startswith('/accounts/login/')):
            return self.get_response(request)
            
        # Verificar se o usuário está logado
        if request.user.is_authenticated:
            # Superusers sempre podem acessar
            if request.user.is_superuser:
                return self.get_response(request)
            
            # Staff com grupos operacionais - deixar o RoleBasedRedirectionMiddleware cuidar do redirecionamento
            if request.user.is_staff:
                grupos_operacionais = ['Operador', 'Gerente', 'Backoffice', 'Supervisor', 'Gerente Solve', 'Recursos Humanos', 'Suporte']
                tem_grupo_operacional = request.user.groups.filter(name__in=grupos_operacionais).exists()
                
                if tem_grupo_operacional:
                    # O RoleBasedRedirectionMiddleware cuidará do redirecionamento
                    pass
            
            # Verificar se está tentando acessar área restrita
            path = request.path_info
            is_restricted = any(path.startswith(url) for url in self.restricted_urls)
            
            if is_restricted:
                # Verificar jornada do colaborador
                from .models import JornadaColaborador
                jornada_colaborador = JornadaColaborador.get_jornada_ativa(request.user)
                
                if jornada_colaborador:
                    # Verificar se pode logar agora
                    pode_logar, motivo = jornada_colaborador.tipo_jornada.pode_logar_agora()
                    
                    if not pode_logar:
                        # Não fazer logout automático, apenas bloquear acesso
                        
                        # Adicionar mensagem explicativa
                        messages.error(
                            request, 
                            f"Acesso negado: {motivo}. "
                            f"Sua jornada '{jornada_colaborador.tipo_jornada.nome}' "
                            f"permite acesso das {jornada_colaborador.tipo_jornada.hora_inicio.strftime('%H:%M')} "
                            f"às {jornada_colaborador.tipo_jornada.hora_fim.strftime('%H:%M')} "
                            f"nos dias: {jornada_colaborador.tipo_jornada.get_dias_semana_display()}."
                        )
                        
                        # Redirecionar para homepage sem fazer logout
                        return redirect('/')
                else:
                    # Usuário não tem jornada atribuída - permitir acesso
                    # (ou você pode escolher bloquear também)
                    pass
        
        return self.get_response(request)


class ForcePasswordChangeMiddleware:
    """
    Middleware para forçar usuários com senha temporária a trocar a senha.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Verificar se o usuário tem senha temporária
            if hasattr(request.user, 'profile') and request.user.profile and request.user.profile.senha_temporaria:
                # URLs que não precisam de troca de senha
                allowed_urls = [
                    '/change-password/',
                    '/participante/change-password/',
                    '/participante/logout/',
                    '/logout/',
                    '/selecionar-posto/',
                    '/participante/selecionar-posto/',
                    '/static/',
                    '/media/',
                ]
                
                current_path = request.path
                
                # Verificar se a URL atual não está na lista de permitidas
                is_allowed = any(current_path.startswith(url) for url in allowed_urls)
                
                if not is_allowed:
                    from django.shortcuts import redirect
                    from django.contrib import messages
                    
                    # Redirecionar para troca de senha
                    messages.warning(request, 'Você precisa alterar sua senha temporária antes de continuar.')
                    return redirect('participante:change_password')
        
        response = self.get_response(request)
        return response
