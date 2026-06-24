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


def can_manage_journey_records(user):
    """
    Verifica se o usuário pode gerenciar registros de jornada
    - Superuser
    - Staff
    - Grupo 'Suporte'
    - Grupo 'Gerente Solve'
    """
    if user.is_superuser or user.is_staff:
        return True
    
    # Verificar grupos específicos
    grupos_permitidos = ['Suporte', 'Gerente Solve']
    user_groups = user.groups.values_list('name', flat=True)
    
    return any(grupo in user_groups for grupo in grupos_permitidos)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def solicitar_materiais(request):
    """
    Redireciona para o formulário externo da empresa.
    Disponível para operadores e outros grupos conforme configuração.
    """
    # Verificar se o usuário tem permissão para acessar esta funcionalidade
    
    if not user_has_card_permission(request.user, 'solicitar_materiais'):
        messages.error(request, "Você não tem permissão para acessar esta funcionalidade.")
        return redirect('lojista:homepage')
    
    # Redirecionar para o formulário externo da empresa
    # SUBSTITUA PELA URL REAL QUE A EMPRESA VAI FORNECER
    link_formulario_empresa = "https://forms.google.com/d/SEU-FORMULARIO-AQUI"
    return redirect(link_formulario_empresa)
    
    # Buscar informações do usuário para o formulário
    try:
        profile = request.user.profile
        posto_trabalho = profile.posto_trabalho
    except:
        profile = None
        posto_trabalho = None
    
    # Se for POST, processar o formulário
    if request.method == 'POST':
        # Aqui você pode processar a solicitação
        tipo_material = request.POST.get('tipo_material')
        quantidade = request.POST.get('quantidade')
        descricao = request.POST.get('descricao')
        urgencia = request.POST.get('urgencia', 'normal')
        
        # Validações básicas
        if not tipo_material or not quantidade or not descricao:
            messages.error(request, "Todos os campos obrigatórios devem ser preenchidos.")
        else:
            # Aqui você salvaria a solicitação no banco de dados
            # Por enquanto, vamos só exibir uma mensagem de sucesso
            messages.success(
                request, 
                f"Solicitação de {tipo_material} enviada com sucesso! "
                f"Quantidade: {quantidade}, Urgência: {urgencia}"
            )
            return redirect('lojista:solicitar_materiais')
    
    # Tipos de materiais disponíveis
    tipos_materiais = [
        ('bobinas_cupom', 'Bobinas para Cupons'),
        ('bobinas_comprovante', 'Bobinas para Comprovantes'),
        ('papel_a4', 'Papel A4'),
        ('canetas', 'Canetas'),
        ('grampeador', 'Grampeador'),
        ('grampos', 'Grampos'),
        ('pasta_documentos', 'Pasta para Documentos'),
        ('outros', 'Outros Materiais'),
    ]
    
    context = {
        'profile': profile,
        'posto_trabalho': posto_trabalho,
        'tipos_materiais': tipos_materiais,
        'page_title': 'Solicitar Materiais',
    }
    
    return render(request, 'lojista/solicitar_materiais.html', context)


