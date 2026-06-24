# services.py

from datetime import timedelta

from ..models import RegistroJornada


def calcular_horas_trabalhadas_diaria(operador, data):
    registros = RegistroJornada.objects.filter(user=operador, horario_inicio__date=data)

    total_horas = timedelta()
    for registro in registros:
        duracao = registro.calcular_duracao()
        if duracao:
            total_horas += duracao

    return total_horas
