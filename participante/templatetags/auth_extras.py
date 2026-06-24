from datetime import timedelta

from django import template
from django.contrib.auth.models import Group

register = template.Library()


@register.filter(name="has_group")
def has_group(user, group_name):
    group = Group.objects.get(name=group_name)
    return True if group in user.groups.all() else False


@register.filter
def formatar_timedelta(td):
    """Formata um timedelta para o formato de horas."""
    if not td or not isinstance(td, timedelta):
        return "N/A"
    total_seconds = int(td.total_seconds())
    horas, resto = divmod(total_seconds, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{horas}:{minutos:02}:{segundos:02}"
