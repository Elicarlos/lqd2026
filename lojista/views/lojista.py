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


@login_required
@require_POST
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def autorizar_lojista(request, lojista_id):
    try:
        lojista = Lojista.objects.get(id=lojista_id)

        novo_status = request.POST.get("status")
        status_validos = dict(Lojista.STATUS_CHOICES).keys()

        if novo_status not in status_validos:
            return JsonResponse(
                {"success": False, "message": "Status inválido"}
            )

        lojista.status = novo_status
        lojista.autorizado_por = request.user
        lojista.save()

        return JsonResponse({"success": True, "status": lojista.status})

    except Lojista.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Lojista não encontrado"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def gerenciar_lojistas(request):
    """
    View completa para gerenciar lojistas com filtros, busca e paginação
    """
    try:
        from django.db.models import Q
        from django.core.paginator import Paginator
        from datetime import datetime
        
        # Obter parâmetros de filtro
        status_filter = request.GET.get('status', '')
        cnpj_search = request.GET.get('cnpj', '').strip()
        
        # Query base
        lojistas = Lojista.objects.all()
        
        # Aplicar filtro por status
        if status_filter:
            lojistas = lojistas.filter(status=status_filter)
        
        # Aplicar busca por CNPJ
        if cnpj_search:
            # Remove caracteres especiais do CNPJ para busca
            cnpj_clean = cnpj_search.replace('.', '').replace('/', '').replace('-', '')
            
            # Busca mais inteligente: tentar tanto o formato original quanto o limpo
            from django.db.models import Q
            
            # Criar query que busca tanto o CNPJ formatado quanto o limpo
            lojistas = lojistas.filter(
                Q(CNPJLojista__icontains=cnpj_search) |  # Busca com formatação
                Q(CNPJLojista__icontains=cnpj_clean)     # Busca sem formatação
            )
        
        # Ordenação (padrão: nome fantasia)
        order_by = request.GET.get('order_by', 'fantasiaLojista')
        if order_by in ['fantasiaLojista', 'razaoLojista', 'CNPJLojista', 'status', 'dataCadastro']:
            lojistas = lojistas.order_by(order_by)
        else:
            lojistas = lojistas.order_by('fantasiaLojista')
        
        # Paginação
        paginator = Paginator(lojistas, 20)  # 20 lojistas por página
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Estatísticas (baseadas nos filtros aplicados)
        autorizados_count = lojistas.filter(status='Sim').count()
        pendentes_count = lojistas.filter(status='Pendente').count()
        inativos_count = lojistas.filter(status__in=['Não', 'Inativo']).count()
        
        # Estatísticas totais (sem filtros)
        total_autorizados = Lojista.objects.filter(status='Sim').count()
        total_pendentes = Lojista.objects.filter(status='Pendente').count()
        total_inativos = Lojista.objects.filter(status__in=['Não', 'Inativo']).count()
        
        return render(
            request,
            "lojista/gerenciar_lojistas.html",
            {
                "page_obj": page_obj,
                "status_filter": status_filter,
                "cnpj_search": cnpj_search,
                "order_by": order_by,
                "autorizados_count": autorizados_count,
                "pendentes_count": pendentes_count,
                "inativos_count": inativos_count,
                "total_autorizados": total_autorizados,
                "total_pendentes": total_pendentes,
                "total_inativos": total_inativos,
                "total_lojistas": lojistas.count(),
                "has_filters": bool(status_filter or cnpj_search),
            },
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f"Erro ao carregar lojistas: {e}")
        return render(request, "lojista/gerenciar_lojistas.html", {
            "page_obj": None,
            "status_filter": "",
            "cnpj_search": "",
            "order_by": "fantasiaLojista",
            "autorizados_count": 0,
            "pendentes_count": 0,
            "inativos_count": 0,
            "total_autorizados": 0,
            "total_pendentes": 0,
            "total_inativos": 0,
            "total_lojistas": 0,
            "has_filters": False,
        })


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def editar_lojista(request, lojista_id):
    # Verificar se o usuário tem permissão para editar lojistas via sistema de cards
    from participante.models import CardDinamico
    
    try:
        card_editar = CardDinamico.objects.get(nome='editar_lojista', ativo=True)
        pode_editar = (
            request.user.is_superuser or 
            card_editar.pode_ver(request.user)
        )
    except CardDinamico.DoesNotExist:
        # Se o card não existe, usar verificação padrão
        pode_editar = request.user.is_superuser or request.user.is_staff
    
    if not pode_editar:
        messages.error(request, "Você não tem permissão para editar lojistas.")
        return redirect('lojista:homepage')
    
    lojista = get_object_or_404(Lojista, id=lojista_id)

    if request.method == "POST":
        form = LojistaRegistrationForm(request.POST, instance=lojista)
        
        if form.is_valid():
            form.save()
            messages.success(request, f"Lojista '{lojista.fantasiaLojista}' atualizado com sucesso!")
            return redirect("lojista:gerenciar_lojistas")
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = LojistaRegistrationForm(instance=lojista)
    
    return render(request, "lojista/editar_lojista.html", {
        "form": form,
        "lojista": lojista
    })


@login_required
def homepage(request):
    # Cards do dashboard agora são gerenciados pelo sistema CardDinamico
    # Não é mais necessário chamar setup_dashboard_cards_auto()
    
    # Verificar se o usuário tem permissão para acessar área operacional
    from participante.models import UserRole
    from participante.permissions import get_user_roles
    
    user_roles = UserRole.objects.filter(user=request.user).values_list('role__name', flat=True)
    user_roles_list = list(user_roles)
    
    # Roles que podem acessar área operacional
    roles_operacionais = ["Operador", "Supervisor", "Gerente", "Backoffice", "Gerente Solve", "Recursos Humanos", "Suporte", "Operadores"]
    is_staff_operacional = (
        request.user.is_superuser or
        any(role in roles_operacionais for role in user_roles_list) or
        any(request.user.groups.filter(name=role).exists() for role in roles_operacionais)
    )
    
    if not is_staff_operacional:
        from django.contrib import messages
        messages.error(request, "Você não tem permissão para acessar esta área.")
        return redirect("participante:dashboard")
    
    documentos_nao_enviados = DocumentoFiscal.objects.filter(
        enviado_por_operador=False, id=OuterRef("documentoFiscal_id")
    )

    cupons_pendentes = (
        Cupom.objects.filter(impresso=False)
        .annotate(documento_nao_enviado=Exists(documentos_nao_enviados))
        .filter(documento_nao_enviado=True)
        .exists()
    )

    campanha = Campanha.objects.filter(ativa=True).first()

    lojista_pendente = Lojista.objects.filter(status="Pendente").exists()

    postos_trabalho = PostoTrabalho.objects.all()
    jornada_ativa = RegistroJornada.objects.filter(
        user=request.user, horario_fim__isnull=True
    ).exists()
    show_popup = request.session.pop("show_popup", False)
    
    # Estatísticas para o dashboard
    from django.utils import timezone
    from django.db.models import Count
    from participante.models import StatusChoices
    
    hoje = timezone.now().date()
    
    # Estatísticas gerais
    # Usuários com is_staff=True são colaboradores (equipe interna)
    from django.contrib.auth.models import User
    colaboradores_ids = User.objects.filter(is_staff=True).values_list('id', flat=True)
    
    stats = {
        'participantes': Profile.objects.exclude(user_id__in=colaboradores_ids).count(),
        'colaboradores': Profile.objects.filter(user_id__in=colaboradores_ids).count(),
        'lojistas': Lojista.objects.count(),
        'lojistas_ativos': Lojista.objects.filter(status="Sim").count(),
        'pendentes': DocumentoFiscal.objects.filter(status=StatusChoices.PENDENTE).count(),
        'cupons': Cupom.objects.filter(dataCriacao__date=hoje).count(),
    }
    
    
    # Buscar cards do usuário
    user_cards = get_user_dashboard_cards(request.user)
    participantes_cards = get_cards_by_type(request.user, 'PARTICIPANTE')
    lojistas_cards = get_cards_by_type(request.user, 'LOJISTA')
    configuracoes_cards = get_cards_by_type(request.user, 'CONFIGURACAO')
    backoffice_cards = get_cards_by_type(request.user, 'BACKOFFICE')
    relatorios_cards = get_cards_by_type(request.user, 'RELATORIO')
    usuarios_cards = get_cards_by_type(request.user, 'RECURSOS_HUMANOS')
    operacoes_cards = get_cards_by_type(request.user, 'OPERACOES')    
    
    

    

    
    # Verificar se usuário tem grupos operacionais
    grupos_operacionais = ['Operador', 'Operadores', 'Gerente', 'Backoffice', 'Supervisor', 'Gerente Solve', 'Recursos Humanos', 'Suporte']
    tem_grupo_operacional = request.user.groups.filter(name__in=grupos_operacionais).exists()
    
    context = {
        "lojista_pendente": lojista_pendente,
        "campanha": campanha,
        "cupons_pendentes": cupons_pendentes,
        "jornada_iniciada": jornada_ativa,
        "show_popup": show_popup,
        "postos_trabalho": postos_trabalho,
        "section": "lojista",
        "is_operador": is_operador(request.user),
        "is_gerente": is_gerente(request.user),
        "is_gerente_solve": is_gerente_solve(request.user),
        "is_backoffice": is_backoffice(request.user),
        "is_supervisor": is_supervisor(request.user),
        "is_recursos_humanos": is_recursos_humanos(request.user),
        "stats": stats,
        # Cards organizados por tipo
        "participantes_cards": participantes_cards,
        "lojistas_cards": lojistas_cards,
        "configuracoes_cards": configuracoes_cards,
        "backoffice_cards": backoffice_cards,
        "relatorios_cards": relatorios_cards,
        "usuarios_cards": usuarios_cards,
        "operacoes_cards": operacoes_cards,
        "user_cards": user_cards,
        # Adicionar variáveis do modal
        "tem_grupo_operacional": tem_grupo_operacional,
        "postos_disponiveis": postos_trabalho,
    }
    return render(request, "lojista/dashboard-new.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def lojistas_home(request):
    """Esse é o dashboard de onde aparece os cards dos operadores e colocaboradores da campanha"""
    return render(request, "lojista/lojistas_home.html", {
        "section": "lojistas",
    })


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def cadastro_lojista(request):
    """Cadastro de lojistas"""
    if request.method == "POST":
        lojista_form = LojistaRegistrationForm(request.POST)

        if lojista_form.is_valid():
            new_lojista = lojista_form.save(commit=False)
            new_lojista.cadastrado_por = request.user

            if lojista_form.cleaned_data.get("lojista_cielo"):
                new_lojista.lojista_cielo = True

            new_lojista.save()

            messages.success(request, f"Lojista '{new_lojista.fantasiaLojista}' cadastrado com sucesso!")
            return redirect("lojista:gerenciar_lojistas")

        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")

    else:
        lojista_form = LojistaRegistrationForm()
    return render(request, "lojista/register-lojista.html", {"lojista_form": lojista_form})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit(request):
    if request.method == "POST":
        user_form = UserEditForm(instance=request.user, data=request.POST)
        profile_form = ProfileEditForm(
            instance=request.user.profile, data=request.POST, files=request.FILES
        )
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Perfil atualizado com sucesso")
        else:
            messages.error(request, "Erro na atualização do perfil")
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)
    return render(
        request,
        "participante/edit.html",
        {"user_form": user_form, "profile_form": profile_form},
    )


@login_required
@user_passes_test(lambda u: u.is_superuser)
def editlojista(request, id):
    if request.method == "POST":
        instance = get_object_or_404(Lojista, id=id)
        lojista_form = LojistaRegistrationForm(instance=instance, data=request.POST)
        if lojista_form.is_valid():
            lojista_form.save()
            messages.success(request, "Perfil atualizado com sucesso")
        else:
            messages.error(request, "Erro na atualização do Lojista")
    else:
        instance = get_object_or_404(Lojista, id=id)
        lojista_form = LojistaRegistrationForm(instance=instance)
    return render(request, "lojista/edit.html", {"lojista_form": lojista_form})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def lojistalist(request):
    lojistas = Lojista.objects.all()
    return render(
        request,
        "lojista/list_lojistas.html",
        {"section": "listar-lojistas", "lojistas": lojistas},
    )


@login_required
@require_card_permission('autorizar_lojista', redirect_url='lojista:homepage')
def autorizar_lojistas(request):
    """
    View para gerenciar autorizações de lojistas
    """
    from django.db.models import Q
    from django.contrib.auth.models import Group
    from django.db import transaction
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from lojista.models import AutorizacaoLojista
    
    # Permissão já verificada pelo decorator @require_card_permission
    
    # Parâmetros de filtro e paginação
    search_query = request.GET.get('search', '').strip()
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 20)  # Itens por página
    
    # Query base para todos os lojistas
    lojistas_queryset = Lojista.objects.all()
    
    # Aplicar filtro de busca se fornecido
    if search_query:
        lojistas_queryset = lojistas_queryset.filter(
            Q(CNPJLojista__icontains=search_query) |
            Q(fantasiaLojista__icontains=search_query) |
            Q(razaoLojista__icontains=search_query)
        )
    
    # Ordenar por fantasia
    lojistas_queryset = lojistas_queryset.order_by('fantasiaLojista')
    
    # Aplicar paginação
    paginator = Paginator(lojistas_queryset, per_page)
    try:
        lojistas_paginados = paginator.page(page)
    except PageNotAnInteger:
        lojistas_paginados = paginator.page(1)
    except EmptyPage:
        lojistas_paginados = paginator.page(paginator.num_pages)
    
    # Buscar todos os lojistas organizados por status (sem paginação para os cards)
    lojistas_pendentes = Lojista.objects.filter(status="Pendente").order_by('fantasiaLojista')
    lojistas_autorizados = Lojista.objects.filter(status="Sim").order_by('fantasiaLojista')
    lojistas_negados = Lojista.objects.filter(status="Não").order_by('fantasiaLojista')
    lojistas_inativos = Lojista.objects.filter(status="Inativo").order_by('fantasiaLojista')
    
    if request.method == "POST":
        action = request.POST.get('action')
        lojista_id = request.POST.get('lojista_id')
        novo_status = request.POST.get('novo_status')
        observacao = request.POST.get('observacao', '')
        
        try:
            lojista = Lojista.objects.get(id=lojista_id)
            status_anterior = lojista.status
            
            if action == 'alterar_status':
                # Validar se novo_status foi fornecido
                if not novo_status or novo_status.strip() == '':
                    messages.error(request, "Status não pode estar vazio.")
                    return redirect('lojista:autorizar_lojistas')
                
                novo_status = novo_status.strip()
                
                # Validar observação para rejeições (apenas quando realmente rejeitando)
                if novo_status == 'Não':
                    observacao_limpa = observacao.strip() if observacao else ''
                    if not observacao_limpa:
                        messages.error(request, "É obrigatório informar o motivo da rejeição.")
                        return redirect('lojista:autorizar_lojistas')
                

                
                with transaction.atomic():
                    # Registrar a autorização
                    AutorizacaoLojista.objects.create(
                        lojista=lojista,
                        autorizado_por=request.user,
                        status_anterior=status_anterior or '',
                        status_novo=novo_status,
                        observacao=observacao
                    )
                    
                    # Atualizar o status do lojista
                    lojista.status = novo_status
                    lojista.autorizado_por = request.user
                    lojista.save()
                    
                    messages.success(request, f"Status do lojista {lojista.fantasiaLojista} alterado para {novo_status}.")
                    return redirect('lojista:autorizar_lojistas')
                    
        except Lojista.DoesNotExist:
            messages.error(request, "Lojista não encontrado.")
            return redirect('lojista:autorizar_lojistas')
        except Exception as e:
            messages.error(request, f"Erro ao processar autorização: {str(e)}")
            return redirect('lojista:autorizar_lojistas')
    
    # Buscar histórico de autorizações
    historico_autorizacoes = AutorizacaoLojista.objects.select_related('lojista', 'autorizado_por').order_by('-data_autorizacao')[:20]
    
    context = {
        'lojistas_pendentes': lojistas_pendentes,
        'lojistas_autorizados': lojistas_autorizados,
        'lojistas_negados': lojistas_negados,
        'lojistas_inativos': lojistas_inativos,
        'lojistas_paginados': lojistas_paginados,
        'historico_autorizacoes': historico_autorizacoes,
        'search_query': search_query,
        'per_page': per_page,
    }
    
    return render(request, "lojista/autorizar_lojistas.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def buscar_lojista_ajax(request):
    """
    View AJAX para buscar lojista por CNPJ exatamente como foi digitado
    """
    from django.http import JsonResponse
    
    cnpj = request.GET.get('cnpj', '').strip()
    
    
    if not cnpj:
        return JsonResponse({
            'success': False,
            'message': 'CNPJ não fornecido'
        })
    
    try:
        # Buscar lojista - busca exata com o CNPJ exatamente como foi digitado
        lojista = Lojista.objects.filter(CNPJLojista=cnpj).first()
        
        if lojista:
            # Busca exata - sempre será encontrado_exato = True
            encontrado_exato = True    
            # Log para debug
           
            
            return JsonResponse({
                'success': True,
                'encontrado_exato': encontrado_exato,
                'cnpj_buscado': cnpj,
                'cnpj_encontrado': lojista.CNPJLojista,
                'lojista': {
                    'id': lojista.id,
                    'cnpj': lojista.CNPJLojista,
                    'razaoLojista': lojista.razaoLojista,
                    'fantasiaLojista': lojista.fantasiaLojista,
                    'status': lojista.status,
                    'telefone': lojista.telefone or '',
                    'endereco': lojista.endereco or ''
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Lojista não encontrado'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao buscar lojista: {str(e)}'
        })


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@require_POST
def cadastrar_lojista_ajax(request):
    """
    View AJAX para cadastrar novo lojista
    """
    from django.http import JsonResponse
    from django.db import transaction

    
    
    try:
        cnpj = request.POST.get('cnpj', '').strip()
        razao_social = request.POST.get('razao_social', '').strip()
        nome_fantasia = request.POST.get('nome_fantasia', '').strip()
        telefone = request.POST.get('telefone', '').strip()
        endereco = request.POST.get('endereco', '').strip()
        ramo_atividade_id = request.POST.get('ramo_atividade_id', '').strip()
        localizacao_id = request.POST.get('localizacao_id', '').strip()

        print(f"Antes e limpar {cnpj}")
        
        # Validações
        if not cnpj or not razao_social or not nome_fantasia:
            return JsonResponse({
                'success': False,
                'message': 'CNPJ, Razão Social e Nome Fantasia são obrigatórios'
            })
        
        # Limpar CNPJ e aplicar máscara
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        
        
        if len(cnpj_limpo) != 14:
            return JsonResponse({
                'success': False,
                'message': 'CNPJ deve ter 14 dígitos'
            })
        
        # Aplicar máscara ao CNPJ (formato XX.XXX.XXX/XXXX-XX)
        cnpj_formatado = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"

       

        
        
        # Verificar se já existe
        if Lojista.objects.filter(CNPJLojista=cnpj_formatado).exists():
            return JsonResponse({
                'success': False,
                'message': 'Lojista com este CNPJ já está cadastrado'
            })
        
        # Buscar ramo de atividade e localização
        ramo_atividade = None
        if ramo_atividade_id:
            try:
                ramo_atividade = RamoAtividade.objects.get(id=ramo_atividade_id, ativo=True)
            except RamoAtividade.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Ramo de atividade selecionado não existe ou está inativo'
                })
        
        localizacao = None
        if localizacao_id:
            try:
                localizacao = Localizacao.objects.get(id=localizacao_id)
            except Localizacao.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Localização selecionada não existe'
                })

        with transaction.atomic():
            # Criar novo lojista
            novo_lojista = Lojista.objects.create(
                CNPJLojista=cnpj_formatado,
                razaoLojista=razao_social,
                fantasiaLojista=nome_fantasia,
                telefone=telefone,
                endereco=endereco,
                ramoAtividade=ramo_atividade,
                localizacao=localizacao,
                status='Pendente',  # Status inicial
                cadastrado_por=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Lojista cadastrado com sucesso',
                'lojista': {
                    'id': novo_lojista.id,
                    'cnpj': novo_lojista.CNPJLojista,
                    'razaoLojista': novo_lojista.razaoLojista,
                    'fantasiaLojista': novo_lojista.fantasiaLojista,
                    'status': novo_lojista.status,
                    'telefone': novo_lojista.telefone or '',
                    'endereco': novo_lojista.endereco or '',
                    'ramoAtividade': novo_lojista.ramoAtividade.atividade if novo_lojista.ramoAtividade else '',
                    'localizacao': novo_lojista.localizacao.nome if novo_lojista.localizacao else ''
                }
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao cadastrar lojista: {str(e)}'
        })


