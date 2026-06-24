from re import sub


def formatar_cpf(cpf):
    """Formata o CPF no formato XXX.XXX.XXX-XX."""
    cpf = sub(r"[^\d]", "", cpf)  # Remove todos os caracteres não numéricos
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf  # Retorna o CPF original se não tiver 11 dígitos


def formatar_duracao(duracao):
    if not duracao or duracao.total_seconds() <= 0:
        return "N/A"

    total_seconds = int(duracao.total_seconds())
    horas, resto = divmod(total_seconds, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{horas:02}:{minutos:02}:{segundos:02}"
