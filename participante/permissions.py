from django.contrib.auth.decorators import user_passes_test
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Group
from django.shortcuts import redirect
from django.urls import reverse

# Roles como constantes para evitar erros de digitação
ROLE_OPERADOR = "Operador"
ROLE_GERENTE = "Gerente"
ROLE_BACKOFFICE = "Backoffice"
ROLE_SUPERVISOR = "Supervisor"
ROLE_GERENTE_SOLVE = "Gerente Solve"
ROLE_RECURSOS_HUMANOS = "Recursos Humanos"
ROLE_SUPORTE = "Suporte"


def get_user_roles(user):
    """Retorna uma lista com todos os roles do usuário."""
    if user.is_superuser:
        return ["superuser"] + [g.name for g in Group.objects.all()]
    return [g.name for g in user.groups.all()]


def has_role(user, role_name):
    """Verifica se o usuário tem um determinado role."""
    return user.groups.filter(name=role_name).exists() or user.is_superuser


def has_any_role(user, role_names):
    """Verifica se o usuário tem pelo menos um dos roles especificados."""
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=role_names).exists()


def has_all_roles(user, role_names):
    """Verifica se o usuário tem todos os roles especificados."""
    if user.is_superuser:
        return True
    user_roles = set(user.groups.values_list('name', flat=True))
    return all(role in user_roles for role in role_names)


def is_operador(user):
    """Verifica se o usuário é operador."""
    return has_role(user, ROLE_OPERADOR)


def is_gerente(user):
    """Verifica se o usuário é gerente."""
    return has_role(user, ROLE_GERENTE)


def is_backoffice(user):
    """Verifica se o usuário é backoffice."""
    return has_role(user, ROLE_BACKOFFICE)


def is_supervisor(user):
    """Verifica se o usuário é supervisor."""
    return has_role(user, ROLE_SUPERVISOR)


def is_gerente_solve(user):
    """Verifica se o usuário é gerente solve."""
    return has_role(user, ROLE_GERENTE_SOLVE)


def is_recursos_humanos(user):
    """Verifica se o usuário é recursos humanos."""
    return has_role(user, ROLE_RECURSOS_HUMANOS)


def is_suporte(user):
    """Verifica se o usuário é suporte."""
    return has_role(user, ROLE_SUPORTE)


def has_operational_access(user):
    """
    Verifica se o usuário tem acesso operacional (é colaborador/staff).
    Usado como substituto simples para o sistema de roles complexo.
    """
    return user.is_superuser or user.is_staff


def get_user_dashboard_cards(user):
    """
    Retorna os cards do dashboard que o usuário tem permissão para acessar.
    """
    from .models import DashboardCard, RoleCard, SystemRole
    
    # Superuser vê todos os cards ativos
    if user.is_superuser:
        return DashboardCard.objects.filter(is_active=True).order_by('order')
    
    # Staff e outros usuários veem apenas cards dos seus grupos/roles
    card_ids = set()
    
    # Verificar cards por grupos Django
    for group in user.groups.all():
        try:
            # Buscar role correspondente ao grupo
            role = SystemRole.objects.get(name=group.name)
            cards = RoleCard.objects.filter(role=role, card__is_active=True).values_list('card_id', flat=True)
            card_ids.update(cards)
        except SystemRole.DoesNotExist:
            # Se não encontrar role, usar cards padrão do grupo
            pass
    
    # Verificar cards por UserRoles
    from .models import UserRole
    user_roles = UserRole.objects.filter(user=user)
    for user_role in user_roles:
        cards = RoleCard.objects.filter(role=user_role.role, card__is_active=True).values_list('card_id', flat=True)
        card_ids.update(cards)
    
    # Se o usuário é staff mas não tem cards específicos, dar acesso a cards básicos
    if user.is_staff and not card_ids:
        # Cards básicos para staff sem role específico
        basic_cards = [
            'cadastrar_participante',
            'buscar_cpf', 
            'lista_participantes',
            'colaboradores_pendentes'
        ]
        basic_card_ids = DashboardCard.objects.filter(
            codename__in=basic_cards,
            is_active=True
        ).values_list('id', flat=True)
        card_ids.update(basic_card_ids)
    
    return DashboardCard.objects.filter(id__in=card_ids, is_active=True).order_by('order')


def user_has_card_permission(user, card_codename):
    """
    Verifica se o usuário tem permissão para acessar um card específico.
    """
    from .models import DashboardCard, RoleCard, SystemRole
    
    # Superuser tem acesso a todos os cards
    if user.is_superuser:
        return True
    
    # Verificar se o usuário tem o card através de grupos Django
    for group in user.groups.all():
        try:
            role = SystemRole.objects.get(name=group.name)
            if RoleCard.objects.filter(role=role, card__codename=card_codename, card__is_active=True).exists():
                return True
        except SystemRole.DoesNotExist:
            pass
    
    # Verificar se o usuário tem o card através de UserRoles
    from .models import UserRole
    user_roles = UserRole.objects.filter(user=user)
    for user_role in user_roles:
        if RoleCard.objects.filter(role=user_role.role, card__codename=card_codename, card__is_active=True).exists():
            return True
    
    return False


def get_cards_by_type(user, card_type):
    """
    Retorna os cards de um tipo específico que o usuário tem permissão para acessar.
    Usa o novo sistema CardDinamico.
    """
    from .models import CardDinamico
    
    # Mapeamento de tipos da view para tipos do modelo
    tipo_mapping = {
        'configuracoes': 'CONFIGURACAO',
        'backoffice': 'BACKOFFICE', 
        'relatorios': 'RELATORIO',
        'usuarios': 'RECURSOS_HUMANOS',
        'operacoes': 'OPERACOES',
        'participantes': 'PARTICIPANTE',
        'lojistas': 'LOJISTA',
    }
    
    # Obter o tipo correto do modelo
    tipo_modelo = tipo_mapping.get(card_type.lower(), card_type.upper())
    
    # Filtrar cards por tipo e que o usuário pode ver
    cards = CardDinamico.objects.filter(
        ativo=True,
        tipo=tipo_modelo
    ).order_by('ordem')
    
    # Filtrar apenas os cards que o usuário pode ver
    return [card for card in cards if card.pode_ver(user)]


def require_card_permission(card_codename):
    """
    Decorator para verificar se o usuário tem permissão para acessar um card.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not user_has_card_permission(request.user, card_codename):
                raise PermissionDenied("Você não tem permissão para acessar esta funcionalidade.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# Decorators para views
def role_required(role_name):
    """
    Decorator que verifica se o usuário tem um role específico.
    Uso: @role_required('Gerente')
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if not has_role(request.user, role_name):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def any_role_required(role_names):
    """
    Decorator que verifica se o usuário tem pelo menos um dos roles especificados.
    Uso: @any_role_required(['Gerente', 'Supervisor'])
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if not has_any_role(request.user, role_names):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def all_roles_required(role_names):
    """
    Decorator que verifica se o usuário tem todos os roles especificados.
    Uso: @all_roles_required(['Gerente', 'Recursos_Humanos'])
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if not has_all_roles(request.user, role_names):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


# Mixin para Class-Based Views
class RoleRequiredMixin:
    required_role = None  # Define na view: required_role = 'Gerente'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not has_role(request.user, self.required_role):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class AnyRoleRequiredMixin:
    required_roles = []  # Define na view: required_roles = ['Gerente', 'Supervisor']

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not has_any_role(request.user, self.required_roles):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


# Permissões específicas por funcionalidade
PERMISSIONS = {
    "dashboard": {
        ROLE_OPERADOR: ["view_dashboard", "add_registro"],
        ROLE_GERENTE: ["view_dashboard", "view_reports", "manage_users"],
        ROLE_BACKOFFICE: ["view_dashboard", "process_documents"],
        ROLE_SUPERVISOR: [
            "view_dashboard",
            "view_reports",
            "manage_users",
            "approve_requests",
        ],
        ROLE_GERENTE_SOLVE: ["view_dashboard", "view_reports", "manage_system"],
        ROLE_RECURSOS_HUMANOS: ["view_dashboard", "manage_users", "view_hr_reports"],
    }
}
