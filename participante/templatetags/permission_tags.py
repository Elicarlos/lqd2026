from django import template
from django.contrib.auth.models import Group
from participante.models import CardDinamico, Funcionalidade

register = template.Library()

@register.filter
def split(value, arg):
    """
    Retorna uma lista de strings separadas pelo argumento
    """
    return value.split(arg)

@register.filter
def pode_ver_card(user, card):
    """
    Verifica se o usuário pode ver um card específico
    """
    # Superusers sempre podem ver todos os cards ativos
    if user.is_superuser:
        return card.ativo
    
    if not card.ativo:
        return False
    
    # Se o card é apenas para admin/staff
    if card.apenas_admin_staff and not (user.is_superuser or user.is_staff):
        return False
    
    # Verificar grupos permitidos
    if card.grupos_permitidos.exists():
        user_groups = user.groups.all()
        if not any(grupo in card.grupos_permitidos.all() for grupo in user_groups):
            return False
    
    # Verificar usuários permitidos
    if card.usuarios_permitidos.exists():
        if user not in card.usuarios_permitidos.all():
            return False
    
    # Verificar usuários excluídos
    if card.usuarios_excluidos.exists():
        if user in card.usuarios_excluidos.all():
            return False
    
    return True

@register.filter
def pode_usar_funcionalidade(user, funcionalidade):
    """
    Verifica se o usuário pode usar uma funcionalidade específica
    """
    # Superusers sempre podem usar todas as funcionalidades ativas
    if user.is_superuser:
        return funcionalidade.ativo
    
    if not funcionalidade.ativo:
        return False
    
    # Verificar grupos permitidos
    if funcionalidade.grupos_permitidos.exists():
        user_groups = user.groups.all()
        if not any(grupo in funcionalidade.grupos_permitidos.all() for grupo in user_groups):
            return False
    
    # Verificar usuários permitidos
    if funcionalidade.usuarios_permitidos.exists():
        if user not in funcionalidade.usuarios_permitidos.all():
            return False
    
    # Verificar usuários excluídos
    if funcionalidade.usuarios_excluidos.exists():
        if user in funcionalidade.usuarios_excluidos.all():
            return False
    
    return True

@register.simple_tag
def get_cards_usuario(user):
    """
    Retorna todos os cards que o usuário pode ver
    """
    cards = CardDinamico.objects.filter(ativo=True).order_by('ordem')
    return [card for card in cards if pode_ver_card(user, card)]

@register.simple_tag
def get_funcionalidades_usuario(user):
    """
    Retorna todas as funcionalidades que o usuário pode usar
    """
    funcionalidades = Funcionalidade.objects.filter(ativo=True)
    return [func for func in funcionalidades if pode_usar_funcionalidade(user, func)]

@register.filter
def tem_grupo(user, grupo_nome):
    """
    Verifica se o usuário pertence a um grupo específico
    """
    return user.groups.filter(name=grupo_nome).exists()

@register.filter
def tem_qualquer_grupo(user, grupo_nomes):
    """
    Verifica se o usuário pertence a qualquer um dos grupos especificados
    """
    if isinstance(grupo_nomes, str):
        grupo_nomes = [nome.strip() for nome in grupo_nomes.split(',')]
    
    user_groups = user.groups.values_list('name', flat=True)
    return any(nome in user_groups for nome in grupo_nomes)

@register.filter
def tem_todos_grupos(user, grupo_nomes):
    """
    Verifica se o usuário pertence a todos os grupos especificados
    """
    if isinstance(grupo_nomes, str):
        grupo_nomes = [nome.strip() for nome in grupo_nomes.split(',')]
    
    user_groups = user.groups.values_list('name', flat=True)
    return all(nome in user_groups for nome in grupo_nomes)
