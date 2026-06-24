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
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def registeratividade(request):
    if request.method == "POST":
        ramoatividade_form = RamoAtividadeRegistrationForm(request.POST)

        if ramoatividade_form.is_valid():
            new_ramoatividade = ramoatividade_form.save(commit=False)
            new_ramoatividade.cadastrado_por = request.user
            new_ramoatividade.save()
            messages.success(request, f"Ramo de atividade '{new_ramoatividade.atividade}' cadastrado com sucesso!")
            return redirect("lojista:listatividade")
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")

    else:
        ramoatividade_form = RamoAtividadeRegistrationForm()
    return render(
        request,
        "lojista/register_ramo_atividade.html",
        {"form": ramoatividade_form},
    )


@login_required
@login_required
@user_passes_test(lambda u: u.is_superuser)
def register_localizacao(request):
    if request.method == "POST":
        localizacao_form = LocalizacaoRegistrationForm(request.POST)

        if localizacao_form.is_valid():
            nova_localizacao = localizacao_form.save(commit=False)
            nova_localizacao.cadastrado_por = request.user
            nova_localizacao.save()
            messages.success(request, f"Localização '{nova_localizacao.nome}' cadastrada com sucesso!")
            return redirect("lojista:lista_localizao")
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
            print(f"Form errors: {localizacao_form.errors}")

    else:
        localizacao_form = LocalizacaoRegistrationForm()
    return render(
        request,
        "lojista/registro_localizacao.html",
        {"localizacao_form": localizacao_form},
    )


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def listatividade(request):
    ramosatividade = RamoAtividade.objects.all().order_by('atividade')
    return render(
        request,
        "lojista/list_ramo_atividade.html",
        {"section": "ramoatividade", "ramosatividade": ramosatividade},
    )


@login_required
@user_passes_test(lambda u: u.is_superuser)
def editar_ramo_atividade(request, ramo_id):
    ramo = get_object_or_404(RamoAtividade, id=ramo_id)
    
    if request.method == "POST":
        atividade = request.POST.get("atividade")
        ativo = request.POST.get("ativo") == "1"
        
        if atividade:
            ramo.atividade = atividade
            ramo.ativo = ativo
            ramo.save()
            messages.success(request, f"Ramo de atividade '{ramo.atividade}' atualizado com sucesso!")
            return redirect("lojista:listatividade")
        else:
            messages.error(request, "Nome da atividade é obrigatório.")
    
    return render(request, "lojista/editar_ramo_atividade.html", {"ramo": ramo})


@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def excluir_ramo_atividade(request, ramo_id):
    ramo = get_object_or_404(RamoAtividade, id=ramo_id)
    nome = ramo.atividade
    
    # Verifica se há lojistas usando este ramo
    lojistas_com_ramo = ramo.lojista_set.count()
    
    if lojistas_com_ramo > 0:
        messages.error(
            request, 
            f"Não é possível excluir o ramo '{nome}' pois existem {lojistas_com_ramo} lojista(s) vinculado(s) a ele."
        )
    else:
        ramo.delete()
        messages.success(request, f"Ramo de atividade '{nome}' excluído com sucesso!")
    
    return redirect("lojista:listatividade")


@login_required
@login_required
@user_passes_test(lambda u: u.is_superuser)
def lista_localizacao(request):
    localizacoes = Localizacao.objects.all().order_by('nome')
    return render(
        request,
        "lojista/list_localizacao.html",
        {"section": "localizacao", "localizacoes": localizacoes},
    )


@login_required
@user_passes_test(lambda u: u.is_superuser)
def editar_localizacao(request, localizacao_id):
    localizacao = get_object_or_404(Localizacao, id=localizacao_id)
    
    if request.method == "POST":
        nome = request.POST.get("nome")
        descricao = request.POST.get("descricao", "")
        
        if nome:
            localizacao.nome = nome
            localizacao.descricao = descricao
            localizacao.save()
            messages.success(request, f"Localização '{localizacao.nome}' atualizada com sucesso!")
            return redirect("lojista:lista_localizao")
        else:
            messages.error(request, "Nome da localização é obrigatório.")
    
    return render(request, "lojista/editar_localizacao.html", {"localizacao": localizacao})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def excluir_localizacao(request, localizacao_id):
    localizacao = get_object_or_404(Localizacao, id=localizacao_id)
    if localizacao.lojista_set.exists():
        messages.error(
            request,
            "Não é possível excluir uma localização que possui lojistas vinculados.",
        )
        return redirect("lojista:lista_localizao")
    try:
        localizacao.delete()
        messages.success(
            request, f'Localização "{localizacao.nome}" excluída com sucesso.'
        )
    except Exception as e:
        messages.error(request, f"Erro ao excluir localização: {str(e)}")
    return redirect("lojista:lista_localizao")


@login_required
@user_passes_test(lambda u: u.is_superuser)
def lista_interessado(request):
    try:
        interessados = AdesaoLojista.objects.all().order_by(
            "atendido", "-data_contato", "fantasia"
        )

        # Estatísticas
        total_count = interessados.count()
        pendentes_count = interessados.filter(status='Pendente').count()
        convertidos_count = interessados.filter(status='Sim').count()
        sem_venda_count = interessados.filter(status='Atendido sem Venda').count()
        inativos_count = interessados.filter(status='Inativo').count()

        return render(
            request,
            "lojista/lista_interessados.html",
            {
                "section": "interessados", 
                "interessados": interessados,
                "total_count": total_count,
                "pendentes_count": pendentes_count,
                "convertidos_count": convertidos_count,
                "sem_venda_count": sem_venda_count,
                "inativos_count": inativos_count,
            },
        )
    except Exception as e:
        print(f"Erro na view lista_interessado: {str(e)}")
        messages.error(request, f"Erro ao carregar a página: {str(e)}")
        return render(request, "lojista/lista_interessados.html", {
            "section": "interessados",
            "interessados": [],
            "total_count": 0,
            "pendentes_count": 0,
            "convertidos_count": 0,
            "sem_venda_count": 0,
            "inativos_count": 0,
        })


@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def marcar_como_atendido(request, adesao_id):
    try:
        adesao = get_object_or_404(AdesaoLojista, id=adesao_id)

        # Pega o status do request ou usa o padrão
        novo_status = request.POST.get("status", "Atendido sem Venda")

        # Valida se o status é permitido
        if novo_status not in dict(AdesaoLojista.STATUS_CHOICES).keys():
            messages.error(request, "Status inválido selecionado.")
            return JsonResponse({"error": "Status inválido"}, status=400)

        # Atualiza os campos
        adesao.atendido = True
        adesao.atendido_por = request.user
        adesao.data_contato = timezone.now()
        adesao.status = novo_status

        # Salva as alterações
        adesao.save()

        # Adiciona mensagem de sucesso
        messages.success(
            request,
            f'Lojista "{adesao.fantasia}" atualizado para status "{novo_status}".',
        )

        # Retorna JSON para requisições AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                "success": True,
                "message": f'Lojista "{adesao.fantasia}" atualizado para status "{novo_status}".',
                "status": novo_status
            })

    except Exception as e:
        # Log do erro e mensagem para o usuário
        print(f"Erro ao atualizar status do lojista: {str(e)}")
        messages.error(
            request, "Erro ao atualizar status do lojista. Por favor, tente novamente."
        )
        return JsonResponse({"error": str(e)}, status=500)

    return redirect("lojista:lista_interessado")


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def register_posto(request):
    if request.method == "POST":
        nome = request.POST.get("nome")
        descricao = request.POST.get("descricao", "")
        
        if nome:
            PostoTrabalho.objects.create(
                nome=nome,
                descricao=descricao
            )
            messages.success(request, f"Posto '{nome}' cadastrado com sucesso!")
            return redirect("lojista:listar_postos")
        else:
            messages.error(request, "Nome do posto é obrigatório.")
    
    return render(request, "lojista/register_posto.html")


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def listar_postos(request):
    postos = PostoTrabalho.objects.all().order_by('nome')
    return render(request, "lojista/listar_postos.html", {"postos": postos})


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def editar_posto(request, posto_id):
    posto = get_object_or_404(PostoTrabalho, id=posto_id)
    
    if request.method == "POST":
        nome = request.POST.get("nome")
        descricao = request.POST.get("descricao", "")
        
        if nome:
            posto.nome = nome
            posto.descricao = descricao
            posto.save()
            messages.success(request, f"Posto '{nome}' atualizado com sucesso!")
            return redirect("lojista:listar_postos")
        else:
            messages.error(request, "Nome do posto é obrigatório.")
    
    return render(request, "lojista/editar_posto.html", {"posto": posto})


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@require_POST
def excluir_posto(request, posto_id):
    posto = get_object_or_404(PostoTrabalho, id=posto_id)
    nome = posto.nome
    
    # Verifica se há usuários usando este posto
    usuarios_com_posto = Profile.objects.filter(posto_trabalho=posto).count()
    jornadas_com_posto = RegistroJornada.objects.filter(posto_trabalho=posto).count()
    
    if usuarios_com_posto > 0 or jornadas_com_posto > 0:
        messages.error(
            request, 
            f"Não é possível excluir o posto '{nome}' pois existem {usuarios_com_posto} usuário(s) e {jornadas_com_posto} jornada(s) vinculada(s) a ele."
        )
    else:
        posto.delete()
        messages.success(request, f"Posto '{nome}' excluído com sucesso!")
    
    return redirect("lojista:listar_postos")


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@require_POST
def atualizar_status(request, interessado_id):
    if request.method == "POST":
        interessado = get_object_or_404(AdesaoLojista, id=interessado_id)
        novo_status = request.POST.get("status")

        if novo_status in dict(interessado.STATUS_CHOICES).keys():
            interessado.atualizar_status(novo_status, request.user)
            return JsonResponse(
                {
                    "success": True,
                    "status": novo_status,
                    "autorizado_por": request.user.get_full_name()
                    or request.user.username,
                }
            )
        return JsonResponse({"success": False, "error": "Status inválido."}, status=400)
    return JsonResponse(
        {"success": False, "error": "Método não permitido."}, status=405
    )


@require_http_methods(["GET"])
def buscar_ramos_atividade_ajax(request):
    """
    View AJAX para buscar ramos de atividade disponíveis
    """
    from django.http import JsonResponse
    
    try:
        ramos = RamoAtividade.objects.filter(ativo=True).order_by('atividade')
        ramos_data = [{'id': ramo.id, 'nome': ramo.atividade} for ramo in ramos]
        
        return JsonResponse({
            'success': True,
            'ramos': ramos_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao buscar ramos de atividade: {str(e)}'
        })


@require_http_methods(["GET"])
def buscar_localizacoes_ajax(request):
    """
    View AJAX para buscar localizações disponíveis
    """
    from django.http import JsonResponse
    
    try:
        localizacoes = Localizacao.objects.all().order_by('nome')
        localizacoes_data = [{'id': loc.id, 'nome': loc.nome} for loc in localizacoes]
        
        return JsonResponse({
            'success': True,
            'localizacoes': localizacoes_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao buscar localizações: {str(e)}'
        })


