import json
from calendar import month
from datetime import datetime, timedelta
from decimal import Decimal
from pydoc import Doc
from unicodedata import decimal
from unittest import result
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    QueryDict,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from yaml import DocumentEndEvent
from participante.tasks import email_boas_vindas_task
from participante.forms import *
from participante.models import Campanha, Profile, DocumentoFiscal, PostoTrabalho, RegistroJornada, StatusChoices, TipoJornada, Auditoria, CancelamentoImpressao
from lojista.models import Lojista, AdesaoLojista
from participante.filters import UserFilter, DocFilter
from django.db.models.functions import Lower, Upper
from cupom.forms import AddCupomForm
from cupom.models import Cupom
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db import transaction
from participante.forms import LoginForm, CepForm
from lojista.forms import FormLojistaAdesao
import requests
from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.utils.timezone import now
from django.db import IntegrityError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from django.template.loader import render_to_string
from participante.tasks import (
    email_recuperacao_senha,
    gerar_pdf_batidas_task,
    gerar_pdf_batidas_filtros_task,
)
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from django.contrib.auth.decorators import permission_required
from django.db.models import Exists, OuterRef
from xhtml2pdf import pisa
from django.db.models import Q
from django.views.generic import TemplateView
from participante.templatetags.custom_filters import formatar_timedelta
from participante.permissions import (
    role_required,
    any_role_required,
    all_roles_required,
    is_operador,
    is_gerente,
    is_backoffice,
    is_supervisor,
    is_gerente_solve,
    is_recursos_humanos,
    get_user_roles,
    PERMISSIONS,
)
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.shortcuts import render
from django.db.models import Count
from participante.models import DocumentoFiscal
from django.db import IntegrityError
from django.http import HttpResponseGone
from django.db.models.functions import TruncMonth, TruncDate
from django.db.models.aggregates import Count, Avg, Min, Max, Sum
from django.db.models import Count, F
from utils.formatters import formatar_duracao
from django.core.files.storage import FileSystemStorage
from django.views.decorators.http import require_POST
from utils.formatters import formatar_cpf  # Importa a função do novo módulo
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie


# Consulta para obter a quantidade de cupons por documento fiscal
def get_cupons_count_by_documento():
    cupons_por_documento = (
        Cupom.objects.values("documentoFiscal__id", "documentoFiscal__numeroDocumento")
        .annotate(total_cupons=Count("id"))
        .order_by("documentoFiscal")
    )
    return cupons_por_documento


@login_required
@user_passes_test(lambda u: u.is_superuser)
def cupons_count_view(request):
    cupons_por_documento = (
        Cupom.objects.values("documentoFiscal__id", "documentoFiscal__numeroDocumento")
        .annotate(total_cupons=Count("id"))
        .order_by("documentoFiscal")
    )
    context = {"cupons_por_documento": cupons_por_documento}
    return render(request, "participante/cupons_count.html", context)


@csrf_exempt
@require_POST
def upload_file(request):
    if "file" not in request.FILES:
        return JsonResponse({"error": "Nenhum arquivo enviado."}, status=400)

    uploaded_file = request.FILES["file"]
    fs = FileSystemStorage()
    filename = fs.save(uploaded_file.name, uploaded_file)
    file_url = fs.url(filename)

    return JsonResponse(
        {
            "success": True,
            "message": "Arquivo enviado com sucesso.",
            "file_url": request.build_absolute_uri(file_url),
        }
    )


@require_http_methods(["POST"])
@ensure_csrf_cookie
def test_api(request):
    """
    View de teste simples para verificar se a API está funcionando.
    """
 
    
    # Verificar se a sessão não expirou
    if not request.session.session_key:
        return JsonResponse({
            'success': False,
            'message': 'Sessão expirada. Faça login novamente.',
            'error_type': 'session_expired'
        }, status=401)
    
    # Verificar se a sessão tem dados de usuário
    if '_auth_user_id' not in request.session:
        return JsonResponse({
            'success': False,
            'message': 'Sessão inválida. Faça login novamente.',
            'error_type': 'invalid_session'
        }, status=401)
    
    response_data = {
        'success': True,
        'message': 'API funcionando corretamente',
        'user': request.user.username,
        'timestamp': timezone.now().isoformat(),
        'debug_info': {
            'authenticated': request.user.is_authenticated,
            'is_staff': request.user.is_staff,
            'method': request.method,
            'path': request.path,
            'content_type': request.content_type,
        }
    }
    
    return JsonResponse(response_data)


