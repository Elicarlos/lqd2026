import logging
from django.utils.timezone import now
from django.shortcuts import redirect
from django.contrib import messages
from django.core.cache import cache

logger = logging.getLogger(__name__)

class JornadaControlMiddleware:
    """
    Middleware para controlar acesso baseado em jornadas de trabalho.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.always_allowed = {'/admin/', '/login/', '/logout/', '/static/', '/media/', 
                             '/password-change/', '/password-reset/'}

    def __call__(self, request):
        path = request.path
        
        # Fast path para URLs permitidas
        if path.startswith(tuple(self.always_allowed)):
            return self.get_response(request)

        # Fast path para usuários não autenticados
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Cache key para verificação de jornada
        cache_key = f'jornada_check_{request.user.id}'
        cached_result = cache.get(cache_key)
        
        if cached_result:
            if cached_result == 'allowed':
                return self.get_response(request)
            return redirect('participante:login')

        # Verifica grupos (apenas se necessário)
        if not any(g.name in {'Operador', 'Operadores'} for g in request.user.groups.all()):
            cache.set(cache_key, 'allowed', 300)  # 5 min cache
            return self.get_response(request)

        # Verifica horário (apenas para operadores)
        profile = getattr(request.user, 'profile', None)
        if not profile or not profile.tipo_jornada:
            cache.set(cache_key, 'denied', 300)
            return redirect('participante:login')

        jornada = profile.tipo_jornada
        hora_atual = now().time()
        
        if jornada.hora_inicio <= hora_atual <= jornada.hora_fim:
            cache.set(cache_key, 'allowed', 60)  # 1 min cache
            return self.get_response(request)
        
        cache.set(cache_key, 'denied', 60)
        messages.error(request, 
            f'Horário permitido: {jornada.hora_inicio.strftime("%H:%M")} às {jornada.hora_fim.strftime("%H:%M")}')
        return redirect('participante:login')

class UpdateJornadaMiddleware:
    """
    Middleware para atualizar o último acesso da jornada.
    """
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
            grupos_jornada = ["Operador", "Operadores", "Backoffice", "Supervisor"]
            precisa_jornada = any(request.user.groups.filter(name=grupo).exists() for grupo in grupos_jornada)
            
            if precisa_jornada and not request.user.is_superuser:
                try:
                    # Verificar se tem profile
                    if hasattr(request.user, 'profile') and request.user.profile:
                        # Atualiza o ultimo_update apenas para jornadas abertas (RegistroJornada)
                        from participante.models import RegistroJornada
                        jornada_ativa = RegistroJornada.objects.filter(
                            user=request.user,
                            horario_fim__isnull=True
                        ).first()
                        
                        if jornada_ativa:
                            jornada_ativa.ultimo_update = now()
                            jornada_ativa.save(update_fields=['ultimo_update'])
                            logger.debug(f"[JORNADA] Atualizado último acesso: {request.user.username}")
                except Exception as e:
                    logger.error(f"[JORNADA] Erro ao atualizar jornada: {str(e)}")

        return self.get_response(request)

class FinalizaJornadaMiddleware:
    """
    Middleware para finalizar jornadas automaticamente após inatividade.
    """
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
            
            if precisa_jornada and not request.user.is_superuser:
                try:
                    # Verificar se tem profile
                    if hasattr(request.user, 'profile') and request.user.profile:
                        # Verifica timeout de inatividade (30 minutos)
                        last_activity = request.session.get("last_activity")
                        if last_activity:
                            now_timestamp = now().timestamp()
                            if (now_timestamp - float(last_activity)) > 1800:  # 30 minutos
                                # Finaliza a jornada atual
                                jornada = request.user.profile.jornada_atual
                                if jornada and not jornada.horario_fim:
                                    jornada.horario_fim = now()
                                    jornada.save()
                                    logger.warning(f"[JORNADA] Finalizada por inatividade: {request.user.username}")
                                    
                                    # Força logout
                                    from django.contrib.auth import logout
                                    logout(request)
                                    return redirect('participante:login')
                except Exception as e:
                    logger.error(f"[JORNADA] Erro ao finalizar jornada: {str(e)}")
                    
                # Atualiza timestamp de última atividade
                request.session["last_activity"] = now().timestamp()

        return self.get_response(request)