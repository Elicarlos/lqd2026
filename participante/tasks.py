from datetime import timedelta, datetime
from io import BytesIO
from re import sub

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.db.models import Q, F
from django.template.loader import render_to_string
from django.utils import timezone
from xhtml2pdf import pisa

from participante.models import RegistroJornada


def formatar_cpf(cpf):
    """Formata o CPF no formato XXX.XXX.XXX-XX."""
    cpf = sub(r"[^\d]", "", cpf)  # Remove todos os caracteres não numéricos
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf  # Re


def formatar_duracao(duracao):
    if not duracao or duracao.total_seconds() <= 0:
        return "N/A"

    total_seconds = int(duracao.total_seconds())
    horas, resto = divmod(total_seconds, 3600)
    minutos, segundos = divmod(resto, 60)
    
    # Se a duração for muito pequena (menos de 1 minuto), mostrar apenas segundos
    if total_seconds < 60:
        return f"00:00:{segundos:02}"
    
    return f"{horas:02}:{minutos:02}:{segundos:02}"


def total_horas_trabalhadas(user):
    registros = RegistroJornada.objects.filter(user=user).exclude(horario_fim=None)
    total = timedelta()
    for reg in registros:
        total += reg.calcular_duracao()
    return total


@shared_task
def gerar_pdf_batidas_task(user_id):
    User = get_user_model()
    user = User.objects.get(pk=user_id)

    # Consulta os registros
    registros = RegistroJornada.objects.filter(user=user).order_by("-horario_inicio")

    # Agrupa registros por usuário
    funcionarios = {}
    for registro in registros:
        user = registro.user
        if user not in funcionarios:
            funcionarios[user] = {
                "nome": (user.profile.nome or user.username).upper(),
                "cpf": user.profile.CPF or "N/A",
                "data_cadastro": (
                    user.profile.dataCadastro.strftime("%d/%m/%Y")
                    if user.profile.dataCadastro
                    else "N/A"
                ),
                "total_horas": timedelta(),
                "registros": [],
            }
        duracao = registro.calcular_duracao()
        if duracao and duracao.total_seconds() > 0:
            funcionarios[user]["total_horas"] += duracao
        registro.duracao_formatada = formatar_duracao(duracao)
        funcionarios[user]["registros"].append(registro)

    # Ordena funcionários alfabeticamente
    funcionarios_ordenados = sorted(funcionarios.values(), key=lambda x: x["nome"])

    # Cria o contexto para o template
    context = {
        "funcionarios": funcionarios_ordenados,
        "data_impressao": timezone.now().strftime("%d/%m/%Y"),
    }

    # Renderiza o template
    html = render_to_string("lojista/gerar_pdf_batidas_filtros.html", context)

    # Gera o PDF
    pdf_file = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_file)

    if pisa_status.err:
        raise Exception("Erro ao gerar PDF")

    return pdf_file.getvalue()


@shared_task
def finalizar_jornadas_inativas():
    agora = timezone.now()
    registros_abertos = RegistroJornada.objects.filter(horario_fim__isnull=True)

    for registro in registros_abertos:
        limite_inatividade = agora - timedelta(minutes=30)
        if registro.ultimo_update and registro.ultimo_update < limite_inatividade:
            # Verificar se o usuário ainda está logado
            if registro.user.is_authenticated:
                registro.horario_fim = agora
                registro.save()
                try:
                    registro.user.session_set.all().delete()  # Remove as sessões ativas
                    print(
                        f"Jornada finalizada e usuário {registro.user.username} deslogado."
                    )
                except AttributeError:
                    pass


@shared_task
def finalizar_jornadas_automaticas():
    """
    DESABILITADO: Finalização automática de jornadas
    Agora usa apenas o botão manual para superusuários/suporte
    """
    print("🔍 Finalização automática de jornadas DESABILITADA")
    print("   - Use o botão manual na página de gestão de jornadas")
    print("   - Disponível para superusuários e grupo Suporte")
    return
    
    # CÓDIGO COMENTADO - FINALIZAÇÃO AUTOMÁTICA DESABILITADA
    """
    from participante.models import JornadaColaborador
    from django.contrib.auth import logout
    from django.contrib.sessions.models import Session
    
    agora = timezone.now()
    hoje = agora.date()
    
    print(f"🔍 Verificando jornadas para finalização automática - {agora.strftime('%d/%m/%Y %H:%M')}")
    
    # Buscar todas as jornadas ativas (não finalizadas)
    jornadas_ativas = RegistroJornada.objects.filter(
        horario_fim__isnull=True,
        status='ATIVA'
    )
    
    for registro in jornadas_ativas:
        try:
            # Buscar a jornada atribuída ao colaborador
            jornada_atribuida = JornadaColaborador.get_jornada_ativa(registro.user)
            
            if not jornada_atribuida:
                print(f"⚠️ Usuário {registro.user.username} não tem jornada atribuída - finalizando com horário atual")
                registro.horario_fim = agora
                registro.status = 'FINALIZADA'
                registro.save()
                continue
            
            tipo_jornada = jornada_atribuida.tipo_jornada
            
            # Calcular horário limite (fim da jornada + tolerância)
            from datetime import datetime, time
            hora_fim_jornada = tipo_jornada.hora_fim
            tolerancia_minutos = tipo_jornada.tolerancia_saida
            
            # CORREÇÃO: Usar a data de início da jornada, não a data de hoje
            data_inicio_jornada = registro.horario_inicio.date()
            fim_jornada = datetime.combine(data_inicio_jornada, hora_fim_jornada)
            
            # Adicionar tolerância
            limite_final = fim_jornada + timedelta(minutes=tolerancia_minutos)
            
            # Se já passou do limite, finalizar a jornada
            if agora > limite_final:
                print(f"⏰ Finalizando jornada de {registro.user.username}")
                print(f"   - Horário fim jornada: {hora_fim_jornada}")
                print(f"   - Tolerância: {tolerancia_minutos} min")
                print(f"   - Limite final: {limite_final.strftime('%H:%M')}")
                print(f"   - Horário atual: {agora.strftime('%H:%M')}")
                
                # Finalizar a jornada
                registro.horario_fim = fim_jornada  # Usar o horário de fim da jornada, não o atual
                registro.status = 'FINALIZADA'
                registro.save()
                
                # Limpar posto de trabalho
                try:
                    from participante.views import limpar_posto_trabalho
                    limpar_posto_trabalho(registro.user)
                except:
                    pass
                
                # Deslogar o usuário
                try:
                    # Encontrar e deletar sessões ativas do usuário
                    sessions = Session.objects.filter(expire_date__gt=agora)
                    for session in sessions:
                        if session.get_decoded().get('_auth_user_id') == str(registro.user.id):
                            session.delete()
                            print(f"   - Sessão deletada para {registro.user.username}")
                except Exception as e:
                    print(f"   - Erro ao deletar sessão: {e}")
                
                print(f"✅ Jornada finalizada automaticamente para {registro.user.username}")
                
        except Exception as e:
            print(f"❌ Erro ao processar jornada de {registro.user.username}: {e}")
    
    print(f"🏁 Verificação de jornadas concluída - {timezone.now().strftime('%H:%M')}")
    """


@shared_task(rate_limit="6/m")
def email_boas_vindas_task(
    assunto,
    destinatario,
    corpo,
    from_email="postmaster@mg.nataldeluzcdl.com.br",
    reply_to="postmaster@mg.nataldeluzcdl.com.br",
):
    mail = EmailMessage(
        subject=assunto,
        from_email=from_email,
        to=[destinatario],
        body=corpo,
        headers={"Reply-To": reply_to},
    )
    mail.send()


@shared_task(rate_limit="6/m")
def email_recuperacao_senha(
    assunto,
    corpo,
    from_email,
    destinatario,
    reply_to="postmaster@mg.nataldeluzcdl.com.br",
):
    mail = EmailMessage(
        subject=assunto,
        body=corpo,
        from_email=from_email,
        to=destinatario,
        headers={"Reply-To": reply_to},
    )
    mail.send()


@shared_task(rate_limit="6/m")
def email_notificacao_task(
    assunto,
    destinatario,
    corpo,
    from_email="postmaster@mg.nataldeluzcdl.com.br",
    reply_to="postmaster@mg.nataldeluzcdl.com.br",
):
    mail = EmailMessage(
        subject=assunto,
        from_email=from_email,
        to=[destinatario],
        body=corpo,
        headers={"Reply-To": reply_to},
    )
    mail.send()


@shared_task
def gerar_pdf_batidas_filtros_task(filtros, user_id=None):
    try:
        print(f"TASK DEBUG: Iniciando geração de PDF com filtros: {filtros}")
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Extrai os filtros
        data_inicio = filtros.get("data_inicio", "")
        data_fim = filtros.get("data_fim", "")
        posto_trabalho_id = filtros.get("posto_trabalho_id", "")
        search_query = filtros.get("search_query", "")

        print(f"TASK DEBUG: Filtros extraídos - data_inicio: '{data_inicio}', data_fim: '{data_fim}', posto_trabalho_id: '{posto_trabalho_id}', search_query: '{search_query}'")

        if search_query.isdigit() and len(search_query) == 11:
            search_query = formatar_cpf(search_query)

        # Busca e ordena os registros - apenas registros válidos
        registros = RegistroJornada.objects.filter(
            horario_inicio__isnull=False,
            horario_fim__isnull=False
        ).exclude(
            horario_fim__lte=F('horario_inicio')  # Exclui registros onde fim <= início
        ).order_by(
            "user__profile__nome", "user__profile__CPF", "-horario_inicio"
        )
        print(f"TASK DEBUG: Total de registros antes dos filtros: {registros.count()}")

        # Aplica os filtros apenas se houver valores válidos
        if data_inicio and data_inicio.strip():
            try:
                data_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
                # Filtra registros que começaram na data de início ou depois
                registros = registros.filter(horario_inicio__date__gte=data_inicio)
                print(f"TASK DEBUG: Filtro data_inicio aplicado: {data_inicio}")
            except ValueError:
                print(f"TASK DEBUG: Erro ao converter data_inicio: {data_inicio}")
                pass

        if data_fim and data_fim.strip():
            try:
                data_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
                # Filtra registros que terminaram na data de fim ou antes
                registros = registros.filter(horario_fim__date__lte=data_fim)
                print(f"TASK DEBUG: Filtro data_fim aplicado: {data_fim}")
            except ValueError:
                print(f"TASK DEBUG: Erro ao converter data_fim: {data_fim}")
                pass

        if posto_trabalho_id and posto_trabalho_id.strip() and posto_trabalho_id != "None":
            registros = registros.filter(posto_trabalho_id=posto_trabalho_id)

        # Aplica o filtro de busca por CPF ou nome apenas se houver busca
        if search_query and search_query.strip():
            # Remove máscaras do CPF se for um CPF
            search_clean = search_query.strip()
            if search_clean.replace('.', '').replace('-', '').replace('_', '').isdigit() and len(search_clean.replace('.', '').replace('-', '').replace('_', '')) == 11:
                # É um CPF, remove máscaras
                search_clean = search_clean.replace('.', '').replace('-', '').replace('_', '')
                print(f"TASK DEBUG: CPF limpo: '{search_query}' → '{search_clean}'")
            
            registros_antes = registros.count()
            registros = registros.filter(
                Q(user__profile__CPF__icontains=search_clean)
                | Q(user__profile__nome__icontains=search_query)
            )
            registros_depois = registros.count()
            print(f"TASK DEBUG: Filtro search aplicado: '{search_query}' (limpo: '{search_clean}') - Registros: {registros_antes} → {registros_depois}")
        else:
            print(f"TASK DEBUG: Nenhum filtro de busca aplicado")

        # Obtém informações do usuário que gerou o relatório
        usuario_nome = "Sistema"
        if user_id:
            try:
                usuario = User.objects.get(id=user_id)
                try:
                    usuario_nome = (
                        usuario.profile.nome or usuario.get_full_name() or usuario.username
                    )
                except:
                    usuario_nome = usuario.username
            except User.DoesNotExist:
                pass

        # Data e hora atual
        agora = timezone.localtime(timezone.now())
        data_impressao = agora.strftime("%d/%m/%Y")
        hora_impressao = agora.strftime("%H:%M:%S")

        # Agrupa registros por usuário
        funcionarios = {}
        for registro in registros:
            user = registro.user
            if user not in funcionarios:
                # Trata caso onde usuário não tem profile
                try:
                    nome = user.profile.nome or user.username
                    cpf = user.profile.CPF or "N/A"
                    data_cadastro = (
                        user.profile.dataCadastro.strftime("%d/%m/%Y")
                        if user.profile.dataCadastro
                        else "N/A"
                    )
                except:
                    nome = user.username
                    cpf = "N/A"
                    data_cadastro = "N/A"
                
                funcionarios[user] = {
                    "nome": nome.upper(),
                    "cpf": cpf,
                    "data_cadastro": data_cadastro,
                    "total_horas": timedelta(),
                    "registros": [],
                }
            duracao = registro.calcular_duracao()
            if duracao and duracao.total_seconds() > 0:
                funcionarios[user]["total_horas"] += duracao
            registro.duracao_formatada = formatar_duracao(duracao)
            funcionarios[user]["registros"].append(registro)

        # Ordena funcionários alfabeticamente e filtra funcionários sem registros
        funcionarios_ordenados = [
            func for func in sorted(funcionarios.values(), key=lambda x: x["nome"])
            if len(func["registros"]) > 0
        ]
        
        print(f"TASK DEBUG: Total de funcionários encontrados: {len(funcionarios_ordenados)}")
        for func in funcionarios_ordenados:
            print(f"TASK DEBUG: Funcionário: {func['nome']} - CPF: {func['cpf']} - Registros: {len(func['registros'])}")

        # Cria o contexto para o template
        context = {
            "funcionarios": funcionarios_ordenados,
            "data_impressao": data_impressao,
            "hora_impressao": hora_impressao,
            "usuario_nome": usuario_nome,
        }

        print(f"TASK DEBUG: Contexto criado com {len(funcionarios_ordenados)} funcionários")

        # Renderiza o template
        html = render_to_string("lojista/gerar_pdf_batidas_filtros.html", context)
        print(f"TASK DEBUG: HTML gerado com {len(html)} caracteres")

        # Gera o PDF
        pdf_file = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_file)

        if pisa_status.err:
            raise Exception("Erro ao gerar PDF")

        pdf_data = pdf_file.getvalue()
        print(f"TASK DEBUG: PDF gerado com sucesso! Tamanho: {len(pdf_data)} bytes")
        return pdf_data
        
    except Exception as e:
        print(f"Erro na task gerar_pdf_batidas_filtros_task: {e}")
        import traceback
        traceback.print_exc()
        raise e
