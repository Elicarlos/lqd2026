from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import CardDinamico

def require_card_permission(card_name, redirect_url='homepage'):
    """
    Decorator para verificar permissão de card.
    
    Args:
        card_name (str): Nome do card a ser verificado
        redirect_url (str): URL para redirecionar se não tiver permissão
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Superusers sempre têm acesso
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            try:
                # Buscar o card
                card = CardDinamico.objects.get(nome=card_name, ativo=True)
                
                # Verificar se o usuário pode ver o card
                if card.pode_ver(request.user):
                    return view_func(request, *args, **kwargs)
                else:
                    messages.error(request, f"Você não tem permissão para acessar esta funcionalidade.")
                    return redirect(redirect_url)
                    
            except CardDinamico.DoesNotExist:
                # Se o card não existe, usar verificação padrão
                if request.user.is_staff:
                    return view_func(request, *args, **kwargs)
                else:
                    messages.error(request, "Funcionalidade não configurada.")
                    return redirect(redirect_url)
        
        return _wrapped_view
    return decorator

def require_group_permission(group_names, redirect_url='homepage'):
    """
    Decorator para verificar se o usuário pertence a um dos grupos especificados.
    
    Args:
        group_names (list): Lista de nomes de grupos permitidos
        redirect_url (str): URL para redirecionar se não tiver permissão
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Superusers sempre têm acesso
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Verificar se o usuário pertence a um dos grupos
            if request.user.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Você não tem permissão para acessar esta funcionalidade.")
                return redirect(redirect_url)
        
        return _wrapped_view
    return decorator
