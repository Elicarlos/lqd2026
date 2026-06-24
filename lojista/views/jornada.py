from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.core.paginator import Paginator
from django.db.models import Case, Exists, OuterRef, Q, When
from django.db import models
from django.http import (
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
    HttpResponseNotFound,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from cupom.models import Cupom
from participante.forms import ProfileEditForm, UserEditForm
from participante.models import (
    Campanha,
    DocumentoFiscal,
    PostoTrabalho,
    Profile,
    RegistroJornada,
    TipoJornada,
    JornadaColaborador,
    SystemRole,
    UserRole,
    URLTreinamento,
)
from participante.permissions import (
    get_user_dashboard_cards,
    get_cards_by_type,
    user_has_card_permission,
    is_operador,
    is_gerente,
    is_backoffice,
    is_supervisor,
    is_gerente_solve,
    is_recursos_humanos,
)
from lojista.filters import LojistaFilter
from lojista.forms import (
    LocalizacaoRegistrationForm,
    LojistaRegistrationForm,
    RamoAtividadeRegistrationForm,
)
from lojista.models import AdesaoLojista, Localizacao, Lojista, RamoAtividade
from participante.decorators import require_card_permission


from .utils import can_manage_journey_records

@login_required
@user_passes_test(can_manage_journey_records)
def jornadas_gestao(request):
    """
    Página principal de gestão de jornadas
    """
    
    # Buscar tipos de jornada
    tipos_jornada = TipoJornada.objects.filter(ativo=True).order_by('nome')
    
    # Buscar colaboradores com jornadas (apenas staff, não participantes)
    colaboradores_com_jornada = User.objects.filter(
        jornadas_atribuidas__ativo=True,
        is_staff=True
    ).distinct().order_by('username')
    
    # Buscar jornadas ativas (novo sistema) - apenas de colaboradores
    from participante.models import RegistroJornada
    jornadas_ativas_list = RegistroJornada.objects.filter(
        status='ATIVA',
        user__is_staff=True
    ).select_related('user', 'user__profile', 'posto_trabalho').order_by('-horario_inicio')
    
    # Buscar configurações de jornada (novo sistema)
    from participante.models import ConfiguracaoJornada
    configuracoes_jornada = ConfiguracaoJornada.objects.filter(
        ativo=True
    ).select_related('grupo').order_by('grupo__name')
    
    # Buscar exceções de jornada (novo sistema) - apenas de colaboradores
    from participante.models import ExcecaoJornada
    excecoes_jornada = ExcecaoJornada.objects.filter(
        ativo=True,
        usuario__is_staff=True
    ).select_related('usuario').order_by('-created_at')[:10]  # Últimas 10
    
    # Estatísticas (apenas colaboradores)
    total_tipos_jornada = tipos_jornada.count()
    total_colaboradores_com_jornada = colaboradores_com_jornada.count()
    total_colaboradores = User.objects.filter(
        is_active=True, 
        is_staff=True
    ).count()
    jornadas_ativas = jornadas_ativas_list.count()
    total_configuracoes = configuracoes_jornada.count()
    
    context = {
        'tipos_jornada': tipos_jornada,
        'colaboradores_com_jornada': colaboradores_com_jornada,
        'jornadas_ativas_list': jornadas_ativas_list,
        'configuracoes_jornada': configuracoes_jornada,
        'excecoes_jornada': excecoes_jornada,
        'total_tipos_jornada': total_tipos_jornada,
        'total_colaboradores_com_jornada': total_colaboradores_com_jornada,
        'total_colaboradores': total_colaboradores,
        'jornadas_ativas': jornadas_ativas,
        'total_configuracoes': total_configuracoes,
        'page_title': 'Gestão de Jornadas',
    }
    
    return render(request, 'lojista/jornadas_gestao.html', context)


@login_required
@user_passes_test(can_manage_journey_records)
def tipos_jornada_list(request):
    """
    Lista os tipos de jornada existentes
    """
    
    tipos = TipoJornada.objects.all().order_by('nome')
    
    # Paginação
    paginator = Paginator(tipos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'page_title': 'Tipos de Jornada',
    }
    
    return render(request, 'lojista/tipos_jornada_list.html', context)


@login_required
@user_passes_test(can_manage_journey_records)
def tipo_jornada_create(request):
    """
    Criar novo tipo de jornada
    """
    
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        hora_inicio = request.POST.get('hora_inicio')
        hora_fim = request.POST.get('hora_fim')
        dias_semana = request.POST.getlist('dias_semana')
        tolerancia_entrada = request.POST.get('tolerancia_entrada', 15)
        tolerancia_saida = request.POST.get('tolerancia_saida', 15)
        ativo = request.POST.get('ativo') == 'on'
        
        # Validações
        if not nome:
            messages.error(request, "Nome da jornada é obrigatório.")
        elif not hora_inicio or not hora_fim:
            messages.error(request, "Horários de início e fim são obrigatórios.")
        elif not dias_semana:
            messages.error(request, "Selecione pelo menos um dia da semana.")
        else:
            try:
                # Converter dias da semana para inteiros
                dias_semana_int = [int(dia) for dia in dias_semana]
                
                # Criar o tipo de jornada
                tipo_jornada = TipoJornada.objects.create(
                    nome=nome,
                    hora_inicio=hora_inicio,
                    hora_fim=hora_fim,
                    dias_semana=dias_semana_int,
                    tolerancia_entrada=int(tolerancia_entrada),
                    tolerancia_saida=int(tolerancia_saida),
                    ativo=ativo
                )
                
                messages.success(request, f"Tipo de jornada '{nome}' criado com sucesso!")
                return redirect('lojista:tipos_jornada_list')
                
            except Exception as e:
                messages.error(request, f"Erro ao criar jornada: {str(e)}")
    
    # Dias da semana para o formulário
    dias_semana_choices = [
        (1, 'Segunda-feira'),
        (2, 'Terça-feira'),
        (3, 'Quarta-feira'),
        (4, 'Quinta-feira'),
        (5, 'Sexta-feira'),
        (6, 'Sábado'),
        (7, 'Domingo'),
    ]
    
    context = {
        'dias_semana_choices': dias_semana_choices,
        'page_title': 'Criar Tipo de Jornada',
    }
    
    return render(request, 'lojista/tipo_jornada_form.html', context)


@login_required
@user_passes_test(can_manage_journey_records)
def tipo_jornada_edit(request, pk):
    """
    Editar tipo de jornada existente
    """
    
    tipo_jornada = get_object_or_404(TipoJornada, pk=pk)
    
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        hora_inicio = request.POST.get('hora_inicio')
        hora_fim = request.POST.get('hora_fim')
        dias_semana = request.POST.getlist('dias_semana')
        tolerancia_entrada = request.POST.get('tolerancia_entrada', 15)
        tolerancia_saida = request.POST.get('tolerancia_saida', 15)
        ativo = request.POST.get('ativo') == 'on'
        
        # Validações
        if not nome:
            messages.error(request, "Nome da jornada é obrigatório.")
        elif not hora_inicio or not hora_fim:
            messages.error(request, "Horários de início e fim são obrigatórios.")
        elif not dias_semana:
            messages.error(request, "Selecione pelo menos um dia da semana.")
        else:
            try:
                # Converter dias da semana para inteiros
                dias_semana_int = [int(dia) for dia in dias_semana]
                
                # Atualizar o tipo de jornada
                tipo_jornada.nome = nome
                tipo_jornada.hora_inicio = hora_inicio
                tipo_jornada.hora_fim = hora_fim
                tipo_jornada.dias_semana = dias_semana_int
                tipo_jornada.tolerancia_entrada = int(tolerancia_entrada)
                tipo_jornada.tolerancia_saida = int(tolerancia_saida)
                tipo_jornada.ativo = ativo
                tipo_jornada.save()
                
                messages.success(request, f"Tipo de jornada '{nome}' atualizado com sucesso!")
                return redirect('lojista:tipos_jornada_list')
                
            except Exception as e:
                messages.error(request, f"Erro ao atualizar jornada: {str(e)}")
    
    # Dias da semana para o formulário
    dias_semana_choices = [
        (1, 'Segunda-feira'),
        (2, 'Terça-feira'), 
        (3, 'Quarta-feira'),
        (4, 'Quinta-feira'),
        (5, 'Sexta-feira'),
        (6, 'Sábado'),
        (7, 'Domingo'),
    ]
    
    context = {
        'tipo_jornada': tipo_jornada,
        'dias_semana_choices': dias_semana_choices,
        'page_title': f'Editar {tipo_jornada.nome}',
    }
    
    return render(request, 'lojista/tipo_jornada_form.html', context)


@login_required
@user_passes_test(can_manage_journey_records)
def jornadas_colaboradores_list(request):
    """
    Lista jornadas atribuídas a colaboradores
    """
    
    # Filtros
    colaborador_filter = request.GET.get('colaborador', '')
    jornada_filter = request.GET.get('jornada', '')
    ativo_filter = request.GET.get('ativo', 'all')
    
    # Query base - apenas jornadas de colaboradores (staff)
    jornadas = JornadaColaborador.objects.select_related(
        'colaborador', 'tipo_jornada'
    ).filter(
        colaborador__is_staff=True
    ).order_by('-data_inicio')
    
    # Aplicar filtros
    if colaborador_filter:
        jornadas = jornadas.filter(
            Q(colaborador__username__icontains=colaborador_filter) |
            Q(colaborador__first_name__icontains=colaborador_filter) |
            Q(colaborador__last_name__icontains=colaborador_filter) |
            Q(colaborador__profile__CPF__icontains=colaborador_filter) |
            Q(colaborador__profile__nome__icontains=colaborador_filter)
        )
    
    if jornada_filter:
        jornadas = jornadas.filter(tipo_jornada__nome__icontains=jornada_filter)
    
    if ativo_filter == 'true':
        jornadas = jornadas.filter(ativo=True)
    elif ativo_filter == 'false':
        jornadas = jornadas.filter(ativo=False)
    
    # Paginação
    paginator = Paginator(jornadas, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Buscar colaboradores e tipos para os filtros
    colaboradores = User.objects.filter(
        jornadas_atribuidas__isnull=False,
        is_staff=True
    ).distinct().order_by('username')
    
    tipos_jornada = TipoJornada.objects.filter(ativo=True).order_by('nome')
    
    context = {
        'page_obj': page_obj,
        'colaboradores': colaboradores,
        'tipos_jornada': tipos_jornada,
        'colaborador_filter': colaborador_filter,
        'jornada_filter': jornada_filter,
        'ativo_filter': ativo_filter,
        'page_title': 'Jornadas dos Colaboradores',
    }
    
    return render(request, 'lojista/jornadas_colaboradores_list.html', context)


@login_required
@user_passes_test(can_manage_journey_records)
def jornada_colaborador_create(request):
    """
    Atribuir jornada a um colaborador
    """
    
    if request.method == 'POST':
        colaborador_id = request.POST.get('colaborador')
        tipo_jornada_id = request.POST.get('tipo_jornada')
        data_inicio = request.POST.get('data_inicio')
        data_fim = request.POST.get('data_fim')
        observacoes = request.POST.get('observacoes', '').strip()
        ativo = request.POST.get('ativo') == 'on'
        
        # Validações
        if not colaborador_id or not tipo_jornada_id or not data_inicio:
            messages.error(request, "Colaborador, tipo de jornada e data de início são obrigatórios.")
        else:
            try:
                colaborador = User.objects.get(pk=colaborador_id)
                tipo_jornada = TipoJornada.objects.get(pk=tipo_jornada_id)
                
                # Verificar se já existe jornada para este colaborador na mesma data
                existing = JornadaColaborador.objects.filter(
                    colaborador=colaborador,
                    data_inicio=data_inicio
                ).first()
                
                # Verificar se o colaborador tem jornadas ativas ou incompletas
                from datetime import date
                
                hoje = date.today()
                
                # Verificar jornadas ativas (sem data_fim ou data_fim > hoje)
                jornadas_ativas = JornadaColaborador.objects.filter(
                    colaborador=colaborador,
                    ativo=True
                ).filter(
                    models.Q(data_fim__isnull=True) | models.Q(data_fim__gte=hoje)
                ).exclude(id=existing.id if existing else None)
                
                # Verificar registros de jornada não finalizados
                registros_nao_finalizados = RegistroJornada.objects.filter(
                    user=colaborador,
                    status='ATIVA'
                ).exists()
                
                if jornadas_ativas.exists():
                    messages.error(
                        request,
                        f"Não é possível atribuir jornada para {colaborador.username}. "
                        f"O colaborador já possui {jornadas_ativas.count()} jornada(s) ativa(s) "
                        f"que ainda não foram finalizadas."
                    )
                elif registros_nao_finalizados:
                    messages.error(
                        request,
                        f"Não é possível atribuir jornada para {colaborador.username}. "
                        f"O colaborador possui registros de jornada não finalizados. "
                        f"É necessário finalizar a jornada atual antes de atribuir uma nova."
                    )
                elif existing:
                    # Atualizar jornada existente
                    existing.tipo_jornada = tipo_jornada
                    existing.data_fim = data_fim if data_fim else None
                    existing.observacoes = observacoes
                    existing.ativo = ativo
                    existing.save()
                    
                    messages.success(
                        request,
                        f"Jornada de {colaborador.username} atualizada para '{tipo_jornada.nome}' com sucesso!"
                    )
                else:
                    # Criar nova atribuição
                    jornada_colaborador = JornadaColaborador.objects.create(
                        colaborador=colaborador,
                        tipo_jornada=tipo_jornada,
                        data_inicio=data_inicio,
                        data_fim=data_fim if data_fim else None,
                        observacoes=observacoes,
                        ativo=ativo
                    )
                    
                    messages.success(
                        request,
                        f"Jornada '{tipo_jornada.nome}' atribuída a {colaborador.username} com sucesso!"
                    )
                
                return redirect('lojista:jornadas_colaboradores_list')
                    
            except (User.DoesNotExist, TipoJornada.DoesNotExist) as e:
                messages.error(request, f"Erro: {str(e)}")
            except Exception as e:
                messages.error(request, f"Erro ao criar atribuição: {str(e)}")
    
    # Buscar colaboradores e tipos de jornada
    colaboradores = User.objects.filter(is_active=True, is_staff=True).select_related('profile').order_by('username')
    tipos_jornada = TipoJornada.objects.filter(ativo=True).order_by('nome')
    
    # Verificar status dos colaboradores para exibição
    from datetime import date
    
    hoje = date.today()
    colaboradores_com_status = []
    
    for colaborador in colaboradores:
        # Verificar jornadas ativas
        jornadas_ativas = JornadaColaborador.objects.filter(
            colaborador=colaborador,
            ativo=True
        ).filter(
            models.Q(data_fim__isnull=True) | models.Q(data_fim__gte=hoje)
        )
        
        # Verificar registros não finalizados
        registros_nao_finalizados = RegistroJornada.objects.filter(
            user=colaborador,
            status='ATIVA'
        ).exists()
        
        status = 'disponivel'
        status_texto = 'Disponível para nova jornada'
        
        if registros_nao_finalizados:
            status = 'jornada_ativa'
            status_texto = 'Jornada ativa (não finalizada)'
        elif jornadas_ativas.exists():
            status = 'jornada_atribuida'
            status_texto = f'{jornadas_ativas.count()} jornada(s) ativa(s)'
        
        colaboradores_com_status.append({
            'colaborador': colaborador,
            'status': status,
            'status_texto': status_texto,
            'jornadas_ativas_count': jornadas_ativas.count(),
            'tem_registro_ativo': registros_nao_finalizados
        })
    
    context = {
        'colaboradores': colaboradores_com_status,
        'tipos_jornada': tipos_jornada,
        'page_title': 'Atribuir Jornada a Colaborador',
    }
    
    return render(request, 'lojista/jornada_colaborador_form.html', context)


@login_required
@user_passes_test(can_manage_journey_records)
def jornada_colaborador_edit(request, jornada_id):
    """
    Editar jornada atribuída a um colaborador
    """
    
    # Buscar a jornada
    try:
        jornada = JornadaColaborador.objects.get(pk=jornada_id)
    except JornadaColaborador.DoesNotExist:
        messages.error(request, "Jornada não encontrada.")
        return redirect('lojista:jornadas_colaboradores_list')
    
    if request.method == 'POST':
        tipo_jornada_id = request.POST.get('tipo_jornada')
        data_inicio = request.POST.get('data_inicio')
        data_fim = request.POST.get('data_fim')
        observacoes = request.POST.get('observacoes', '').strip()
        ativo = request.POST.get('ativo') == 'on'
        
        # Validações
        if not tipo_jornada_id or not data_inicio:
            messages.error(request, "Tipo de jornada e data de início são obrigatórios.")
        else:
            try:
                tipo_jornada = TipoJornada.objects.get(pk=tipo_jornada_id)
                
                # Atualizar jornada
                jornada.tipo_jornada = tipo_jornada
                jornada.data_inicio = data_inicio
                jornada.data_fim = data_fim if data_fim else None
                jornada.observacoes = observacoes
                jornada.ativo = ativo
                jornada.save()
                
                messages.success(
                    request,
                    f"Jornada de {jornada.colaborador.username} atualizada com sucesso!"
                )
                return redirect('lojista:jornadas_colaboradores_list')
                    
            except TipoJornada.DoesNotExist:
                messages.error(request, "Tipo de jornada não encontrado.")
            except Exception as e:
                messages.error(request, f"Erro ao atualizar jornada: {str(e)}")
    
    # Buscar tipos de jornada
    tipos_jornada = TipoJornada.objects.filter(ativo=True).order_by('nome')
    
    context = {
        'jornada': jornada,
        'tipos_jornada': tipos_jornada,
        'page_title': 'Editar Jornada de Colaborador',
    }
    
    return render(request, 'lojista/jornada_colaborador_edit.html', context)


@login_required
@user_passes_test(can_manage_journey_records)
def jornada_colaborador_toggle_status(request, jornada_id):
    """
    Ativar/Inativar jornada atribuída a um colaborador via AJAX
    """
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)
    
    try:
        jornada = JornadaColaborador.objects.get(pk=jornada_id)
        
        # Alternar status
        jornada.ativo = not jornada.ativo
        jornada.save()
        
        status_texto = 'ativada' if jornada.ativo else 'inativada'
        
        return JsonResponse({
            'success': True, 
            'message': f'Jornada {status_texto} com sucesso!',
            'ativo': jornada.ativo
        })
        
    except JornadaColaborador.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Jornada não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=500)


@login_required
@user_passes_test(can_manage_journey_records)
def configuracoes_jornada_list(request):
    """
    Lista configurações de jornada por grupo
    """
    
    # Buscar configurações
    from participante.models import ConfiguracaoJornada
    configuracoes = ConfiguracaoJornada.objects.select_related('grupo').order_by('grupo__name')
    
    # Paginação
    paginator = Paginator(configuracoes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'page_title': 'Configurações de Jornada',
    }
    
    return render(request, 'lojista/configuracoes_jornada_list.html', context)


@login_required
@user_passes_test(can_manage_journey_records)
def configuracao_jornada_create(request):
    """
    Criar nova configuração de jornada
    """
    
    if request.method == 'POST':
        from participante.models import ConfiguracaoJornada
        
        grupo_id = request.POST.get('grupo')
        requer_jornada = request.POST.get('requer_jornada') == 'on'
        jornada_flexivel = request.POST.get('jornada_flexivel') == 'on'
        tolerancia_entrada = request.POST.get('tolerancia_entrada', 15)
        tolerancia_saida = request.POST.get('tolerancia_saida', 15)
        ativo = request.POST.get('ativo') == 'on'
        
        # Validações
        if not grupo_id:
            messages.error(request, "Grupo é obrigatório.")
        else:
            try:
                grupo = Group.objects.get(pk=grupo_id)
                
                # Verificar se já existe configuração para este grupo
                existing = ConfiguracaoJornada.objects.filter(grupo=grupo).first()
                if existing:
                    messages.error(request, f"Já existe uma configuração para o grupo '{grupo.name}'.")
                else:
                    # Criar configuração
                    configuracao = ConfiguracaoJornada.objects.create(
                        grupo=grupo,
                        requer_jornada=requer_jornada,
                        jornada_flexivel=jornada_flexivel,
                        tolerancia_entrada=tolerancia_entrada,
                        tolerancia_saida=tolerancia_saida,
                        ativo=ativo
                    )
                    
                    messages.success(
                        request,
                        f"Configuração criada com sucesso para o grupo '{grupo.name}'!"
                    )
                    return redirect('lojista:configuracoes_jornada_list')
                    
            except Group.DoesNotExist:
                messages.error(request, "Grupo não encontrado.")
            except Exception as e:
                messages.error(request, f"Erro ao criar configuração: {str(e)}")
    
    # Buscar grupos disponíveis
    grupos = Group.objects.all().order_by('name')
    
    context = {
        'grupos': grupos,
        'page_title': 'Nova Configuração de Jornada',
    }
    
    return render(request, 'lojista/configuracao_jornada_form.html', context)


@login_required
@user_passes_test(can_manage_journey_records)
def configuracao_jornada_edit(request, config_id):
    """
    Editar configuração de jornada
    """
    
    # Buscar configuração
    from participante.models import ConfiguracaoJornada
    try:
        configuracao = ConfiguracaoJornada.objects.get(pk=config_id)
    except ConfiguracaoJornada.DoesNotExist:
        messages.error(request, "Configuração não encontrada.")
        return redirect('lojista:configuracoes_jornada_list')
    
    if request.method == 'POST':
        requer_jornada = request.POST.get('requer_jornada') == 'on'
        jornada_flexivel = request.POST.get('jornada_flexivel') == 'on'
        tolerancia_entrada = request.POST.get('tolerancia_entrada', 15)
        tolerancia_saida = request.POST.get('tolerancia_saida', 15)
        ativo = request.POST.get('ativo') == 'on'
        
        try:
            # Atualizar configuração
            configuracao.requer_jornada = requer_jornada
            configuracao.jornada_flexivel = jornada_flexivel
            configuracao.tolerancia_entrada = tolerancia_entrada
            configuracao.tolerancia_saida = tolerancia_saida
            configuracao.ativo = ativo
            configuracao.save()
            
            messages.success(
                request,
                f"Configuração atualizada com sucesso para o grupo '{configuracao.grupo.name}'!"
            )
            return redirect('lojista:configuracoes_jornada_list')
                
        except Exception as e:
            messages.error(request, f"Erro ao atualizar configuração: {str(e)}")
    
    context = {
        'configuracao': configuracao,
        'page_title': 'Editar Configuração de Jornada',
    }
    
    return render(request, 'lojista/configuracao_jornada_edit.html', context)


@login_required
@user_passes_test(can_manage_journey_records)
def configuracao_jornada_toggle_status(request, config_id):
    """
    Ativar/Inativar configuração de jornada via AJAX
    """
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)
    
    try:
        from participante.models import ConfiguracaoJornada
        configuracao = ConfiguracaoJornada.objects.get(pk=config_id)
        
        # Alternar status
        configuracao.ativo = not configuracao.ativo
        configuracao.save()
        
        status_texto = 'ativada' if configuracao.ativo else 'inativada'
        
        return JsonResponse({
            'success': True, 
            'message': f'Configuração {status_texto} com sucesso!',
            'ativo': configuracao.ativo
        })
        
    except ConfiguracaoJornada.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Configuração não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=500)


@login_required
@user_passes_test(can_manage_journey_records)
def excecoes_jornada_list(request):
    """
    Lista exceções de jornada
    """
    
    # Buscar exceções
    from participante.models import ExcecaoJornada
    excecoes = ExcecaoJornada.objects.select_related('usuario', 'created_by').order_by('-created_at')
    
    # Filtros
    usuario_filter = request.GET.get('usuario', '')
    tipo_filter = request.GET.get('tipo', '')
    ativo_filter = request.GET.get('ativo', 'all')
    
    if usuario_filter:
        excecoes = excecoes.filter(
            models.Q(usuario__username__icontains=usuario_filter) |
            models.Q(usuario__first_name__icontains=usuario_filter) |
            models.Q(usuario__last_name__icontains=usuario_filter)
        )
    
    if tipo_filter:
        excecoes = excecoes.filter(tipo=tipo_filter)
    
    if ativo_filter != 'all':
        excecoes = excecoes.filter(ativo=ativo_filter == 'true')
    
    # Paginação
    paginator = Paginator(excecoes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'usuario_filter': usuario_filter,
        'tipo_filter': tipo_filter,
        'ativo_filter': ativo_filter,
        'page_title': 'Exceções de Jornada',
    }
    
    return render(request, 'lojista/excecoes_jornada_list.html', context)


@login_required
@user_passes_test(can_manage_journey_records)
def excecao_jornada_create(request):
    """
    Criar nova exceção de jornada
    """
    
    if request.method == 'POST':
        from participante.models import ExcecaoJornada
        
        usuario_id = request.POST.get('usuario')
        tipo = request.POST.get('tipo')
        data_inicio = request.POST.get('data_inicio')
        data_fim = request.POST.get('data_fim')
        horario_inicio = request.POST.get('horario_inicio')
        horario_fim = request.POST.get('horario_fim')
        justificativa = request.POST.get('justificativa', '').strip()
        ativo = request.POST.get('ativo') == 'on'
        
        # Validações
        if not usuario_id or not tipo or not data_inicio or not justificativa:
            messages.error(request, "Usuário, tipo, data de início e justificativa são obrigatórios.")
        else:
            try:
                usuario = User.objects.get(pk=usuario_id)
                
                # Criar exceção
                excecao = ExcecaoJornada.objects.create(
                    usuario=usuario,
                    tipo=tipo,
                    data_inicio=data_inicio,
                    data_fim=data_fim if data_fim else None,
                    horario_inicio=horario_inicio if horario_inicio else None,
                    horario_fim=horario_fim if horario_fim else None,
                    justificativa=justificativa,
                    ativo=ativo,
                    created_by=request.user
                )
                
                messages.success(
                    request,
                    f"Exceção criada com sucesso para {usuario.username}!"
                )
                return redirect('lojista:excecoes_jornada_list')
                    
            except User.DoesNotExist:
                messages.error(request, "Usuário não encontrado.")
            except Exception as e:
                messages.error(request, f"Erro ao criar exceção: {str(e)}")
    
    # Buscar usuários disponíveis (apenas staff)
    usuarios = User.objects.filter(is_active=True, is_staff=True).order_by('username')
    
    # Tipos de exceção
    from participante.models import ExcecaoJornada
    tipos_excecao = ExcecaoJornada.TIPO_CHOICES
    
    context = {
        'usuarios': usuarios,
        'tipos_excecao': tipos_excecao,
        'page_title': 'Nova Exceção de Jornada',
    }
    
    return render(request, 'lojista/excecao_jornada_form.html', context)


@login_required
@user_passes_test(can_manage_journey_records)
def excecao_jornada_edit(request, excecao_id):
    """
    Editar exceção de jornada
    """
    
    # Buscar exceção
    from participante.models import ExcecaoJornada
    try:
        excecao = ExcecaoJornada.objects.get(pk=excecao_id)
    except ExcecaoJornada.DoesNotExist:
        messages.error(request, "Exceção não encontrada.")
        return redirect('lojista:excecoes_jornada_list')
    
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        data_inicio = request.POST.get('data_inicio')
        data_fim = request.POST.get('data_fim')
        horario_inicio = request.POST.get('horario_inicio')
        horario_fim = request.POST.get('horario_fim')
        justificativa = request.POST.get('justificativa', '').strip()
        ativo = request.POST.get('ativo') == 'on'
        
        # Validações
        if not tipo or not data_inicio or not justificativa:
            messages.error(request, "Tipo, data de início e justificativa são obrigatórios.")
        else:
            try:
                # Atualizar exceção
                excecao.tipo = tipo
                excecao.data_inicio = data_inicio
                excecao.data_fim = data_fim if data_fim else None
                excecao.horario_inicio = horario_inicio if horario_inicio else None
                excecao.horario_fim = horario_fim if horario_fim else None
                excecao.justificativa = justificativa
                excecao.ativo = ativo
                excecao.save()
                
                messages.success(
                    request,
                    f"Exceção atualizada com sucesso para {excecao.usuario.username}!"
                )
                return redirect('lojista:excecoes_jornada_list')
                    
            except Exception as e:
                messages.error(request, f"Erro ao atualizar exceção: {str(e)}")
    
    # Tipos de exceção
    tipos_excecao = ExcecaoJornada.TIPO_CHOICES
    
    context = {
        'excecao': excecao,
        'tipos_excecao': tipos_excecao,
        'page_title': 'Editar Exceção de Jornada',
    }
    
    return render(request, 'lojista/excecao_jornada_edit.html', context)


@login_required
@user_passes_test(can_manage_journey_records)
def excecao_jornada_toggle_status(request, excecao_id):
    """
    Ativar/Inativar exceção de jornada via AJAX
    """
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)
    
    try:
        from participante.models import ExcecaoJornada
        excecao = ExcecaoJornada.objects.get(pk=excecao_id)
        
        # Alternar status
        excecao.ativo = not excecao.ativo
        excecao.save()
        
        status_texto = 'ativada' if excecao.ativo else 'inativada'
        
        return JsonResponse({
            'success': True, 
            'message': f'Exceção {status_texto} com sucesso!',
            'ativo': excecao.ativo
        })
        
    except ExcecaoJornada.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Exceção não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=500)


@login_required
@user_passes_test(can_manage_journey_records)
def finalizar_jornadas_automaticas_manual(request):
    """
    Finaliza jornadas automaticamente (botão manual para usuários autorizados)
    """
    
    if request.method == "POST":
        try:
            from participante.models import RegistroJornada, JornadaColaborador
            from django.contrib.sessions.models import Session
            from datetime import datetime, time, timedelta
            from django.utils import timezone
            
            agora = timezone.now()
            jornadas_finalizadas = 0
            usuarios_deslogados = 0
            
            print(f"🔍 Executando finalização manual de jornadas - {agora.strftime('%d/%m/%Y %H:%M')}")
            
            # Buscar todas as jornadas ativas
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
                        jornadas_finalizadas += 1
                        usuarios_deslogados += 1
                        continue
                    
                    tipo_jornada = jornada_atribuida.tipo_jornada
                    
                    # Calcular horário limite (fim da jornada + tolerância)
                    hora_fim_jornada = tipo_jornada.hora_fim
                    tolerancia_minutos = tipo_jornada.tolerancia_saida
                    
                    # CORREÇÃO: Usar a data de início da jornada, não a data de hoje
                    data_inicio_jornada = registro.horario_inicio.date()
                    fim_jornada = datetime.combine(data_inicio_jornada, hora_fim_jornada)
                    
                    # Adicionar tolerância
                    limite_final = fim_jornada + timedelta(minutes=tolerancia_minutos)
                    
                    # Se já passou do limite, finalizar a jornada
                    # CORREÇÃO: Usar timezone-aware para comparação
                    from django.utils import timezone
                    limite_final_aware = timezone.make_aware(limite_final)
                    
                    if agora > limite_final_aware:
                        print(f"⏰ Finalizando jornada de {registro.user.username}")
                        print(f"   - Data início: {data_inicio_jornada}")
                        print(f"   - Horário fim jornada: {hora_fim_jornada}")
                        print(f"   - Tolerância: {tolerancia_minutos} min")
                        print(f"   - Limite final: {limite_final_aware.strftime('%d/%m/%Y %H:%M')}")
                        print(f"   - Horário atual: {agora.strftime('%d/%m/%Y %H:%M')}")
                        
                        # Finalizar a jornada usando o método do modelo
                        registro.horario_fim = timezone.make_aware(fim_jornada)
                        registro.finalizar(finalizada_por=request.user, deslogar_usuario=True)
                        jornadas_finalizadas += 1
                        usuarios_deslogados += 1
                        
                        # Limpar posto de trabalho
                        try:
                            from participante.views import limpar_posto_trabalho
                            limpar_posto_trabalho(registro.user)
                        except Exception as e:
                            print(f"   - Erro ao limpar posto: {e}")
                        
                        print(f"✅ Jornada finalizada para {registro.user.username}")
                        
                except Exception as e:
                    print(f"❌ Erro ao processar jornada de {registro.user.username}: {e}")
            
            print(f"🏁 Finalização manual concluída - {jornadas_finalizadas} jornadas finalizadas (usuários deslogados automaticamente)")
            
            messages.success(
                request, 
                f"Finalização automática executada! {jornadas_finalizadas} jornadas finalizadas, {usuarios_deslogados} usuários deslogados."
            )
            
            # Log da ação
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"Finalização manual de jornadas executada por {request.user.username}: "
                f"{jornadas_finalizadas} jornadas finalizadas, {usuarios_deslogados} usuários deslogados"
            )
            
        except Exception as e:
            messages.error(
                request, 
                f"Erro ao executar finalização automática: {str(e)}"
            )
            
            # Log do erro
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Erro na finalização manual por {request.user.username}: {str(e)}"
            )
    
    return redirect('lojista:jornadas_gestao')


@user_passes_test(can_manage_journey_records)
def gestao_registros_jornada(request):
    """
    Gestão completa de registros de jornada
    - Visualizar todos os registros
    - Editar horários
    - Finalizar jornadas esquecidas
    - Gerenciar status
    
    Permissões: superuser, staff, grupo 'Suporte', grupo 'Gerente Solve'
    Tags: gestao, jornada, registros, rh
    """
    from participante.models import RegistroJornada, Profile, PostoTrabalho
    from django.db.models import Q
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    # Filtros
    status_filter = request.GET.get('status', '')
    colaborador_filter = request.GET.get('colaborador', '')
    posto_filter = request.GET.get('posto', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    apenas_ativas = request.GET.get('apenas_ativas', '') == 'on'

    # Normalização de CPF informado no filtro (aceita com ou sem máscara)
    cpf_masked_from_digits = None
    if colaborador_filter:
        digits_only = ''.join(ch for ch in colaborador_filter if ch.isdigit())
        if len(digits_only) == 11:
            cpf_masked_from_digits = f"{digits_only[0:3]}.{digits_only[3:6]}.{digits_only[6:9]}-{digits_only[9:11]}"
    
    # Buscar registros apenas de colaboradores (is_staff e is_colaborador)
    registros = RegistroJornada.objects.select_related(
        'user__profile', 'posto_trabalho'
    ).filter(
        user__is_staff=True,
        user__profile__is_colaborador=True
    ).order_by('user__id', 'horario_inicio')
    
    # Aplicar filtros
    if status_filter:
        registros = registros.filter(status=status_filter)
    
    if colaborador_filter:
        cpf_term = cpf_masked_from_digits or colaborador_filter
        registros = registros.filter(
            Q(user__first_name__icontains=colaborador_filter) |
            Q(user__last_name__icontains=colaborador_filter) |
            Q(user__username__icontains=colaborador_filter) |
            Q(user__profile__CPF__icontains=cpf_term) |
            Q(user__profile__nome__icontains=colaborador_filter)
        )
    
    if posto_filter:
        registros = registros.filter(posto_trabalho__id=posto_filter)
    
    # Validação e aplicação de intervalo de datas (corrige se invertido)
    data_inicio_dt = None
    data_fim_dt = None
    if data_inicio:
        try:
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except ValueError:
            data_inicio_dt = None
    if data_fim:
        try:
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except ValueError:
            data_fim_dt = None

    if data_inicio_dt and data_fim_dt and data_inicio_dt > data_fim_dt:
        # corrige ordem invertida
        data_inicio_dt, data_fim_dt = data_fim_dt, data_inicio_dt
    
    if data_inicio_dt:
        registros = registros.filter(horario_inicio__date__gte=data_inicio_dt)
    if data_fim_dt:
        registros = registros.filter(horario_inicio__date__lte=data_fim_dt)
    
    if apenas_ativas:
        registros = registros.filter(status='ATIVA')
    
    # Paginação
    from django.core.paginator import Paginator
    paginator = Paginator(registros, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estatísticas
    total_registros = registros.count()
    registros_ativos = registros.filter(status='ATIVA').count()
    registros_finalizados = registros.filter(status='FINALIZADA').count()
    registros_pausados = registros.filter(status='PAUSA').count()
    
    # Dados para filtros - apenas colaboradores
    colaboradores = Profile.objects.filter(
        is_colaborador=True,
        user__is_staff=True
    ).order_by('user__first_name')
    postos = PostoTrabalho.objects.all().order_by('nome')
    
    context = {
        'page_obj': page_obj,
        'total_registros': total_registros,
        'registros_ativos': registros_ativos,
        'registros_finalizados': registros_finalizados,
        'registros_pausados': registros_pausados,
        'colaboradores': colaboradores,
        'postos': postos,
        'status_filter': status_filter,
        'colaborador_filter': colaborador_filter,
        'posto_filter': posto_filter,
        'data_inicio': data_inicio_dt.strftime('%Y-%m-%d') if data_inicio_dt else data_inicio,
        'data_fim': data_fim_dt.strftime('%Y-%m-%d') if data_fim_dt else data_fim,
        'apenas_ativas': apenas_ativas,
        'has_filters': bool(status_filter or colaborador_filter or posto_filter or data_inicio or data_fim or apenas_ativas),
    }
    
    return render(request, "lojista/gestao_registros_jornada.html", context)


@login_required
@user_passes_test(can_manage_journey_records)
def editar_registro_jornada(request, registro_id):
    """
    Editar um registro de jornada específico
    - Corrigir horários
    - Alterar status
    - Adicionar observações
    
    Permissões: superuser, staff, grupo 'Suporte', grupo 'Gerente Solve'
    Tags: gestao, jornada, editar, rh
    """
    from participante.models import RegistroJornada
    from django.utils import timezone
    from datetime import datetime
    
    try:
        registro = RegistroJornada.objects.get(id=registro_id)
    except RegistroJornada.DoesNotExist:
        messages.error(request, "Registro de jornada não encontrado.")
        return redirect('lojista:gestao_registros_jornada')
    
    # Verificar se há ação via GET (para ações rápidas)
    action = request.GET.get('action')
    if action:
        if action == 'finalizar':
            registro.finalizar(finalizada_por=request.user)
            messages.success(request, "Jornada finalizada com sucesso!")
            return redirect('lojista:gestao_registros_jornada')
        
        elif action == 'pausar':
            registro.pausar()
            messages.success(request, "Jornada pausada com sucesso!")
            return redirect('lojista:gestao_registros_jornada')
        
        elif action == 'retomar':
            registro.retomar()
            messages.success(request, "Jornada retomada com sucesso!")
            return redirect('lojista:gestao_registros_jornada')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'salvar':
            try:
                # Horários
                horario_inicio_str = request.POST.get('horario_inicio')
                horario_fim_str = request.POST.get('horario_fim')
                status = request.POST.get('status')
                observacoes = request.POST.get('observacoes', '')
                
                # Converter strings para datetime
                if horario_inicio_str:
                    registro.horario_inicio = datetime.fromisoformat(horario_inicio_str.replace('Z', '+00:00'))
                
                if horario_fim_str:
                    registro.horario_fim = datetime.fromisoformat(horario_fim_str.replace('Z', '+00:00'))
                else:
                    registro.horario_fim = None
                
                registro.status = status
                registro.observacoes = observacoes
                registro.ultimo_update = timezone.now()
                
                # Se foi finalizada, registrar quem finalizou
                if status == 'FINALIZADA' and not registro.horario_fim:
                    registro.horario_fim = timezone.now()
                    registro.finalizada_por = request.user
                    # Deslogar o usuário se atender aos critérios
                    if registro._deve_deslogar_usuario(request.user):
                        registro._deslogar_usuario()
                
                registro.save()
                messages.success(request, "Registro de jornada atualizado com sucesso!")
                return redirect('lojista:gestao_registros_jornada')
                
            except Exception as e:
                messages.error(request, f"Erro ao atualizar registro: {str(e)}")
        
        elif action == 'finalizar':
            registro.finalizar(finalizada_por=request.user, deslogar_usuario=True)
            messages.success(request, "Jornada finalizada com sucesso!")
            return redirect('lojista:gestao_registros_jornada')
        
        elif action == 'pausar':
            registro.pausar()
            messages.success(request, "Jornada pausada com sucesso!")
            return redirect('lojista:gestao_registros_jornada')
        
        elif action == 'retomar':
            registro.retomar()
            messages.success(request, "Jornada retomada com sucesso!")
            return redirect('lojista:gestao_registros_jornada')
    
    # Buscar jornada configurada do colaborador
    jornada_configurada = None
    try:
        # Buscar jornada ativa do colaborador para a data do registro
        data_registro = registro.horario_inicio.date()
        jornada_configurada = JornadaColaborador.objects.filter(
            colaborador=registro.user,
            ativo=True,
            data_inicio__lte=data_registro
        ).filter(
            Q(data_fim__isnull=True) | Q(data_fim__gte=data_registro)
        ).select_related('tipo_jornada').first()
    except Exception:
        pass  # Se não conseguir buscar, continua sem a informação
    
    context = {
        'registro': registro,
        'jornada_configurada': jornada_configurada,
    }
    
    return render(request, "lojista/editar_registro_jornada.html", context)


@login_required
@user_passes_test(can_manage_journey_records)
def finalizar_jornadas_esquecidas(request):
    """
    Finalizar jornadas que foram esquecidas (ativas há mais de 24h)
    
    Permissões: superuser, staff, grupo 'Suporte', grupo 'Gerente Solve'
    Tags: gestao, jornada, finalizar, rh
    """
    from participante.models import RegistroJornada
    from django.utils import timezone
    from datetime import timedelta
    
    if request.method == 'POST':
        # Buscar jornadas ativas há mais de 24h - apenas colaboradores
        limite_24h = timezone.now() - timedelta(hours=24)
        jornadas_esquecidas = RegistroJornada.objects.filter(
            status='ATIVA',
            horario_inicio__lt=limite_24h,
            user__is_staff=True,
            user__profile__is_colaborador=True
        )
        
        count = 0
        for jornada in jornadas_esquecidas:
            jornada.finalizar(finalizada_por=request.user, deslogar_usuario=True)
            count += 1
        
        if count > 0:
            messages.success(request, f"{count} jornada(s) finalizada(s) automaticamente!")
        else:
            messages.info(request, "Nenhuma jornada esquecida encontrada.")
        
        return redirect('lojista:gestao_registros_jornada')
    
    # Mostrar preview das jornadas que seriam finalizadas - apenas colaboradores
    limite_24h = timezone.now() - timedelta(hours=24)
    jornadas_esquecidas = RegistroJornada.objects.filter(
        status='ATIVA',
        horario_inicio__lt=limite_24h,
        user__is_staff=True,
        user__profile__is_colaborador=True
    ).select_related('user__profile', 'posto_trabalho')
    
    context = {
        'jornadas_esquecidas': jornadas_esquecidas,
        'count': jornadas_esquecidas.count(),
    }
    
    return render(request, "lojista/finalizar_jornadas_esquecidas.html", context)


@login_required
@user_passes_test(can_manage_journey_records)
def exportar_registros_jornada_pdf(request):
    """
    Exporta os registros de jornada (com os mesmos filtros) para PDF.
    Usa xhtml2pdf para renderizar um template simples e devolve application/pdf.
    """
    from participante.models import RegistroJornada, Profile, PostoTrabalho
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa
    from io import BytesIO
    from datetime import datetime

    # Filtros (mesma lógica da listagem)
    status_filter = request.GET.get('status', '')
    colaborador_filter = request.GET.get('colaborador', '')
    posto_filter = request.GET.get('posto', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    apenas_ativas = request.GET.get('apenas_ativas', '') == 'on'

    # Normalização de CPF informado (aceita com ou sem máscara)
    cpf_masked_from_digits = None
    if colaborador_filter:
        digits_only = ''.join(ch for ch in colaborador_filter if ch.isdigit())
        if len(digits_only) == 11:
            cpf_masked_from_digits = f"{digits_only[0:3]}.{digits_only[3:6]}.{digits_only[6:9]}-{digits_only[9:11]}"

    registros = RegistroJornada.objects.select_related(
        'user__profile', 'posto_trabalho'
    ).filter(
        user__is_staff=True,
        user__profile__is_colaborador=True
    ).order_by('-horario_inicio')

    if status_filter:
        registros = registros.filter(status=status_filter)

    if colaborador_filter:
        from django.db.models import Q
        cpf_term = cpf_masked_from_digits or colaborador_filter
        registros = registros.filter(
            Q(user__first_name__icontains=colaborador_filter) |
            Q(user__last_name__icontains=colaborador_filter) |
            Q(user__username__icontains=colaborador_filter) |
            Q(user__profile__CPF__icontains=cpf_term) |
            Q(user__profile__nome__icontains=colaborador_filter)
        )

    if posto_filter:
        registros = registros.filter(posto_trabalho__id=posto_filter)

    # Validação e aplicação de intervalo (corrige invertido)
    data_inicio_dt = None
    data_fim_dt = None
    if data_inicio:
        try:
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except ValueError:
            data_inicio_dt = None
    if data_fim:
        try:
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except ValueError:
            data_fim_dt = None

    if data_inicio_dt and data_fim_dt and data_inicio_dt > data_fim_dt:
        data_inicio_dt, data_fim_dt = data_fim_dt, data_inicio_dt

    if data_inicio_dt:
        registros = registros.filter(horario_inicio__date__gte=data_inicio_dt)
    if data_fim_dt:
        registros = registros.filter(horario_inicio__date__lte=data_fim_dt)

    if apenas_ativas:
        registros = registros.filter(status='ATIVA')

    # Preparar dados para PDF agrupados por colaborador (sem cortar grupos)
    agora = timezone.now()
    from collections import OrderedDict
    grupos = OrderedDict()

    # Ordenar por colaborador e data/hora para garantir agrupamento estável
    registros = registros.order_by('user__id', 'horario_inicio')

    for r in registros.iterator():
        # calcular duração de exibição
        if r.horario_inicio:
            fim = r.horario_fim or agora
            duracao = fim - r.horario_inicio
            if duracao.total_seconds() < 0:
                from datetime import timedelta as _td
                duracao = _td(0)
            r.duracao_exibicao = RegistroJornada.formatar_duracao(duracao)
        else:
            r.duracao_exibicao = "N/A"

        uid = r.user_id
        if uid not in grupos:
            grupos[uid] = {
                'user': r.user,
                'registros': [],
                'total_segundos': 0,
            }
        grupos[uid]['registros'].append(r)
        if r.horario_inicio:
            fim_calc = r.horario_fim or agora
            grupos[uid]['total_segundos'] += int((fim_calc - r.horario_inicio).total_seconds())

    # Construir páginas já prontas
    from datetime import timedelta as _td
    pages = []
    for data in grupos.values():
        total_str = RegistroJornada.formatar_duracao(_td(seconds=max(0, data['total_segundos'])))
        pages.append({
            'user': data['user'],
            'registros': data['registros'],
            'total_duracao': total_str,
        })

    context = {
        'pages': pages,
        'gerado_em': agora,
        'periodo_inicio': data_inicio_dt,
        'periodo_fim': data_fim_dt,
        'status_filter': status_filter,
        'colaborador_filter': colaborador_filter,
        'posto_filter': posto_filter,
        'apenas_ativas': apenas_ativas,
    }

    html = render_to_string('lojista/registros_jornada_pdf.html', context)
    result = BytesIO()
    pdf_status = pisa.CreatePDF(src=html, dest=result)

    if pdf_status.err:
        messages.error(request, 'Falha ao gerar PDF de registros de jornada.')
        return redirect('lojista:gestao_registros_jornada')

    # Nome de arquivo informativo conforme filtros
    nome_parts = ["registros_jornada"]
    if data_inicio_dt or data_fim_dt:
        nome_parts.append((data_inicio_dt or 'ini').__str__())
        nome_parts.append((data_fim_dt or 'fim').__str__())
    if colaborador_filter:
        # usa somente dígitos do CPF para não ter caracteres especiais
        safe_cpf = ''.join(ch for ch in colaborador_filter if ch.isdigit())
        if safe_cpf:
            nome_parts.append(safe_cpf)
    filename = "_".join(str(p) for p in nome_parts) + ".pdf"

    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


