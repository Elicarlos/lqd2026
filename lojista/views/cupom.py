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
@user_passes_test(lambda u: u.is_staff)
def reprint(request):
    # Obter parâmetros de busca
    numero_documento = request.GET.get("numero_documento", "")
    cpf_participante = request.GET.get("cpf_participante", "")
    data_documento = request.GET.get("data_documento", "")
    lojista_id = request.GET.get("lojista", "")
    status = request.GET.get("status", "")
    valor_minimo = request.GET.get("valor_minimo", "")

    # Query base
    documentos = DocumentoFiscal.objects.all()

    # Aplicar filtros
    if numero_documento:
        documentos = documentos.filter(numeroDocumento__icontains=numero_documento)
    
    if cpf_participante:
        cpf_limpo = cpf_participante.replace('.', '').replace('-', '')
        documentos = documentos.filter(user__profile__CPF__icontains=cpf_limpo)
    
    if data_documento:
        documentos = documentos.filter(dataDocumento=data_documento)
    
    if lojista_id:
        documentos = documentos.filter(lojista_id=lojista_id)
    
    if status:
        documentos = documentos.filter(status=status)
    
    if valor_minimo:
        try:
            valor = float(valor_minimo)
            documentos = documentos.filter(valorDocumento__gte=valor)
        except ValueError:
            pass

    # Ordenar por data de cadastro (mais recentes primeiro)
    documentos = documentos.order_by('-dataCadastro')

    # Obter lista de lojistas para o filtro
    lojistas = Lojista.objects.filter(status="Sim").order_by('fantasiaLojista')

    context = {
        "documentos": documentos,
        "lojistas": lojistas,
    }

    return render(request, "lojista/search_doc.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def cupons(request):
    if request.GET.get("q"):
        if "q" in request.GET is not None:
            cpf = request.GET.get("q")
            profile = get_object_or_404(Profile, CPF=cpf)
            user = get_object_or_404(User, username=profile.user.username)
            cupons = Cupom.objects.filter(user=user)
            return render(
                request,
                "lojista/cupons.html",
                {"section": "cupons", "user": profile, "cupons": cupons},
            )
        else:
            messages.error(request, "CPF não encontrado!")
    return render(request, "lojista/search_by_cpf.html")


@login_required
@user_passes_test(lambda u: u.is_superuser)
def search_cupom(request):
    if request.GET.get("q"):
        if "q" in request.GET is not None:
            numeroCupom = request.GET.get("q")
            try:
                cupom = Cupom.objects.get(id=numeroCupom)
                if cupom:
                    profile = Profile.objects.get(user=cupom.user)
                    return render(
                        request,
                        "lojista/cupom_detail.html",
                        {"section": "cupons", "user": profile, "cupom": cupom},
                    )
            except Cupom.DoesNotExist:
                messages.error(request, "Cupom não encontrado!")
                return render(request, "lojista/search_by_cupom.html")
        else:
            messages.error(request, "Cupom não encontrado!")
    return render(request, "lojista/search_by_cupom.html")


@login_required
@user_passes_test(lambda u: u.is_superuser)
def search(request):
    # Ordena os lojistas pelo status, priorizando "Pendente"
    lojista_list = Lojista.objects.all().order_by(
        Case(When(status="Pendente", then=0), default=1), "status"
    )

    lojista_filter = LojistaFilter(request.GET, queryset=lojista_list)
    queryset_filtrado = lojista_filter.qs

    # Paginação
    paginator = Paginator(queryset_filtrado, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "lojista/lojistas_list.html",
        {
            "filter": lojista_filter,
            "page_obj": page_obj,
            "section": "lojistas",
        },
    )


