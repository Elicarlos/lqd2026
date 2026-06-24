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


@login_required
def doc_fiscal_done(request, doc_id):
    documentoFiscal = get_object_or_404(DocumentoFiscal, id=doc_id)
    return render(
        request,
        "participante/doc_fiscal_done.html",
        {"new_documentoFiscal": documentoFiscal},
    )


@login_required
@user_passes_test(lambda u: u.is_superuser)
@csrf_exempt
def atualizar_status_impresso(request, doc_id):
    if request.method == "POST":
        try:
            doc = DocumentoFiscal.objects.get(id=doc_id)
            doc.impresso = True
            doc.save()
            return JsonResponse(
                {
                    "success": True,
                    "message": "Status atualizado para impresso com sucesso.",
                }
            )
        except DocumentoFiscal.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Documento não encontrado."}
            )
    return JsonResponse({"success": False, "message": "Método inválido."})


@login_required
@user_passes_test(lambda u: u.is_staff)
def update_observacao_docfiscal(request):
    """
    View para o operador atualizar observações de um documento fiscal.
    Ao salvar uma observação, o status do documento é alterado para 'Inconsistente'.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Método não permitido."}, status=405)
        
    doc_id = request.POST.get("doc_id")
    observacao = request.POST.get("observacao", "").strip()
    
    if not doc_id:
        return JsonResponse({"success": False, "message": "ID do documento não informado."}, status=400)

    if not observacao:
        return JsonResponse({"success": False, "message": "A observação não pode estar em branco."}, status=400)

    try:
        doc = get_object_or_404(DocumentoFiscal, id=doc_id)
        doc.observacao = observacao
        doc.status = StatusChoices.INCONSISTENTE
        doc.save()
        
        messages.success(request, f"Documento {doc.numeroDocumento} marcado como inconsistente.")

        return JsonResponse({
            "success": True, 
            "message": "Documento marcado como inconsistente e observação salva!", 
            "status": StatusChoices.INCONSISTENTE
        })
    except Exception as e:
        return JsonResponse({
            "success": False, 
            "message": f"Erro ao atualizar observação: {str(e)}"
        }, status=400)


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


def adddocfiscal_disabled(request):
    return HttpResponseGone("Adição de documento desabilitada no momento.")


@login_required
@transaction.atomic
def adddocfiscal(request):
    # Verificar se o usuário logado é colaborador
    if request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Colaboradores não podem participar da campanha. Esta funcionalidade é restrita a participantes comuns.")
        return redirect("participante:dashboard")
    
    if request.method == "POST":
        documentoFiscal_form = UserAddFiscalDocForm(request.POST, files=request.FILES)

        if documentoFiscal_form.is_valid():
            cnpj = documentoFiscal_form.cleaned_data["lojista_cnpj"]

            try:
                lojista = Lojista.objects.get(CNPJLojista=cnpj)
                if lojista.status == "Sim":
                    new_documentoFiscal = documentoFiscal_form.save(commit=False)
                    new_documentoFiscal.user = request.user
                    new_documentoFiscal.lojista = lojista
                    
                    # Processar valores separados
                    valor_cielo = documentoFiscal_form.cleaned_data.get("valorCielo") or 0
                    valor_outros = documentoFiscal_form.cleaned_data.get("valorOutros") or 0
                    valor_total = valor_cielo + valor_outros
                    
                    new_documentoFiscal.valorCielo = valor_cielo
                    new_documentoFiscal.valorOutros = valor_outros
                    new_documentoFiscal.valorDocumento = valor_total
                    new_documentoFiscal.compradoCielo = valor_cielo > 0
                    
                    # Adicionar campos de rastreabilidade
                    new_documentoFiscal.cadastrado_por = request.user
                    new_documentoFiscal.posto_trabalho = getattr(request.user.profile, 'posto_trabalho', None)
                    new_documentoFiscal.enviado_por_operador = False
                    
                    new_documentoFiscal.save()

                    messages.success(request, "Documento adicionado com sucesso! Aguarde a validação.")

                    return redirect("participante:dashboard")

                elif lojista.status in ["Pendente", "Inativo"]:
                    messages.error(
                        request,
                        f"Não é possivel adicionar documento para lojistas com status '{lojista.status}'.",
                    )

                else:
                    messages.error(
                        request,
                        "Lojista não participante desta campanha. <a href='https://wa.me/5586999950081?text=Ola%20preciso%20de%20suporte' style='color: #FFF'><b>|Informar ao Suporte|</b></a>",
                    )

            except IntegrityError:
                messages.error(
                    request,
                    "Este documento já foi registrado para este lojista pelo usuário.",
                )

            except Lojista.DoesNotExist:
                messages.error(
                    request,
                    "Lojista não cadastrado na base de lojistas do Natal de Luz e Prêmios. <a href='https://wa.me/5586999950081?text=Ola%20preciso%20de%20suporte' style='color: #FFF'><b>|Informar ao Suporte|</b></a>",
                )
        else:
            # Collect all form errors
            error_messages = []
            for field, errors in documentoFiscal_form.errors.items():
                # Try to get the field's label, fall back to the field name
                field_name = documentoFiscal_form.fields.get(field).label if field in documentoFiscal_form.fields else field
                for error in errors:
                    error_messages.append(f"{field_name or 'Campo desconhecido'}: {error}")
            
            messages.error(
                request, 
                "Erro no formulário: " + " | ".join(error_messages)
            )
    else:
        documentoFiscal_form = UserAddFiscalDocForm()

    return render(
        request,
        "participante/doc_fiscal_add-participante.html",
        {"documentoFiscal_form": documentoFiscal_form},
    )


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@transaction.atomic
def adddocfiscalbyop(request, id):
    ## Usado apenas por coloboradores e admins
    """ Rota usada para adicionar documento fiscal por operador """
    # Verificar se o usuário logado tem profile
    if not hasattr(request.user, 'profile'):
        messages.error(request, "Erro: Usuário operador não possui perfil configurado. Entre em contato com o administrador.")
        return redirect("participante:dashboard")

    user = get_object_or_404(User, id=id)
    is_superuser = request.user.is_superuser

    if request.method == "POST":
        try:
            user_aux = User.objects.get(id=id)
            if is_superuser:
                documentoFiscal_form = UserAddFiscalDocFormSuperuser(
                    request.POST
                )
            else:
                # Usar o formulário específico para operadores
                documentoFiscal_form = UserAddFiscalDocFormOperador(
                    request.POST
                )

            if documentoFiscal_form.is_valid():
                cnpj = documentoFiscal_form.cleaned_data["lojista_cnpj"]

                comprado_com_cielo = documentoFiscal_form.cleaned_data.get(
                    "compradoCielo"
                )
                
                from decimal import Decimal
                
                # Processar valorOutros (campo temporário do formulário)
                valor_outros = documentoFiscal_form.cleaned_data.get("valorOutros")
                if valor_outros is None:
                    valor_outros = Decimal('0')

                try:
                    lojista = Lojista.objects.get(CNPJLojista=cnpj)
                    

                    # Valida o status do Lojista
                    if lojista.status == "Sim":
                        new_documentoFiscal = documentoFiscal_form.save(commit=False)
                        new_documentoFiscal.user = user_aux
                        new_documentoFiscal.lojista = lojista
                        new_documentoFiscal.posto_trabalho = (
                            getattr(request.user.profile, 'posto_trabalho', None) if hasattr(request.user, 'profile') else None
                        )
                        new_documentoFiscal.enviado_por_operador = True
                        new_documentoFiscal.cadastrado_por = request.user
                        
                        # Processar valores separados
                        valor_cielo = documentoFiscal_form.cleaned_data.get("valorCielo") or 0
                        valor_outros = documentoFiscal_form.cleaned_data.get("valorOutros") or 0
                        valor_total = valor_cielo + valor_outros
                        
                        new_documentoFiscal.valorCielo = valor_cielo
                        new_documentoFiscal.valorOutros = valor_outros
                        new_documentoFiscal.valorDocumento = valor_total
                        new_documentoFiscal.compradoCielo = valor_cielo > 0
                        
                        # Documentos criados por operadores são automaticamente validados
                        new_documentoFiscal.status = StatusChoices.VALIDADO
                        
                        new_documentoFiscal.save()
                        
                        # Gerar cupons automaticamente para documentos criados por operadores
                        cupons_a_gerar = new_documentoFiscal.get_cupons()
                        cupons_criados = 0
                        if cupons_a_gerar > 0:
                            try:
                                # Verificar se o usuário tem posto de trabalho antes de criar cupons
                                if not hasattr(request.user, 'profile') or not request.user.profile.posto_trabalho:
                                    messages.error(request, "Você precisa selecionar um posto de trabalho antes de criar cupons.")
                                    return redirect('participante:selecionar_posto')
                                
                                posto_trabalho = request.user.profile.posto_trabalho
                                cupons = [
                                    Cupom(
                                        documentoFiscal=new_documentoFiscal,
                                        user=new_documentoFiscal.user,
                                        operador=request.user,
                                        posto_trabalho=posto_trabalho,
                                    )
                                    for _ in range(cupons_a_gerar)
                                ]
                                Cupom.objects.bulk_create(cupons)
                                cupons_criados = cupons_a_gerar
                            except Exception as e:
                                # Log do erro mas não falha a criação do documento
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.error(f"Erro ao criar cupons para documento {new_documentoFiscal.id}: {str(e)}")
                                messages.warning(request, f"Documento criado, mas houve erro ao gerar cupons: {str(e)}")

                        # Mensagem de sucesso com informação dos cupons
                        success_msg = "Documento adicionado com sucesso!"
                        if cupons_criados > 0:
                            success_msg += f" {cupons_criados} cupons gerados automaticamente."
                        
                        if lojista.status == "Não" and comprado_com_cielo:
                            messages.success(request, success_msg)
                        else:
                            messages.success(request, success_msg)

                        # Redirecionar para a busca por CPF do participante onde aparecerá o cupom para imprimir
                        cpf = getattr(new_documentoFiscal.user.profile, 'CPF', '') if hasattr(new_documentoFiscal.user, 'profile') else ''
                        return redirect(f"{reverse('participante:search_by_cpf')}?q={cpf}")

                    elif lojista.status in ["Pendente", "Inativo"]:
                        messages.error(
                            request,
                            f"Não é possivel adicionar documentos para lojistas com status '{lojista.status}'.",
                        )

                    else:
                        messages.error(
                            request,
                            "Lojista não participante desta campanha. <a href='https://wa.me/5586999950081?text=Ola%20preciso%20de%20suporte' style='color: #FFF'><b>|Informar ao Suporte|</b></a>",
                        )

                except IntegrityError:
                    messages.error(
                        request,
                        "Este documento já foi registrado para este lojista pelo usuário.",
                    )

                except Lojista.DoesNotExist:
                    messages.error(
                        request,
                        "Lojista não cadastrado na base de lojistas do Natal de Luz e Prêmios. <a href='https://wa.me/5586999950081?text=Ola%20preciso%20de%20suporte' style='color: #FFF'><b>|Informar ao Suporte|</b></a>",
                    )
            else:
                # Collect all form errors
                error_messages = []
                for field, errors in documentoFiscal_form.errors.items():
                    field_name = documentoFiscal_form.fields[field].label or field
                    for error in errors:
                        error_messages.append(f"{field_name}: {error}")
                
                messages.error(
                    request, 
                    "Erro no formulário: " + " | ".join(error_messages)
                )
        except Exception as e:
            messages.error(request, f"Ocorreu um erro inesperado: {e}")
    else:
        if is_superuser:
            documentoFiscal_form = UserAddFiscalDocFormSuperuser()
        else:
            # Usar o formulário específico para operadores
            documentoFiscal_form = UserAddFiscalDocFormOperador()

    return render(
        request,
        "participante/doc_fiscal_add_op.html",
        {"documentoFiscal_form": documentoFiscal_form, "participante": user},
    )


@login_required
def doclist(request):
    docs_list = DocumentoFiscal.objects.filter(user=request.user)
    docs_filter = DocFilter(request.GET, queryset=docs_list)
    return render(
        request,
        "participante/list_doc_fiscal.html",
        {"filter": docs_filter, "section": "docsfiscais"},
    )


@login_required
@transaction.atomic
def editdocfiscal(request, id):
    instance = get_object_or_404(DocumentoFiscal, id=id)
    
    # Verificar se o documento já foi validado
    if instance.status == StatusChoices.VALIDADO:
        messages.warning(request, "Este documento já foi validado e não pode ser editado.")
        return redirect("participante:dashboard")
    
    if request.method == "POST":
        documentofiscal_form = DocumentoFiscalEditForm(
            instance=instance, data=request.POST, files=request.FILES
        )
        
        # Função para limpar valores monetários
        def limpar_valor_monetario(valor):
            if not valor:
                return 0
            if isinstance(valor, str):
                # Remove R$, espaços, pontos e converte vírgula para ponto
                valor_limpo = valor.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
                try:
                    return float(valor_limpo)
                except ValueError:
                    return 0
            return float(valor)
        
        # Processar valores diretamente do POST (antes da validação)
        valor_cielo_raw = request.POST.get('valorCielo', '0')
        valor_outros_raw = request.POST.get('valorOutros', '0')
        
        valor_cielo = limpar_valor_monetario(valor_cielo_raw)
        valor_outros = limpar_valor_monetario(valor_outros_raw)
        
        # Processar dados diretamente na instância, sem usar save(commit=False)
        # Calcular valor total (soma de Cielo + Outros)
        valor_total = valor_cielo + valor_outros
        
        # Atualizar valores diretamente na instância
        instance.valorCielo = valor_cielo
        instance.valorOutros = valor_outros
        instance.valorDocumento = valor_total
        instance.compradoCielo = valor_cielo > 0
        
        # Atualizar outros campos do formulário se válido
        if documentofiscal_form.is_valid():
            # Atualizar campos do formulário
            for field_name, value in documentofiscal_form.cleaned_data.items():
                if hasattr(instance, field_name):
                    setattr(instance, field_name, value)
        
        # Verificar se QUALQUER campo foi alterado (não apenas observação)
        campos_alterados = documentofiscal_form.changed_data
        valores_alterados = []

        # Verificar também alterações nos valores monetários
        valor_cielo_original = float(instance.valorCielo or 0)
        valor_outros_original = float(instance.valorOutros or 0)

        if valor_cielo != valor_cielo_original:
            valores_alterados.append(f"Valor Cielo: R$ {valor_cielo_original:.2f} → R$ {valor_cielo:.2f}")

        if valor_outros != valor_outros_original:
            valores_alterados.append(f"Valor Outros: R$ {valor_outros_original:.2f} → R$ {valor_outros:.2f}")

        # Se houve alterações em qualquer campo
        if campos_alterados or valores_alterados:
            instance.corrigido_pelo_participante = True
            instance.status = StatusChoices.PENDENTE
        
            # Log detalhado das alterações
            
            # Mensagem mais específica
            mensagens_alteracao = []
            
            if valores_alterados:
                mensagens_alteracao.extend(valores_alterados)
            
            if 'observacao' in campos_alterados:
                mensagens_alteracao.append("Observação atualizada")
            
            if campos_alterados and 'observacao' not in campos_alterados:
                outros_campos = [campo for campo in campos_alterados if campo != 'observacao']
                mensagens_alteracao.append(f"Campos atualizados: {', '.join(outros_campos)}")
            
            if mensagens_alteracao:
                messages.success(request, f"Documento Fiscal atualizado com sucesso! {', '.join(mensagens_alteracao)}")
            else:
                messages.success(request, "Documento Fiscal atualizado com sucesso!")
        else:
            messages.info(request, "Nenhuma alteração foi feita no documento.")
        
        instance.save()
        return redirect("participante:dashboard")
    else:
        documentofiscal_form = DocumentoFiscalEditForm(instance=instance)
        
        # Verificar se o campo observacao está presente no formulário
        if 'observacao' in documentofiscal_form.fields:
            pass  # Placeholder para futuras implementações
    
    return render(
        request,
        "participante/doc_fiscal_edit_participante.html",
        {"documentofiscal_form": documentofiscal_form},
    )


 # Mudança para permitir staff
@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
@transaction.atomic
def editdocfiscalbyop(request, id):
    import logging
    logger = logging.getLogger(__name__)
    
    # Log da requisição
    logger.info(f"Edição de documento fiscal iniciada - ID: {id}, User: {request.user.username}")
    
    try:
        instance = get_object_or_404(DocumentoFiscal.objects.select_for_update(), id=id)
        
        if request.method == "POST":
            # Para requisições POST, permitir edição mesmo se já estiver validado
            # (pode ser uma revalidação ou correção)
            pass
        else:
            # Verificar se o documento pode ser editado apenas para requisições GET
            if instance.status == StatusChoices.VALIDADO:
                messages.warning(request, f"Documento {instance.numeroDocumento} já está validado. Apenas documentos pendentes podem ser editados.")
                return redirect("participante:backoffice")
        
        if request.method == "POST":
            documentofiscal_form = DocumentoFiscalEditFormOp(
                instance=instance, data=request.POST, files=request.FILES
            )
            if documentofiscal_form.is_valid():
                # Salvar o documento
                doc = documentofiscal_form.save()
                
                # Validar o documento e gerar cupons
                doc.status = StatusChoices.VALIDADO
                doc.save()
                
                # Gerar cupons se não existirem
                cupons_gerados = 0
                if not Cupom.objects.filter(documentoFiscal=doc).exists():
                    cupons_a_gerar = doc.get_cupons()                  
                    if cupons_a_gerar > 0:
                        # Verificar se o usuário tem posto de trabalho antes de criar cupons
                        if not hasattr(request.user, 'profile') or not request.user.profile.posto_trabalho:
                            messages.error(request, "Você precisa selecionar um posto de trabalho antes de criar cupons.")
                            return redirect('participante:selecionar_posto')
                        
                        posto_trabalho = request.user.profile.posto_trabalho
                        
                        cupons = [
                            Cupom(
                                documentoFiscal=doc,
                                user=doc.user,
                                operador=request.user,
                                posto_trabalho=posto_trabalho,
                            )
                            for _ in range(cupons_a_gerar)
                        ]
                        Cupom.objects.bulk_create(cupons)
                        cupons_gerados = cupons_a_gerar
                        logger.info(f"Gerados {cupons_gerados} cupons para documento {doc.numeroDocumento}")
                
                messages.success(request, f"Documento Fiscal atualizado e validado com sucesso! {cupons_gerados} cupons gerados.")
                logger.info(f"Documento {instance.numeroDocumento} atualizado, validado e {cupons_gerados} cupons gerados")
                # Redirecionar para a página do participante após salvar com sucesso
                return redirect(f"{reverse('participante:search_by_cpf')}?q={instance.user.profile.CPF}")
            else:
                # Log detalhado dos erros
                logger.error(f"Erro de validação no formulário: {documentofiscal_form.errors}")
                logger.error(f"Dados recebidos: {request.POST}")
                logger.error(f"Cleaned data: {documentofiscal_form.cleaned_data if hasattr(documentofiscal_form, 'cleaned_data') else 'N/A'}")
                
                # Mensagem mais específica
                error_fields = list(documentofiscal_form.errors.keys())
                if error_fields:
                    error_msg = f"Erro nos campos: {', '.join(error_fields)}. Verifique os dados inseridos."
                else:
                    error_msg = "Erro na atualização do documento Fiscal! Verifique se não há algum dado incoerente no formulário."
                
                messages.error(request, error_msg)
        else:
            documentofiscal_form = DocumentoFiscalEditFormOp(instance=instance)
        
        context = {
            "documentofiscal_form": documentofiscal_form,
            "documento": instance,
            "section": "edit_document"
        }
        
        return render(request, "participante/doc_fiscal_edit_participante.html", context)
        
    except Exception as e:
        logger.error(f"Erro ao editar documento fiscal ID {id}: {str(e)}", exc_info=True)
        messages.error(request, f"Erro ao carregar documento fiscal: {str(e)}")
        return redirect("participante:backoffice")


@login_required
@user_passes_test(lambda u: u.is_staff)  # Mudança para permitir staff
@transaction.atomic
def validadocfiscal(request, id):
    "O backoffice usa esta view para validar documentos fiscais "
    import logging
    logger = logging.getLogger(__name__)
    
    # Log da requisição
    logger.info(f"Validação de documento iniciada - ID: {id}, User: {request.user.username}")
    
    instance = get_object_or_404(DocumentoFiscal, id=id)

    if instance.status != StatusChoices.PENDENTE:
        error_msg = f"O documento {instance.numeroDocumento} não está pendente de validação."
        messages.error(request, error_msg)
        return redirect("participante:backoffice")

    if request.method == "POST":
        try:
            with transaction.atomic():
                doc = instance
                doc.status = StatusChoices.VALIDADO
                doc.save()

                # Lógica para gerar cupons
                cupons_gerados = 0
                if not Cupom.objects.filter(documentoFiscal=doc).exists():
                    cupons_a_gerar = doc.get_cupons()
                    if cupons_a_gerar > 0:
                        # Verificar se o usuário tem posto de trabalho antes de criar cupons
                        if not hasattr(request.user, 'profile') or not request.user.profile.posto_trabalho:
                            messages.error(request, "Você precisa selecionar um posto de trabalho antes de criar cupons.")
                            return redirect('participante:selecionar_posto')
                        
                        posto_trabalho = request.user.profile.posto_trabalho
                        
                        cupons = [
                            Cupom(
                                documentoFiscal=doc,
                                user=doc.user,
                                operador=request.user,
                                posto_trabalho=posto_trabalho,
                            )
                            for _ in range(cupons_a_gerar)
                        ]
                        Cupom.objects.bulk_create(cupons)
                        cupons_gerados = cupons_a_gerar                       
                else:
                    messages.warning(request, f"Cupons para o documento {doc.numeroDocumento} já existem.")

                success_msg = f"Documento {doc.numeroDocumento} validado com sucesso!"
                if cupons_gerados > 0:
                    success_msg += f" {cupons_gerados} cupons gerados."
                
                messages.success(request, success_msg)
                logger.info(f"Validação bem-sucedida: {success_msg}")
                
        except Exception as e:
            logger.error(f"Erro na validação: {str(e)}", exc_info=True)
            messages.error(request, f"Erro ao validar documento: {str(e)}")
    
    return redirect("participante:backoffice")


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def documento_validado_op(request, doc_id):
    """View para marcar documento como validado pelo operador"""
    try:
        documento = DocumentoFiscal.objects.get(id=doc_id)
        
        # Verificar se o usuário tem permissão
        if not has_operational_access(request.user):
            messages.error(request, 'Você não tem permissão para executar esta ação.')
            return redirect('lojista:homepage')
        
        # Marcar como validado
        documento.status = StatusChoices.VALIDADO
        documento.dataValidacao = timezone.now()
        documento.validadoPor = request.user
        documento.save()
        
        messages.success(request, f'Documento {documento.numeroDocumento} marcado como validado com sucesso!')
        
    except DocumentoFiscal.DoesNotExist:
        messages.error(request, 'Documento não encontrado.')
    except Exception as e:
        messages.error(request, f'Erro ao validar documento: {str(e)}')
    
    return redirect('lojista:search_by_doc')


@require_http_methods(["POST"])
@ensure_csrf_cookie
def confirmar_impressao(request, doc_id):
    """
    Confirma a impressão de um documento, marcando todos os cupons como impressos.
    Apenas staff pode confirmar impressões.
    """

    
    # Se o usuário não está autenticado, retornar erro
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Usuário não autenticado'
        }, status=401)
    
    # Verificar permissões
    try:
        has_permission = (request.user.is_staff or request.user.is_superuser or is_backoffice(request.user))
    except Exception as e:
        # Fallback: apenas verificar se é staff ou superuser
        has_permission = (request.user.is_staff or request.user.is_superuser)
    
    if not has_permission:
        return JsonResponse({
            'success': False,
            'message': 'Você não tem permissão para executar esta ação'
        }, status=403)
    
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Método não permitido'
        }, status=405)
    
    try:
        # Verificar se o documento existe antes de usar get_object_or_404
        try:
            documento = DocumentoFiscal.objects.get(id=doc_id)
        except DocumentoFiscal.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'Documento com ID {doc_id} não encontrado'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao buscar documento: {str(e)}'
            }, status=500)
        
        # Buscar todos os cupons do documento
        todos_cupons = Cupom.objects.filter(documentoFiscal=documento)
        cupons_nao_impressos = todos_cupons.filter(impresso=False)
        cupons_ja_impressos = todos_cupons.filter(impresso=True)
        
        # Se não há cupons no documento
        if not todos_cupons.exists():
            return JsonResponse({
                'success': False,
                'message': 'Nenhum cupom encontrado para este documento'
            })
        
        # Se todos já foram impressos (marcados na geração do PDF)
        if cupons_ja_impressos.exists() and not cupons_nao_impressos.exists():
            return JsonResponse({
                'success': True,
                'message': f'✅ {cupons_ja_impressos.count()} cupons já foram marcados como impressos',
                'cupons_confirmados': cupons_ja_impressos.count(),
                'already_printed': True
            })
        
        # Contar cupons antes da atualização
        cupons_count = cupons_nao_impressos.count()
        
        # Marcar cupons não impressos como impressos (fluxo antigo)
        if cupons_nao_impressos.exists():
            with transaction.atomic():
                cupons_nao_impressos.update(
                    impresso=True,
                    dataImpressao=timezone.now()
                )
            
            # Registrar na auditoria
            try:
                Auditoria.objects.create(
                    usuario=request.user,
                    tipo_acao='impressao_cupons',
                    descricao=f'Confirmação manual de impressão do documento {documento.numeroDocumento}',
                    documento_fiscal=documento
                )
            except Exception as audit_error:
                # Não falhar se a auditoria der erro
                pass
            
            response_data = {
                'success': True,
                'message': f'Impressão confirmada para {cupons_count} cupon(s)',
                'cupons_confirmados': cupons_count,
                'documento_info': {
                    'id': documento.id,
                    'numero': documento.numeroDocumento,
                    'lojista': documento.lojista.fantasiaLojista,
                    'participante': documento.user.username
                }
            }
            return JsonResponse(response_data)
        
    except DocumentoFiscal.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Documento não encontrado'
        }, status=404)
    except Exception as e:
        # Garantir que sempre retornamos JSON, mesmo em caso de erro
        try:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao confirmar impressão: {str(e)}'
                }, status=500)
        except Exception as json_error:
            # Fallback: retornar resposta simples
            from django.http import HttpResponse
            return HttpResponse(
                f'{{"success": false, "message": "Erro interno do servidor"}}',
                content_type='application/json',
                status=500
            )


@require_http_methods(["POST"])
@ensure_csrf_cookie
def confirmar_impressao_simple(request, doc_id):
    """
    Versão simplificada da confirmação de impressão para teste.
    """
   
  
    
    # Verificar autenticação
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Usuário não autenticado'
        }, status=401)
    
    # Verificar permissões básicas
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({
            'success': False,
            'message': 'Sem permissão para esta ação'
        }, status=403)
    
    try:
        # Buscar documento
        documento = DocumentoFiscal.objects.get(id=doc_id)
        
        # Buscar cupons
        cupons = Cupom.objects.filter(documentoFiscal=documento, impresso=False)
        
        if not cupons.exists():
            return JsonResponse({
                'success': False,
                'message': 'Não há cupons para confirmar impressão'
            })
        
        # Marcar como impressos
        cupons.update(impresso=True, dataImpressao=timezone.now())
        
        return JsonResponse({
            'success': True,
            'message': f'Impressão confirmada para {cupons.count()} cupon(s)',
            'documento': documento.numeroDocumento
        })
    
    except DocumentoFiscal.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Documento não encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@ensure_csrf_cookie
def registrar_cancelamento_impressao(request, doc_id):
    """
    Registra um cancelamento de impressão.
    Permite controlar quantas vezes cada usuário pode cancelar a impressão de um documento.
    """
    # Debug logging
    
    
    # Verificar autenticação
    if not request.user.is_authenticated:
        
        return JsonResponse({
            'success': False,
            'message': 'Usuário não autenticado'
        }, status=401)
    
    # Verificar permissões
  
    if not (request.user.is_staff or request.user.is_superuser):
        
        return JsonResponse({
            'success': False,
            'message': 'Sem permissão para esta ação'
        }, status=403)
    
    try:
        
        # Buscar documento
        documento = DocumentoFiscal.objects.get(id=doc_id)
        
        
        # Verificar se pode cancelar
        from participante.models import CancelamentoImpressao
        pode_cancelar, mensagem = CancelamentoImpressao.pode_cancelar(request.user, documento)
        
        if not pode_cancelar:
            return JsonResponse({
                'success': False,
                'message': mensagem
            }, status=403)
        
        # Obter motivo do request
        try:
            data = json.loads(request.body)
            motivo = data.get('motivo', '').strip()
        except (json.JSONDecodeError, KeyError):
            return JsonResponse({
                'success': False,
                'message': 'Motivo do cancelamento é obrigatório'
            }, status=400)
        
        if not motivo:
            return JsonResponse({
                'success': False,
                'message': 'Motivo do cancelamento é obrigatório'
            }, status=400)
        
        # Registrar cancelamento
        cancelamento = CancelamentoImpressao.registrar_cancelamento(
            usuario=request.user,
            documento=documento,
            motivo=motivo
        )
        
        # IMPORTANTE: Cancelar chama Reverter automaticamente (versão segura)
        # Executar reversão usando função interna segura
        sucesso_reversao, mensagem_reversao = _executar_reversao_interna(request.user, documento)
        
        if not sucesso_reversao:
            return JsonResponse({
                'success': False,
                'message': f'Cancelamento registrado, mas erro na reversão: {mensagem_reversao}'
            }, status=500)
        
        # Registrar na auditoria
        try:
            Auditoria.objects.create(
                usuario=request.user,
                tipo_acao='cancelamento_impressao',
                descricao=f'Cancelamento e reversão do documento {documento.numeroDocumento}',
                documento_fiscal=documento,
                justificativa=motivo
            )
        except Exception as audit_error:
            # Não falhar se a auditoria der erro
            pass
        
        return JsonResponse({
            'success': True,
            'message': 'Cancelamento e reversão realizados com sucesso! Documento voltou para pendente.',
            'cancelamento_id': cancelamento.id,
            'documento': documento.numeroDocumento
        })
        
    except DocumentoFiscal.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Documento não encontrado'
        }, status=404)
    except Exception as e:
        
        import traceback
        
        return JsonResponse({
            'success': False,
            'message': f'Erro ao registrar cancelamento: {str(e)}'
        }, status=500)


