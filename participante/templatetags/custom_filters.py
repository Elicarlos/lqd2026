from datetime import timedelta

from django import template

register = template.Library()


@register.filter
def formatar_timedelta(td):
    """Formata um timedelta para o formato de horas."""
    if not td or not isinstance(td, timedelta):
        return "N/A"
    total_seconds = int(td.total_seconds())
    horas, resto = divmod(total_seconds, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{horas}:{minutos:02}:{segundos:02}"
