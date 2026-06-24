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
def cadastrar_colaborador(request):

    """
    View para cadastrar novos colaboradores da equipe interna.
    
    Funcionalidades:
    - Cadastro de colaboradores usando formulário de registro
    - Marca automaticamente como staff e colaborador
    - Status inativo até ser configurado pelo RH
    
    Permissões: superuser, staff
    Tags: gestao, colaboradores, cadastro
    """
    from participante.forms import UserRegistrationForm, ProfileRegistrationForm
    from participante.models import Profile
    from django.contrib.auth.models import User
    from django.contrib import messages
    from django.db import transaction, IntegrityError
    from django.urls import reverse
    
    # Verificar se usuário tem permissão
    # DEBUG: Temporariamente permitir superuser ou staff
    if not (request.user.is_superuser or request.user.is_staff):
        if not user_has_card_permission(request.user, 'adicionar_colaboradores'):
            messages.error(request, "Você não tem permissão para adicionar colaboradores.")
            return redirect('lojista:homepage')
    
    if request.method == "POST":
        
        user_form = UserRegistrationForm(request.POST)
        profile_form = ProfileRegistrationForm(request.POST, files=request.FILES)
        
        # Para colaboradores, definir valores padrão para campos obrigatórios
        if 'sexo' not in request.POST:
            profile_form.data = profile_form.data.copy()
            profile_form.data['sexo'] = 'P'  # Prefiro não dizer
        
        if 'pergunta' not in request.POST:
            profile_form.data = profile_form.data.copy()
            profile_form.data['pergunta'] = 'liquida_teresina_2025'  # Valor padrão
        
        # Para colaboradores, não exigir password2 (confirmação de senha)
        if 'password2' not in request.POST:
            user_form.data = user_form.data.copy()
            user_form.data['password2'] = user_form.data.get('password', '')  # Usar a mesma senha

        # Get raw data to check for duplicates before full validation
        username = user_form.data.get('username')
        email = user_form.data.get('email')

        if username and User.objects.filter(username=username).exists():
            user_form.add_error('username', "Este CPF já está cadastrado no sistema.")
        
        if email and User.objects.filter(email=email).exists():
            user_form.add_error('email', "Este e-mail já está cadastrado no sistema.")

        # Now, validate both forms. If we added an error above, is_valid() will be False.
        if user_form.is_valid() and profile_form.is_valid():
            try:
                with transaction.atomic():
                    # If we get here, forms are valid and no duplicates were found
                    new_user = user_form.save(commit=False)
                    new_user.set_password(user_form.cleaned_data["password"])
                    # Marcar como staff (colaborador)
                    new_user.is_staff = True
                    new_user.save()

                    new_profile = profile_form.save(commit=False)
                    # Formatar o CPF antes de salvar no Profile
                    cpf_limpo = new_user.username
                    cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
                    new_profile.CPF = cpf_formatado
                    new_profile.user = new_user
                    
                    # Marcar como colaborador
                    new_profile.is_colaborador = True
                    # Colaboradores começam com status inativo até serem configurados
                    new_profile.status_ativo = False
                    
                    new_profile.save()

                    messages.success(request, f"Colaborador {new_profile.nome} cadastrado com sucesso! Você pode atribuir funções na página de gerenciamento de usuários.")
                    
                    return redirect('lojista:homepage')

            except Exception as e:
                # Add a generic error if something unexpected happens during save
                user_form.add_error(None, f"Ocorreu um erro inesperado durante o cadastro: {e}")
        
        # If we reach this point, it's because the forms were invalid from the start,
        # or we added a duplicate error. Render the page again with the forms
        # containing the error messages.
        if not (user_form.is_valid() and profile_form.is_valid()):
            # Mostrar os erros específicos na mensagem
            error_details = []
            
            if not user_form.is_valid():
                for field, errors in user_form.errors.items():
                    for error in errors:
                        error_details.append(f"User form - {field}: {error}")
            
            if not profile_form.is_valid():
                for field, errors in profile_form.errors.items():
                    for error in errors:
                        error_details.append(f"Profile form - {field}: {error}")
            
            # Mostrar os erros específicos na mensagem
            if error_details:
                error_message = "Erros encontrados:<br/>" + "<br/>".join(error_details[:5])  # Limitar a 5 erros
                messages.error(request, error_message)
            else:
                messages.error(request, "Erro no formulário. Por favor, corrija os erros indicados.")
    else:
        # For a GET request, display a blank form
        user_form = UserRegistrationForm()
        profile_form = ProfileRegistrationForm()
    
    # Buscar roles do usuário para exibir na interface
    from participante.permissions import get_user_roles
    user_roles = get_user_roles(request.user)
    
    
    return render(
        request,
        "lojista/colaboradores.html",
        {
            "user_form": user_form, 
            "profile_form": profile_form,
            "user_roles": user_roles,
        },
    )


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def gerenciar_colaboradores_pendentes(request):
    """
    View para gerenciar colaboradores pendentes de ativação.
    
    Funcionalidades:
    - Lista colaboradores cadastrados mas não ativados
    - Permite ativar colaborador com jornada e grupo
    - Permite rejeitar colaborador (desativa)
    - Configuração inicial de jornada e permissões
    
    Permissões: superuser, staff
    Tags: gestao, colaboradores, rh, ativacao
    """
    from participante.models import Profile, UserRole, SystemRole
    from participante.models import PostoTrabalho, TipoJornada, JornadaColaborador
    from django.contrib.auth.models import Group
    from django.db import transaction
    
    # Buscar colaboradores pendentes
    colaboradores_pendentes = Profile.objects.filter(
        is_colaborador=True,
        status_ativo=False
    ).select_related('user').order_by('dataCadastro')
    
    # Buscar colaboradores ativos para comparação
    colaboradores_ativos = Profile.objects.filter(
        is_colaborador=True,
        status_ativo=True
    ).select_related('user').order_by('-dataCadastro')[:10]
    
    # Dados para formulários
    tipos_jornada = TipoJornada.objects.filter(ativo=True).order_by('nome')
    roles = Group.objects.all().order_by('name')  # Usar grupos do Django em vez de SystemRole
    grupos = Group.objects.all().order_by('name')
    
    if request.method == "POST":
        action = request.POST.get('action')
        colaborador_id = request.POST.get('colaborador_id')
        
        try:
            colaborador = Profile.objects.get(id=colaborador_id, is_colaborador=True)
            
            if action == 'ativar':
                with transaction.atomic():
                    # Configurar jornada
                    jornada_id = request.POST.get('tipo_jornada')
                    if jornada_id:
                        jornada = TipoJornada.objects.get(id=jornada_id)
                        # Verificar se já existe jornada para este colaborador na data atual
                        data_inicio = timezone.now().date()
                        jornada_existente, created = JornadaColaborador.objects.get_or_create(
                            colaborador=colaborador.user,
                            data_inicio=data_inicio,
                            defaults={'tipo_jornada': jornada}
                        )
                        # Se já existia, atualizar o tipo de jornada
                        if not created:
                            jornada_existente.tipo_jornada = jornada
                            jornada_existente.save()
                    
                    # Configurar role/grupo
                    role_id = request.POST.get('role')
                    if role_id:
                        grupo = Group.objects.get(id=role_id)
                        colaborador.user.groups.add(grupo)
                    
                    # Ativar colaborador
                    colaborador.status_ativo = True
                    colaborador.save()
                    
                    messages.success(request, f"Colaborador {colaborador.nome} ativado com sucesso!")
                    
            elif action == 'rejeitar':
                # Marcar como inativo e remover is_colaborador
                colaborador.status_ativo = False
                colaborador.is_colaborador = False
                colaborador.save()
                
                # Desativar usuário
                colaborador.user.is_active = False
                colaborador.user.save()
                
                messages.warning(request, f"Colaborador {colaborador.nome} rejeitado e desativado.")
                
        except Profile.DoesNotExist:
            messages.error(request, "Colaborador não encontrado.")
        except Exception as e:
            messages.error(request, f"Erro ao processar ação: {str(e)}")
    
    context = {
        'colaboradores_pendentes': colaboradores_pendentes,
        'colaboradores_ativos': colaboradores_ativos,
        'tipos_jornada': tipos_jornada,
        'roles': roles,
        'grupos': grupos,
    }
    
    return render(request, "lojista/colaboradores_pendentes.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def cadastrar_colaboradores_massa(request):
    """
    View para cadastro em massa de colaboradores durante treinamentos/eventos.
    
    Funcionalidades:
    - Cadastro múltiplo sem redirecionamento
    - Lista de colaboradores cadastrados recentemente
    - Suporte a URL com hash para acesso direto
    - Interface otimizada para cadastros em lote
    - QR Code pode direcionar para esta rota
    
    Permissões: superuser, staff
    Tags: gestao, colaboradores, cadastro, massa, treinamento
    """
    from participante.forms import UserRegistrationForm, ProfileRegistrationForm
    from participante.models import Profile
    from django.contrib.auth.models import User
    from django.contrib import messages
    from django.db import transaction, IntegrityError
    from django.urls import reverse
    
    # Verificar se usuário tem permissão
    if not (request.user.is_superuser or request.user.is_staff):
        if not user_has_card_permission(request.user, 'adicionar_colaboradores'):
            messages.error(request, "Você não tem permissão para adicionar colaboradores.")
            return redirect('lojista:homepage')
    
    # Buscar colaboradores cadastrados recentemente (últimos 10)
    colaboradores_recentes = Profile.objects.filter(
        is_colaborador=True
    ).select_related('user').order_by('-dataCadastro')[:10]
    
    if request.method == "POST":
        user_form = UserRegistrationForm(request.POST)
        profile_form = ProfileRegistrationForm(request.POST, files=request.FILES)
        
        # Para colaboradores, definir valores padrão para campos obrigatórios
        if 'sexo' not in request.POST:
            profile_form.data = profile_form.data.copy()
            profile_form.data['sexo'] = 'P'  # Prefiro não dizer
        
        if 'pergunta' not in request.POST:
            profile_form.data = profile_form.data.copy()
            profile_form.data['pergunta'] = 'liquida_teresina_2025'  # Valor padrão
        
        # Para colaboradores, não exigir password2 (confirmação de senha)
        if 'password2' not in request.POST:
            user_form.data = user_form.data.copy()
            user_form.data['password2'] = user_form.data.get('password', '')  # Usar a mesma senha

        # Get raw data to check for duplicates before full validation
        username = user_form.data.get('username')
        email = user_form.data.get('email')

        if username and User.objects.filter(username=username).exists():
            user_form.add_error('username', "Este CPF já está cadastrado no sistema.")
        
        if email and User.objects.filter(email=email).exists():
            user_form.add_error('email', "Este e-mail já está cadastrado no sistema.")

        # Now, validate both forms. If we added an error above, is_valid() will be False.
        if user_form.is_valid() and profile_form.is_valid():
            try:
                with transaction.atomic():
                    # If we get here, forms are valid and no duplicates were found
                    new_user = user_form.save(commit=False)
                    new_user.set_password(user_form.cleaned_data["password"])
                    # Marcar como staff (colaborador)
                    new_user.is_staff = True
                    new_user.save()

                    new_profile = profile_form.save(commit=False)
                    # Formatar o CPF antes de salvar no Profile
                    cpf_limpo = new_user.username
                    cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
                    new_profile.CPF = cpf_formatado
                    new_profile.user = new_user
                    
                    # Marcar como colaborador
                    new_profile.is_colaborador = True
                    # Colaboradores começam com status inativo até serem configurados
                    new_profile.status_ativo = False
                    
                    new_profile.save()

                    messages.success(request, f"✅ Colaborador {new_profile.nome} cadastrado com sucesso!")
                    
                    # Limpar formulário para próximo cadastro
                    user_form = UserRegistrationForm()
                    profile_form = ProfileRegistrationForm()
                    
                    # Atualizar lista de colaboradores recentes
                    colaboradores_recentes = Profile.objects.filter(
                        is_colaborador=True
                    ).select_related('user').order_by('-dataCadastro')[:10]

            except Exception as e:
                # Add a generic error if something unexpected happens during save
                user_form.add_error(None, f"Ocorreu um erro inesperado durante o cadastro: {e}")
        
        # If we reach this point, it's because the forms were invalid from the start,
        # or we added a duplicate error. Render the page again with the forms
        # containing the error messages.
        if not (user_form.is_valid() and profile_form.is_valid()):
            # DEBUG: Mostrar erros específicos
            error_details = []
            
            if not user_form.is_valid():
                for field, errors in user_form.errors.items():
                    for error in errors:
                        error_details.append(f"User form - {field}: {error}")
            
            if not profile_form.is_valid():
                for field, errors in profile_form.errors.items():
                    for error in errors:
                        error_details.append(f"Profile form - {field}: {error}")
            
            # Mostrar os erros específicos na mensagem
            if error_details:
                error_message = "Erros encontrados:<br/>" + "<br/>".join(error_details[:5])  # Limitar a 5 erros
                messages.error(request, error_message)
            else:
                messages.error(request, "Erro no formulário. Por favor, corrija os erros indicados.")
    else:
        # For a GET request, display a blank form
        user_form = UserRegistrationForm()
        profile_form = ProfileRegistrationForm()
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'colaboradores_recentes': colaboradores_recentes,
        'total_cadastrados': colaboradores_recentes.count(),
        'hash_url': request.GET.get('hash', ''),
        'section': 'colaboradores_massa'
    }
    
    return render(request, "lojista/colaboradores_massa.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def upload_colaboradores_lote(request):
    """
    View para upload em lote de colaboradores via planilha CSV/Excel.
    
    Funcionalidades:
    - Upload de arquivo CSV/Excel com dados dos colaboradores
    - Validação em lote dos dados
    - Processamento assíncrono para grandes volumes
    - Relatório detalhado de sucessos e erros
    - Template para download da planilha modelo
    - Suporte a diferentes formatos de arquivo
    
    Permissões: superuser, staff
    Tags: gestao, colaboradores, upload, lote, planilha
    """
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    from django.db import transaction
    from django.contrib.auth.models import User
    from participante.models import Profile
    import csv
    import io
    from datetime import datetime
    
    # Verificar se usuário tem permissão
    if not (request.user.is_superuser or request.user.is_staff):
        if not user_has_card_permission(request.user, 'adicionar_colaboradores'):
            messages.error(request, "Você não tem permissão para adicionar colaboradores.")
            return redirect('lojista:homepage')
    
    if request.method == "POST":
        uploaded_file = request.FILES.get('arquivo_colaboradores')
        
        if not uploaded_file:
            messages.error(request, "Por favor, selecione um arquivo para upload.")
        else:
            # Validar tipo de arquivo
            if not uploaded_file.name.endswith(('.csv', '.xlsx', '.xls')):
                messages.error(request, "Formato de arquivo não suportado. Use CSV ou Excel.")
            else:
                try:
                    # Processar arquivo CSV
                    if uploaded_file.name.endswith('.csv'):
                        # Decodificar arquivo CSV
                        content = uploaded_file.read().decode('utf-8')
                        csv_reader = csv.DictReader(io.StringIO(content))
                        
                        sucessos = 0
                        erros = []
                        
                        for row_num, row in enumerate(csv_reader, start=2):  # Começar do 2 (linha 1 é cabeçalho)
                            try:
                                # Validar dados obrigatórios
                                if not row.get('cpf') or not row.get('nome') or not row.get('email'):
                                    erros.append(f"Linha {row_num}: CPF, nome e email são obrigatórios")
                                    continue
                                
                                # Verificar se CPF já existe
                                cpf_limpo = ''.join(filter(str.isdigit, row['cpf']))
                                if User.objects.filter(username=cpf_limpo).exists():
                                    erros.append(f"Linha {row_num}: CPF {row['cpf']} já cadastrado")
                                    continue
                                
                                # Verificar se email já existe
                                if User.objects.filter(email=row['email']).exists():
                                    erros.append(f"Linha {row_num}: Email {row['email']} já cadastrado")
                                    continue
                                
                                # Criar usuário
                                with transaction.atomic():
                                    user = User.objects.create_user(
                                        username=cpf_limpo,
                                        email=row['email'],
                                        password=row.get('senha', '123456')  # Senha padrão
                                    )
                                    user.is_staff = True
                                    user.save()
                                    
                                    # Criar perfil
                                    profile = Profile.objects.create(
                                        user=user,
                                        nome=row['nome'],
                                        CPF=f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}",
                                        whatsapp=row.get('telefone', ''),
                                        endereco=row.get('endereco', ''),
                                        bairro=row.get('bairro', ''),
                                        cidade=row.get('cidade', ''),
                                        estado=row.get('estado', ''),
                                        date_of_birth=datetime.strptime(row.get('data_nascimento', '1990-01-01'), '%Y-%m-%d').date() if row.get('data_nascimento') else None,
                                        is_colaborador=True,
                                        status_ativo=False,
                                        sexo=row.get('sexo', 'P'),
                                        pergunta='liquida_teresina_2025'
                                    )
                                    
                                    sucessos += 1
                                    
                            except Exception as e:
                                erros.append(f"Linha {row_num}: Erro - {str(e)}")
                        
                        # Mostrar resultados
                        if sucessos > 0:
                            messages.success(request, f"✅ {sucessos} colaborador(es) cadastrado(s) com sucesso!")
                        
                        if erros:
                            error_msg = f"❌ {len(erros)} erro(s) encontrado(s):<br/>" + "<br/>".join(erros[:10])
                            if len(erros) > 10:
                                error_msg += f"<br/>... e mais {len(erros) - 10} erro(s)"
                            messages.error(request, error_msg)
                    
                    else:
                        messages.error(request, "Processamento de arquivos Excel será implementado em breve.")
                        
                except Exception as e:
                    messages.error(request, f"Erro ao processar arquivo: {str(e)}")
    
    # Buscar estatísticas de uploads recentes
    colaboradores_recentes = Profile.objects.filter(
        is_colaborador=True
    ).select_related('user').order_by('-dataCadastro')[:5]
    
    context = {
        'colaboradores_recentes': colaboradores_recentes,
        'total_cadastrados': colaboradores_recentes.count(),
        'section': 'colaboradores_upload'
    }
    
    return render(request, "lojista/colaboradores_upload.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def cadastrar_colaborador_rapido(request):
    """
    View para cadastro rápido de colaboradores com formulário minimalista.
    
    Funcionalidades:
    - Formulário simplificado com apenas campos essenciais
    - Cadastro rápido para situações urgentes
    - Campos opcionais podem ser preenchidos posteriormente
    - Interface otimizada para cadastros rápidos
    - Redirecionamento para edição posterior
    
    Permissões: superuser, staff
    Tags: gestao, colaboradores, cadastro, rapido, urgente
    """
    from participante.forms import UserRegistrationForm, ProfileRegistrationForm
    from participante.models import Profile
    from django.contrib.auth.models import User
    from django.contrib import messages
    from django.db import transaction, IntegrityError
    from django.urls import reverse
    
    # Verificar se usuário tem permissão
    if not (request.user.is_superuser or request.user.is_staff):
        if not user_has_card_permission(request.user, 'adicionar_colaboradores'):
            messages.error(request, "Você não tem permissão para adicionar colaboradores.")
            return redirect('lojista:homepage')
    
    if request.method == "POST":
        # Criar formulários com apenas campos essenciais
        user_form = UserRegistrationForm(request.POST)
        
        # Para cadastro rápido, apenas campos essenciais
        profile_data = {
            'nome': request.POST.get('nome', ''),
            'whatsapp': request.POST.get('whatsapp', ''),
            'sexo': 'P',  # Padrão
            'pergunta': 'liquida_teresina_2025',  # Padrão
        }
        
        profile_form = ProfileRegistrationForm(profile_data)
        
        # Para colaboradores, não exigir password2 (confirmação de senha)
        if 'password2' not in request.POST:
            user_form.data = user_form.data.copy()
            user_form.data['password2'] = user_form.data.get('password', '')  # Usar a mesma senha

        # Get raw data to check for duplicates before full validation
        username = user_form.data.get('username')
        email = user_form.data.get('email')

        if username and User.objects.filter(username=username).exists():
            user_form.add_error('username', "Este CPF já está cadastrado no sistema.")
        
        if email and User.objects.filter(email=email).exists():
            user_form.add_error('email', "Este e-mail já está cadastrado no sistema.")

        # Validar apenas campos essenciais
        if user_form.is_valid() and profile_data['nome']:
            try:
                with transaction.atomic():
                    # If we get here, forms are valid and no duplicates were found
                    new_user = user_form.save(commit=False)
                    new_user.set_password(user_form.cleaned_data["password"])
                    # Marcar como staff (colaborador)
                    new_user.is_staff = True
                    new_user.save()

                    new_profile = Profile.objects.create(
                        user=new_user,
                        nome=profile_data['nome'],
                        whatsapp=profile_data['whatsapp'],
                        CPF=f"{new_user.username[:3]}.{new_user.username[3:6]}.{new_user.username[6:9]}-{new_user.username[9:]}",
                        is_colaborador=True,
                        status_ativo=False,
                        sexo=profile_data['sexo'],
                        pergunta=profile_data['pergunta']
                    )

                    messages.success(request, f"✅ Colaborador {new_profile.nome} cadastrado rapidamente! Complete os dados posteriormente.")
                    
                    # Redirecionar para edição do perfil
                    return redirect('participante:gestao_colaboradores')

            except Exception as e:
                # Add a generic error if something unexpected happens during save
                user_form.add_error(None, f"Ocorreu um erro inesperado durante o cadastro: {e}")
        
        # If we reach this point, it's because the forms were invalid from the start,
        # or we added a duplicate error. Render the page again with the forms
        # containing the error messages.
        if not user_form.is_valid() or not profile_data['nome']:
            # DEBUG: Mostrar erros específicos
            error_details = []
            
            if not user_form.is_valid():
                for field, errors in user_form.errors.items():
                    for error in errors:
                        error_details.append(f"User form - {field}: {error}")
            
            if not profile_data['nome']:
                error_details.append("Nome é obrigatório")
            
            # Mostrar os erros específicos na mensagem
            if error_details:
                error_message = "Erros encontrados:<br/>" + "<br/>".join(error_details[:5])  # Limitar a 5 erros
                messages.error(request, error_message)
            else:
                messages.error(request, "Erro no formulário. Por favor, corrija os erros indicados.")
    else:
        # For a GET request, display a blank form
        user_form = UserRegistrationForm()
    
    context = {
        'user_form': user_form,
        'section': 'colaboradores_rapido'
    }
    
    return render(request, "lojista/colaboradores_rapido.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def criar_url_treinamento(request):
    """
    View para criar nova URL de treinamento.
    
    Funcionalidades:
    - Criar URL com hash único
    - Gerar QR Code automaticamente
    - Configurar título e descrição
    - Controle de ativação
    
    Permissões: superuser, staff
    Tags: treinamento, url, qr-code, colaboradores
    """
    from participante.models import URLTreinamento
    import uuid
    
    if request.method == "POST":
        titulo = request.POST.get('titulo')
        descricao = request.POST.get('descricao')
        
        if titulo and descricao:
            # Gerar hash único
            hash_url = str(uuid.uuid4())[:8]
            
            # Criar URL de treinamento
            url_treinamento = URLTreinamento.objects.create(
                hash_url=hash_url,
                titulo=titulo,
                descricao=descricao,
                criado_por=request.user
            )
            
            messages.success(request, f"✅ URL de treinamento criada com sucesso!")
            return redirect('lojista:gerenciar_urls_treinamento')
        else:
            messages.error(request, "Por favor, preencha todos os campos obrigatórios.")
    
    context = {
        'section': 'criar_url_treinamento'
    }
    
    return render(request, "lojista/criar_url_treinamento.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def gerenciar_urls_treinamento(request):
    """
    View para gerenciar URLs de treinamento.
    
    Funcionalidades:
    - Listar todas as URLs criadas
    - Ativar/desativar URLs
    - Visualizar estatísticas
    - Gerar QR Codes
    
    Permissões: superuser, staff
    Tags: treinamento, gerenciar, urls, colaboradores
    """
    from participante.models import URLTreinamento
    
    # Buscar URLs de treinamento
    urls_treinamento = URLTreinamento.objects.all().order_by('-data_criacao')
    
    # Processar ações
    if request.method == "POST":
        url_id = request.POST.get('url_id')
        action = request.POST.get('action')
        
        if url_id and action:
            try:
                url_treinamento = URLTreinamento.objects.get(id=url_id)
                
                if action == 'ativar':
                    url_treinamento.ativar()
                    messages.success(request, f"✅ URL '{url_treinamento.titulo}' ativada!")
                elif action == 'desativar':
                    url_treinamento.desativar()
                    messages.success(request, f"✅ URL '{url_treinamento.titulo}' desativada!")
                elif action == 'excluir':
                    url_treinamento.delete()
                    messages.success(request, f"✅ URL '{url_treinamento.titulo}' excluída!")
                
                return redirect('lojista:gerenciar_urls_treinamento')
                
            except URLTreinamento.DoesNotExist:
                messages.error(request, "URL de treinamento não encontrada.")
    
    context = {
        'urls_treinamento': urls_treinamento,
        'section': 'gerenciar_urls_treinamento'
    }
    
    return render(request, "lojista/gerenciar_urls_treinamento.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def colaboradores_url_treinamento(request, hash_url):
    """
    View para visualizar colaboradores cadastrados via URL específica.
    
    Funcionalidades:
    - Listar colaboradores por URL
    - Estatísticas de cadastro
    - Exportar dados
    
    Permissões: superuser, staff
    Tags: treinamento, colaboradores, estatisticas
    """
    from participante.models import URLTreinamento
    
    try:
        url_treinamento = URLTreinamento.objects.get(hash_url=hash_url)
        colaboradores = url_treinamento.colaboradores_cadastrados.all().order_by('-dataCadastro')
        
        context = {
            'url_treinamento': url_treinamento,
            'colaboradores': colaboradores,
            'total_colaboradores': colaboradores.count(),
            'section': 'colaboradores_url_treinamento'
        }
        
        return render(request, "lojista/colaboradores_url_treinamento.html", context)
        
    except URLTreinamento.DoesNotExist:
        messages.error(request, "URL de treinamento não encontrada.")
        return redirect('lojista:gerenciar_urls_treinamento')


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def gestao_colaboradores_dashboard(request):
    """
    Dashboard principal de gestão de colaboradores
    - Ações rápidas
    - Acesso a todas as funcionalidades
    - Sem estatísticas (conforme solicitado)
    
    Permissões: superuser, staff
    Tags: gestao, colaboradores, dashboard, rh
    """
    from participante.models import Profile, UserRole, SystemRole
    from participante.models import PostoTrabalho, TipoJornada, JornadaColaborador
    from django.contrib.auth.models import Group
    from django.db.models import Count
    
    # Buscar dados para contexto
    colaboradores_pendentes = Profile.objects.filter(
        is_colaborador=True,
        status_ativo=False
    ).count()
    
    colaboradores_ativos = Profile.objects.filter(
        is_colaborador=True,
        status_ativo=True
    ).count()
    
    # Dados para formulários
    tipos_jornada = TipoJornada.objects.filter(ativo=True).order_by('nome')
    roles = Group.objects.all().order_by('name')  # Usar grupos do Django
    grupos = Group.objects.all().order_by('name')
    postos_trabalho = PostoTrabalho.objects.all().order_by('nome')
    
    context = {
        'colaboradores_pendentes_count': colaboradores_pendentes,
        'colaboradores_ativos_count': colaboradores_ativos,
        'tipos_jornada': tipos_jornada,
        'roles': roles,
        'grupos': grupos,
        'postos_trabalho': postos_trabalho,
    }
    
    return render(request, "lojista/gestao_colaboradores_dashboard.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def configurar_colaborador_unificado(request, colaborador_id=None):
    """
    Página unificada para configurar colaborador
    - Criar novo colaborador
    - Editar colaborador existente
    - Configurar tudo de uma vez
    
    Permissões: superuser, staff
    Tags: gestao, colaboradores, configuracao, rh
    """
    from participante.models import Profile, UserRole, SystemRole
    from participante.models import PostoTrabalho, TipoJornada, JornadaColaborador
    from django.contrib.auth.models import Group
    from django.db import transaction
    from django.utils import timezone
    
    # Dados para formulários
    tipos_jornada = TipoJornada.objects.filter(ativo=True).order_by('nome')
    roles = Group.objects.all().order_by('name')  # Usar grupos do Django
    grupos = Group.objects.all().order_by('name')
    postos_trabalho = PostoTrabalho.objects.all().order_by('nome')
    
    colaborador = None
    is_edit = False
    
    if colaborador_id:
        try:
            colaborador = Profile.objects.get(id=colaborador_id, is_colaborador=True)
            is_edit = True
        except Profile.DoesNotExist:
            messages.error(request, "Colaborador não encontrado.")
            return redirect('lojista:gestao_colaboradores_dashboard')
    
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == 'salvar':
            try:
                with transaction.atomic():
                    # Dados básicos
                    nome = request.POST.get('nome')
                    email = request.POST.get('email')
                    whatsapp = request.POST.get('whatsapp')
                    
                    # Configuração de trabalho
                    posto_id = request.POST.get('posto_trabalho')
                    jornada_id = request.POST.get('tipo_jornada')
                    role_id = request.POST.get('role')
                    data_inicio = request.POST.get('data_inicio')
                    status_ativo = request.POST.get('status_ativo') == 'on'
                    
                    # Configurações de jornada
                    requer_jornada = request.POST.get('requer_jornada') == 'on'
                    jornada_flexivel = request.POST.get('jornada_flexivel') == 'on'
                    
                    if is_edit and colaborador:
                        # Atualizar colaborador existente
                        colaborador.nome = nome
                        colaborador.whatsapp = whatsapp
                        colaborador.status_ativo = status_ativo
                        colaborador.requer_jornada = requer_jornada
                        colaborador.jornada_flexivel = jornada_flexivel
                        
                        # Atualizar posto de trabalho
                        if posto_id:
                            posto = PostoTrabalho.objects.get(id=posto_id)
                            colaborador.posto_trabalho = posto
                        
                        colaborador.save()
                        
                        # Atualizar email do usuário
                        colaborador.user.email = email
                        colaborador.user.save()
                        
                        # Configurar jornada
                        if jornada_id and data_inicio:
                            # Remover jornadas antigas
                            JornadaColaborador.objects.filter(colaborador=colaborador.user).delete()
                            
                            # Criar nova jornada
                            jornada = TipoJornada.objects.get(id=jornada_id)
                            JornadaColaborador.objects.create(
                                colaborador=colaborador.user,
                                tipo_jornada=jornada,
                                data_inicio=data_inicio
                            )
                        
                        # Configurar role
                        if role_id:
                            # Remover roles antigas
                            UserRole.objects.filter(user=colaborador.user).delete()
                            
                            # Configurar grupo
                            grupo = Group.objects.get(id=role_id)
                            colaborador.user.groups.clear()  # Remove grupos antigos
                            colaborador.user.groups.add(grupo)  # Adiciona novo grupo
                        
                        messages.success(request, f"Colaborador {colaborador.nome} atualizado com sucesso!")
                        
                    else:
                        # Criar novo colaborador (implementar se necessário)
                        messages.info(request, "Funcionalidade de criação será implementada em breve.")
                    
                    return redirect('lojista:gestao_colaboradores_dashboard')
                    
            except Exception as e:
                messages.error(request, f"Erro ao salvar colaborador: {str(e)}")
        
        elif action == 'ativar':
            if colaborador:
                try:
                    with transaction.atomic():
                        colaborador.status_ativo = True
                        colaborador.save()
                        messages.success(request, f"Colaborador {colaborador.nome} ativado com sucesso!")
                        return redirect('lojista:gestao_colaboradores_dashboard')
                except Exception as e:
                    messages.error(request, f"Erro ao ativar colaborador: {str(e)}")
        
        elif action == 'rejeitar':
            if colaborador:
                try:
                    with transaction.atomic():
                        colaborador.status_ativo = False
                        colaborador.is_colaborador = False
                        colaborador.save()
                        
                        colaborador.user.is_active = False
                        colaborador.user.save()
                        
                        messages.warning(request, f"Colaborador {colaborador.nome} rejeitado e desativado.")
                        return redirect('lojista:gestao_colaboradores_dashboard')
                except Exception as e:
                    messages.error(request, f"Erro ao rejeitar colaborador: {str(e)}")
    
    context = {
        'colaborador': colaborador,
        'is_edit': is_edit,
        'tipos_jornada': tipos_jornada,
        'roles': roles,
        'grupos': grupos,
        'postos_trabalho': postos_trabalho,
    }
    
    return render(request, "lojista/configurar_colaborador_unificado.html", context)


