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


from .utils import has_operational_access

@login_required
@user_passes_test(lambda u: u.is_superuser)
def search(request):
    user_list = Profile.objects.all().order_by(Upper("nome").asc())
    user_filter = UserFilter(request.GET, queryset=user_list)
    return render(
        request,
        "participante/participante_list.html",
        {"filter": user_filter, "section": "participantes"},
    )


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)  # Mudança para permitir staff
def search_by_cpf(request):
    cpf = request.GET.get("q", "").strip()

    if cpf:
        # Remove todos os caracteres não numéricos do CPF
        cpf_limpo = "".join(filter(str.isdigit, cpf))
        
        # Validação básica do CPF
        if len(cpf_limpo) != 11:
            messages.error(request, "CPF inválido. O CPF deve conter 11 dígitos numéricos.")
            return render(
                request,
                "participante/search_by_cpf.html",
                {
                    "section": "search",
                },
            )
        
        # Verifica se todos os dígitos são iguais (CPF inválido)
        if len(set(cpf_limpo)) == 1:
            messages.error(request, "CPF inválido. O CPF não pode ter todos os dígitos iguais.")
            return render(
                request,
                "participante/search_by_cpf.html",
                {
                    "section": "search",
                },
            )
        
        # Formata o CPF no padrão XXX.XXX.XXX-XX
        cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
        
        try:
            # Tenta buscar com todas as possíveis formatações - APENAS PARTICIPANTES (não colaboradores)
            profile = Profile.objects.filter(
                Q(CPF=cpf_limpo) |  # CPF sem formatação
                Q(CPF=cpf_formatado) |  # CPF com formatação padrão
                Q(CPF__icontains=cpf_limpo)  # CPF em qualquer formato que contenha os números
            ).filter(
                user__is_superuser=False,  # Excluir superusers
                is_colaborador=False       # Excluir colaboradores
            ).first()
            
            if not profile:
                # Verifica se existe um perfil com esse CPF mas é colaborador
                colaborador_exists = Profile.objects.filter(
                    Q(CPF=cpf_limpo) | 
                    Q(CPF=cpf_formatado) | 
                    Q(CPF__icontains=cpf_limpo)
                ).filter(
                    user__is_superuser=False,
                    is_colaborador=True
                ).exists()
                
                if colaborador_exists:
                    messages.error(request, "CPF encontrado, mas pertence a um colaborador/operador. Apenas participantes podem ser consultados nesta busca.")
                else:
                    messages.error(request, f"Participante não encontrado com o CPF {cpf_formatado}. Verifique se o CPF está correto ou se o participante já foi cadastrado.")
                
                return render(
                    request,
                    "participante/search_by_cpf.html",
                    {
                        "section": "search",
                    },
                )

            docs = DocumentoFiscal.objects.filter(
                user=profile.user,
            ).annotate(
                has_unprinted_cupons=Exists(
                    Cupom.objects.filter(
                        documentoFiscal=OuterRef("id"),
                        impresso=False,  # Apenas cupons não impressos
                    )
                ),
                has_cancelamento=Exists(
                    CancelamentoImpressao.objects.filter(
                        documento=OuterRef("id")
                    )
                )
            ).order_by('-dataCadastro')  # Ordena por data de cadastro (mais recente primeiro)

            # Calcular estatísticas (antes da paginação)
            total_docs = docs.count()
            validated_docs = docs.filter(status=StatusChoices.VALIDADO).count()
            pending_docs = docs.filter(status=StatusChoices.PENDENTE).count()
            
            # Calcular total de cupons
            total_cupons = 0
            for doc in docs:
                if doc.status == StatusChoices.VALIDADO:
                    total_cupons += doc.get_cupons()

            # Paginação
            paginator = Paginator(docs, 10)  # 10 documentos por página
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
            # Debug para verificar paginação

            # Adicionar verificação de documentos revertidos diretamente na view
            from participante.models import ReversaoImpressao
            from participante.permissions import is_suporte, is_operador, is_backoffice
            
            documentos_revertidos_ids = []
            documentos_cancelados_ids = []
            
            if not is_suporte(request.user) and not request.user.is_superuser:
                grupo_atual = request.user.groups.first()
                if grupo_atual:
                    usuarios_do_grupo = grupo_atual.user_set.all()
                    documentos_revertidos_ids = list(ReversaoImpressao.objects.filter(
                        usuario__in=usuarios_do_grupo
                    ).values_list('documento_id', flat=True).distinct())
                    documentos_cancelados_ids = list(CancelamentoImpressao.objects.filter(
                        usuario__in=usuarios_do_grupo
                    ).values_list('documento_id', flat=True).distinct())

            return render(
                request,
                "participante/participante_detail_operador.html",
                {
                    "section": "people", 
                    "user": profile, 
                    "docs": page_obj,
                    "page_obj": page_obj,
                    "total_docs": total_docs,
                    "validated_docs": validated_docs,
                    "pending_docs": pending_docs,
                    "total_cupons": total_cupons,
                    "documentos_revertidos_ids": documentos_revertidos_ids,
                    "documentos_cancelados_ids": documentos_cancelados_ids,
                },
            )
        except Exception as e:
            messages.error(request, f"Erro ao buscar participante: {str(e)}")
            return render(
                request,
                "participante/search_by_cpf.html",
                {
                    "section": "search",
                },
            )

    return render(
        request,
        "participante/search_by_cpf.html",
        {
            "section": "search",
        },
    )


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)  # Mudança para permitir staff
def participante_list(request):
    """Lista todos os participantes cadastrados (não colaboradores)"""
    from participante.filters import UserFilter
    
    # Busca apenas participantes normais (não colaboradores, não superusers)
    participantes = Profile.objects.filter(
        user__is_superuser=False,
        is_colaborador=False  # Excluir colaboradores
    ).order_by('-dataCadastro')
    
    # Aplica filtro usando django-filter
    filter_obj = UserFilter(request.GET, queryset=participantes)
    
    # Debug para verificar se a busca está funcionando
    if request.GET:
        pass  # Add debug logic here if needed
    
    context = {
        'filter': filter_obj,
        'total_participantes': participantes.count(),
        'participantes_filtrados': filter_obj.qs.count(),
    }
    
    return render(request, "participante/participante_list.html", context)


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)  # Mudança para permitir staff
@transaction.atomic
def cadastro_participante_operador(request):
    """Cadastro de participantes por operador"""
    if request.method == "POST":
        username = request.POST.get("username")
        
        # Verificar se já existe na tabela User
        try:
            usuario_aux = User.objects.get(username=username)
            if usuario_aux:
                messages.error(
                    request,
                    "Não foi possivel prosseguir! Já existe um participante com este CPF ou Email cadastrado!",
                )
                user_form = UserRegistrationForm()
                profile_form = ProfileRegistrationForm()
                return render(
                    request,
                    "participante/cadastro-participante-operador.html",
                    {"user_form": user_form, "profile_form": profile_form},
                )

        except User.DoesNotExist:
            # Verificar se o CPF já existe na tabela Profile (colaboradores ou participantes)
            if username:
                cpf_limpo = "".join(filter(str.isdigit, username))
                cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
                
                if Profile.objects.filter(
                    Q(CPF=cpf_limpo) | 
                    Q(CPF=cpf_formatado) | 
                    Q(CPF__icontains=cpf_limpo)
                ).exists():
                    messages.error(
                        request,
                        "Não foi possivel prosseguir! Já existe um participante com este CPF ou Email cadastrado!",
                    )
                    user_form = UserRegistrationForm()
                    profile_form = ProfileRegistrationForm()
                    return render(
                        request,
                        "participante/cadastro-participante-operador.html",
                        {"user_form": user_form, "profile_form": profile_form},
                    )
            user_form = UserRegistrationForm(request.POST)
            profile_form = ProfileRegistrationForm(request.POST, files=request.FILES)
            if user_form.is_valid() and profile_form.is_valid():
                # Create a new user object but avoid saving it yet
                new_user = user_form.save(commit=False)
                # Set the chosen password
                new_user.set_password(user_form.cleaned_data["password"])
                # Save the User object
                new_user.save()
                # Create the user profile
                new_profile = profile_form.save(commit=False)
                # Formatar o CPF antes de salvar no Profile
                cpf_limpo = new_user.username
                cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
                new_profile.CPF = cpf_formatado
                new_profile.user = new_user
                
                # Para participantes, definir is_colaborador como False
                new_profile.is_colaborador = False
                
                new_profile.save()

                assunto = (
                    "Cadastro concluído com sucesso! Natal de Luz e Prêmios"
                )
                corpo = "Seu cadastro na promoção Natal de Luz e Prêmios realizado com sucesso!"
                # email_boas_vindas_task.delay(assunto, new_user.email, corpo)

                messages.success(request, f"Participante {new_profile.nome} cadastrado com sucesso! Agora você pode adicionar documentos.")
                return redirect(reverse('participante:adddocfiscalbyop', kwargs={'id': new_user.id}))
            else:
                messages.error(request, "Erro no formulário. Por favor, corrija os erros indicados.")
        except Exception as e:
            messages.error(request, f"Ocorreu um erro inesperado durante o cadastro: {e}")
    else:
        user_form = UserRegistrationForm()
        profile_form = ProfileRegistrationForm()
    return render(
        request,
        "participante/cadastro-participante-operador.html",
        {"user_form": user_form, "profile_form": profile_form},
    )


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
@transaction.atomic
def user_edit_by_id(request, id):
    instance_user = get_object_or_404(User, id=id)
    instance_profile = instance_user.profile  # Correção aqui

    if request.method == "POST":
        profile_form = ProfileEditForm(
            instance=instance_profile, data=request.POST, files=request.FILES
        )

        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Participante atualizado com sucesso")
            return redirect(
                "participante:user_detail", id=id
            )  # Redirecione conforme necessário
        else:
            messages.error(request, "Erro na atualização do perfil do participante")
    else:
        profile_form = ProfileEditForm(instance=instance_profile)

    return render(
        request, "participante/editbyoperador.html", {"profile_form": profile_form}
    )


@transaction.atomic
def editar_cliente_por_operador(request, id):
    """
    View para o operador editar o perfil de um cliente.
    """
    # Busca o cliente pelo ID
    try:
        instance_user = User.objects.get(id=id, is_active=True)
        instance_profile = instance_user.profile
    except User.DoesNotExist:
        messages.error(request, "Usuário não encontrado ou inativo.")
        return redirect("participante:dashboard")

    if request.method == "POST":
        # Formulários preenchidos com os dados enviados
        user_form = UserEditForm(instance=instance_user, data=request.POST)
        profile_form = ProfileEditForm(
            instance=instance_profile, data=request.POST, files=request.FILES
        )

        if user_form.is_valid() and profile_form.is_valid():
            # Salva as alterações
            user_form.save()
            profile_form.save()
            messages.success(
                request, f"Perfil de {instance_profile.nome} atualizado com sucesso."
            )
            return redirect(
                "participante:dashboard"
            )  # Ajuste a URL conforme necessário
        else:
            messages.error(request, "Erro na atualização do perfil do cliente.")
    else:
        # Formulários preenchidos com os dados existentes
        user_form = UserEditForm(instance=instance_user)
        profile_form = ProfileEditForm(instance=instance_profile)

    return render(
        request,
        "participante/editar_cliente.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "cliente": instance_user,
        },
    )


@login_required
@transaction.atomic
@login_required
def edit(request):
    """
    View para edição do perfil do usuário.
    Permite atualizar informações pessoais e de contato.
    """
    if request.method == "POST":
        user_form = UserEditForm(instance=request.user, data=request.POST)
        profile_form = ProfileEditForm(
            instance=request.user.profile, 
            data=request.POST, 
            files=request.FILES
        )
        
        if user_form.is_valid() and profile_form.is_valid():
            try:
                with transaction.atomic():
                    user = user_form.save()
                    profile = profile_form.save(commit=False)
                    profile.user = user
                    profile.save()
                
                messages.success(request, "Perfil atualizado com sucesso!")
                return redirect("participante:dashboard")
            except Exception as e:
                messages.error(request, "Erro ao salvar as alterações. Por favor, tente novamente.")
                
        else:
            messages.error(request, "Por favor, corrija os erros abaixo.")
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)
    
    return render(
        request,
        "participante/edit.html",  # Usando o template atualizado
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "title": "Editar Perfil",
            "submit_text": "Salvar Alterações"
        }
    )


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def user_detail(request, id):
    # Busca o usuário e o perfil
    user = get_object_or_404(User, id=id, is_active=True)
    profile = get_object_or_404(Profile, user=user)

    # Filtra os documentos do usuário e verifica se tem cupons não impressos
    docs_list = DocumentoFiscal.objects.filter(
        user=user,
    ).annotate(
        has_unprinted_cupons=Exists(
            Cupom.objects.filter(
                documentoFiscal=OuterRef("id"),
                impresso=False,  # Apenas cupons não impressos
            )
        )
    ).order_by('-dataCadastro')  # Ordena por data de cadastro (mais recente primeiro)

    # Adicionar verificação de documentos revertidos diretamente na view
    from participante.models import ReversaoImpressao
    from participante.permissions import is_suporte, is_operador, is_backoffice
    
    documentos_revertidos_ids = []
    
    if not is_suporte(request.user) and (is_operador(request.user) or is_backoffice(request.user)):
        grupo_atual = request.user.groups.first()
        if grupo_atual:
            usuarios_do_grupo = grupo_atual.user_set.all()
            documentos_revertidos_ids = list(ReversaoImpressao.objects.filter(
                usuario__in=usuarios_do_grupo
            ).values_list('documento_id', flat=True).distinct())

    return render(
        request,
        "participante/participante_detail_operador.html",
        {"section": "people", "user": profile, "docs": docs_list, "documentos_revertidos_ids": documentos_revertidos_ids},
    )


@login_required
@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)  # Mudança para permitir staff
def print_detail(request):
    # Filtra documentos com cupons não impressos
    docs_list = (
        DocumentoFiscal.objects.filter(
            pendente=False,
            status=True,
            # enviado_por_operador=False,
            rel_cupom_doc__impresso=False,  # Substitua "rel_cupom_doc" pelo related_name configurado
        )
        .distinct()
        .order_by("-dataCadastro")
    )

    # Paginação
    docs_list = Paginator(docs_list, 100)
    page = docs_list.page(request.GET.get("page", "1"))
    

    return render(
        request, "participante/print_detail.html", {"section": "people", "docs": page}
    )


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@transaction.atomic
def user_edit(request, id):
    
    # Busca o usuário e o perfil relacionados ao ID
    instance_user = get_object_or_404(User, id=id)
    instance_profile = get_object_or_404(Profile, user=instance_user)

    if request.method == "POST":
        # Formulários preenchidos com os dados enviados pelo POST
        user_form = UserEditForm(instance=instance_user, data=request.POST)
        profile_form = ProfileEditForm(
            instance=instance_profile, data=request.POST, files=request.FILES
        )

        # Verifica se ambos os formulários são válidos
        if user_form.is_valid() and profile_form.is_valid():
            # Salva os dados do formulário
            user_form.save()
            profile_form.save()
            messages.success(request, "Participante atualizado com sucesso")
            return redirect("participante:dashboard")
        else:
            messages.error(request, "Erro na validação do Participante")
    else:
        # Instancia os formulários para exibir os dados atuais
        user_form = UserEditForm(instance=instance_user)
        profile_form = ProfileEditForm(instance=instance_profile)

    # Renderiza o template com os formulários
    return render(
        request,
        "participante/editbyoperador.html",
        {"user_form": user_form, "profile_form": profile_form},
    )


@require_POST
def search_cpf_ajax(request):
    """
    View para busca de CPF via AJAX - retorna dados do participante em JSON
    """
    from django.http import JsonResponse
    import re
    
    cpf = request.POST.get('cpf', '').strip()
    
    if not cpf:
        return JsonResponse({
            'success': False,
            'message': 'CPF não informado'
        })
    
    # Remove todos os caracteres não numéricos do CPF
    cpf_limpo = re.sub(r'\D', '', cpf)
    
    if len(cpf_limpo) != 11:
        return JsonResponse({
            'success': False,
            'message': 'CPF deve ter 11 dígitos'
        })
    
    try:
        # Busca o perfil do participante
        profile = Profile.objects.filter(
            Q(CPF=cpf_limpo) |  # CPF sem formatação
            Q(CPF__icontains=cpf_limpo)  # CPF em qualquer formato que contenha os números
        ).filter(
            user__is_superuser=False,  # Excluir superusers
            is_colaborador=False       # Excluir colaboradores
        ).first()
        
        if not profile:
            return JsonResponse({
                'success': False,
                'message': 'CPF não encontrado na base de dados'
            })
        
        # Retorna os dados do participante
        data = {
            'nome': profile.nome,
            'email': profile.user.email,
            'telefone': profile.whatsapp or profile.foneCelular1 or profile.foneFixo,
            'endereco': profile.endereco,
            'bairro': profile.bairro,
            'cidade': profile.cidade,
            'estado': profile.estado,
            'cep': profile.CEP,
            'data_nascimento': profile.date_of_birth.strftime('%Y-%m-%d') if profile.date_of_birth else None,
        }
        
        return JsonResponse({
            'success': True,
            'data': data,
            'message': 'Dados encontrados com sucesso'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao buscar CPF: {str(e)}'
        })


def cadastro_publico(request, hash_url):
    """
    View para cadastro público de colaboradores via URL de treinamento.
    
    Funcionalidades:
    - Cadastro público sem autenticação
    - Validação de URL ativa
    - Formulário simplificado para mobile
    - Redirecionamento para página de sucesso
    - Associação automática à URL de treinamento
    
    Permissões: Público (sem autenticação)
    Tags: treinamento, cadastro, publico, colaboradores
    """
    from participante.models import URLTreinamento, Profile
    from participante.forms import UserRegistrationForm
    from django.contrib.auth.models import User
    from django.contrib import messages
    from django.db import transaction
    from django.shortcuts import render, redirect
    from django.conf import settings
    
    # Verificar se a URL de treinamento existe e está ativa
    try:
        url_treinamento = URLTreinamento.objects.get(hash_url=hash_url, ativo=True)
    except URLTreinamento.DoesNotExist:
        return render(request, "participante/url_invalida.html", {
            'mensagem': 'URL de treinamento não encontrada ou inativa.'
        })
    
    if request.method == "POST":
        # Criar formulário com dados do POST
        user_form = UserRegistrationForm(request.POST)
        
        # Dados do perfil
        nome = request.POST.get('nome', '')
        whatsapp = request.POST.get('whatsapp', '')
        
        # Validar dados obrigatórios
        if not nome:
            messages.error(request, "Nome é obrigatório.")
        elif user_form.is_valid():
            try:
                with transaction.atomic():
                    # Criar usuário
                    new_user = user_form.save(commit=False)
                    new_user.set_password(user_form.cleaned_data["password"])
                    new_user.is_staff = True  # Marcar como colaborador
                    new_user.save()
                    
                    # Criar perfil
                    new_profile = Profile.objects.create(
                        user=new_user,
                        nome=nome,
                        whatsapp=whatsapp,
                        CPF=f"{new_user.username[:3]}.{new_user.username[3:6]}.{new_user.username[6:9]}-{new_user.username[9:]}",
                        is_colaborador=True,
                        status_ativo=False,  # Começa inativo
                        sexo='P',  # Padrão
                        pergunta='liquida_teresina_2025'  # Padrão
                    )
                    
                    # Associar à URL de treinamento
                    url_treinamento.colaboradores_cadastrados.add(new_profile)
                    
                    messages.success(request, f"✅ Cadastro realizado com sucesso! Aguarde a ativação do seu perfil.")
                    return redirect('participante:cadastro_sucesso', hash_url=hash_url)
                    
            except Exception as e:
                messages.error(request, f"Erro durante o cadastro: {str(e)}")
        else:
            # Mostrar erros de validação
            for field, errors in user_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        user_form = UserRegistrationForm()
    
    context = {
        'url_treinamento': url_treinamento,
        'user_form': user_form,
        'hash_url': hash_url
    }
    
    return render(request, "participante/cadastro_publico.html", context)


def cadastro_sucesso(request, hash_url):
    """
    View para página de sucesso após cadastro público.
    
    Funcionalidades:
    - Página de confirmação
    - Informações sobre próximos passos
    - Link para voltar ao treinamento
    
    Permissões: Público
    Tags: treinamento, sucesso, cadastro
    """
    from participante.models import URLTreinamento
    
    try:
        url_treinamento = URLTreinamento.objects.get(hash_url=hash_url)
    except URLTreinamento.DoesNotExist:
        url_treinamento = None
    
    context = {
        'url_treinamento': url_treinamento,
        'hash_url': hash_url
    }
    
    return render(request, "participante/cadastro_sucesso.html", context)


def exibir_aviso(request):
    """
    View para exibir avisos e mensagens de erro de forma elegante.
    Pode ser chamada com parâmetros GET ou POST para exibir diferentes tipos de mensagens.
    """
    # Obter parâmetros da URL ou da sessão
    titulo = request.GET.get('titulo') or request.session.get('aviso_titulo')
    mensagem = request.GET.get('mensagem') or request.session.get('aviso_mensagem')
    tipo = request.GET.get('tipo') or request.session.get('aviso_tipo', 'info')
    detalhes = request.GET.get('detalhes') or request.session.get('aviso_detalhes')
    acao_primaria = request.GET.get('acao_primaria') or request.session.get('aviso_acao_primaria')
    acao_primaria_url = request.GET.get('acao_primaria_url') or request.session.get('aviso_acao_primaria_url')
    acao_primaria_icone = request.GET.get('acao_primaria_icone') or request.session.get('aviso_acao_primaria_icone')
    acao_secundaria = request.GET.get('acao_secundaria') or request.session.get('aviso_acao_secundaria')
    acao_secundaria_url = request.GET.get('acao_secundaria_url') or request.session.get('aviso_acao_secundaria_url')
    acao_secundaria_icone = request.GET.get('acao_secundaria_icone') or request.session.get('aviso_acao_secundaria_icone')
    mostrar_voltar = request.GET.get('mostrar_voltar') or request.session.get('aviso_mostrar_voltar', True)
    
    # Limpar dados da sessão após usar
    session_keys = [
        'aviso_titulo', 'aviso_mensagem', 'aviso_tipo', 'aviso_detalhes',
        'aviso_acao_primaria', 'aviso_acao_primaria_url', 'aviso_acao_primaria_icone',
        'aviso_acao_secundaria', 'aviso_acao_secundaria_url', 'aviso_acao_secundaria_icone',
        'aviso_mostrar_voltar'
    ]
    for key in session_keys:
        request.session.pop(key, None)
    
    # Se não há mensagem, redirecionar para home
    if not mensagem:
        return redirect('/')
    
    context = {
        'titulo': titulo,
        'mensagem': mensagem,
        'tipo': tipo,
        'detalhes': detalhes,
        'acao_primaria': acao_primaria,
        'acao_primaria_url': acao_primaria_url,
        'acao_primaria_icone': acao_primaria_icone,
        'acao_secundaria': acao_secundaria,
        'acao_secundaria_url': acao_secundaria_url,
        'acao_secundaria_icone': acao_secundaria_icone,
        'mostrar_voltar': mostrar_voltar,
    }
    
    return render(request, 'participante/aviso.html', context)


def redirecionar_aviso(request, titulo, mensagem, tipo='info', **kwargs):
    """
    Função auxiliar para redirecionar para a página de aviso com os parâmetros corretos.
    Pode ser usada em outras views para redirecionar para avisos elegantes.
    """
    # Armazenar dados na sessão para evitar URLs muito longas
    request.session['aviso_titulo'] = titulo
    request.session['aviso_mensagem'] = mensagem
    request.session['aviso_tipo'] = tipo
    
    for key, value in kwargs.items():
        if key.startswith('aviso_'):
            request.session[key] = value
        else:
            request.session[f'aviso_{key}'] = value
    
    return redirect('participante:exibir_aviso')


def exemplo_uso_aviso_elegante(request):
    """
    Exemplo de como usar a nova funcionalidade de aviso elegante.
    Esta função demonstra diferentes cenários de uso.
    """
    # Exemplo 1: Erro de validação
    if request.GET.get('tipo') == 'erro_validacao':
        return redirecionar_aviso(
            request,
            titulo="Erro de Validação",
            mensagem="Os dados informados não são válidos. Verifique as informações e tente novamente.",
            tipo="error",
            acao_primaria="Corrigir Dados",
            acao_primaria_url="/cadastros/",
            acao_primaria_icone="edit",
            acao_secundaria="Voltar",
            acao_secundaria_url="/",
            acao_secundaria_icone="arrow-left"
        )
    
    # Exemplo 2: Aviso de manutenção
    elif request.GET.get('tipo') == 'manutencao':
        return redirecionar_aviso(
            request,
            titulo="Sistema em Manutenção",
            mensagem="O sistema está passando por manutenção programada. Tente novamente em alguns minutos.",
            tipo="warning",
            acao_primaria="Tentar Novamente",
            acao_primaria_url="/",
            acao_primaria_icone="refresh",
            detalhes="Manutenção programada das 02:00 às 04:00"
        )
    
    # Exemplo 3: Sucesso com informações
    elif request.GET.get('tipo') == 'sucesso':
        return redirecionar_aviso(
            request,
            titulo="Operação Concluída",
            mensagem="Sua operação foi realizada com sucesso!",
            tipo="info",
            acao_primaria="Continuar",
            acao_primaria_url="/dashboard/",
            acao_primaria_icone="check",
            detalhes="Um email de confirmação foi enviado para seu endereço cadastrado."
        )
    
    # Exemplo 4: Acesso negado
    elif request.GET.get('tipo') == 'acesso_negado':
        return redirecionar_aviso(
            request,
            titulo="Acesso Negado",
            mensagem="Você não tem permissão para acessar esta área.",
            tipo="error",
            acao_primaria="Ir para Home",
            acao_primaria_url="/",
            acao_primaria_icone="home",
            acao_secundaria="Contatar Suporte",
            acao_secundaria_url="mailto:suporte@exemplo.com",
            acao_secundaria_icone="envelope"
        )
    
    # Exemplo padrão
    else:
        return redirecionar_aviso(
            request,
            titulo="Exemplo de Aviso",
            mensagem="Esta é uma demonstração da nova funcionalidade de avisos elegantes.",
            tipo="info",
            acao_primaria="Entendi",
            acao_primaria_url="/",
            acao_primaria_icone="check"
        )


def exemplo_uso_direto_aviso(request):
    """
    Exemplo de como usar a view de aviso diretamente com parâmetros GET.
    Útil para casos onde você quer passar parâmetros via URL.
    """
    # Esta função demonstra como usar a view diretamente
    # Exemplo de URL: /aviso/?titulo=Teste&mensagem=Esta é uma mensagem&tipo=warning
    return exibir_aviso(request)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def auditoria_view(request):
    """
    View para visualizar registros de auditoria.
    Apenas superusuários e staff podem acessar.
    """
    from participante.models import Auditoria
    from django.core.paginator import Paginator
    
    # Filtros
    usuario_filtro = request.GET.get('usuario', '')
    tipo_acao_filtro = request.GET.get('tipo_acao', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    documento_filtro = request.GET.get('documento', '')
    
    # Query base
    auditorias = Auditoria.objects.select_related('usuario', 'documento_fiscal').all()
    
    # Aplicar filtros
    if usuario_filtro:
        auditorias = auditorias.filter(usuario__username__icontains=usuario_filtro)
    
    if tipo_acao_filtro:
        auditorias = auditorias.filter(tipo_acao=tipo_acao_filtro)
    
    if data_inicio:
        try:
            from datetime import datetime
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
            auditorias = auditorias.filter(data_hora__date__gte=data_inicio_obj.date())
        except ValueError:
            pass
    
    if data_fim:
        try:
            from datetime import datetime
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
            auditorias = auditorias.filter(data_hora__date__lte=data_fim_obj.date())
        except ValueError:
            pass
    
    if documento_filtro:
        auditorias = auditorias.filter(documento_fiscal__numeroDocumento__icontains=documento_filtro)
    
    # Paginação
    paginator = Paginator(auditorias, 50)  # 50 registros por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estatísticas
    total_registros = auditorias.count()
    registros_hoje = auditorias.filter(data_hora__date=timezone.now().date()).count()
    
    context = {
        'page_obj': page_obj,
        'total_registros': total_registros,
        'registros_hoje': registros_hoje,
        'tipos_acao': Auditoria.TIPO_ACAO_CHOICES,
        'filtros': {
            'usuario': usuario_filtro,
            'tipo_acao': tipo_acao_filtro,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'documento': documento_filtro,
        }
    }
    
    return render(request, 'participante/auditoria.html', context)


