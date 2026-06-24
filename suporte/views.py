"""
Views específicas para o suporte.
Funcionalidades de busca e reversão de documentos para auxiliar o suporte.
Acesso restrito apenas para usuários do grupo 'Suporte' e superusers.
"""

import json
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q

from participante.models import DocumentoFiscal, Profile, StatusChoices
from cupom.models import Cupom
from participante.permissions import is_suporte


def suporte_required(view_func):
    """
    Decorator para verificar se o usuário é do grupo Suporte ou superuser.
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'message': 'Usuário não autenticado'
            }, status=401)
        
        if not (is_suporte(request.user) or request.user.is_superuser):
            return JsonResponse({
                'success': False,
                'message': 'Acesso restrito ao suporte'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@suporte_required
def suporte_dashboard(request):
    """
    Dashboard principal do suporte com funcionalidades de busca.
    """
    return render(request, 'suporte/suporte_dashboard.html', {
        'title': 'Dashboard do Suporte',
        'user': request.user
    })


@login_required
@suporte_required
@require_http_methods(["GET"])
def buscar_participante_cpf(request):
    """
    Busca participante por CPF para o suporte.
    """
    cpf = request.GET.get('cpf', '').strip()
    
    if not cpf:
        return JsonResponse({
            'success': False,
            'message': 'CPF é obrigatório'
        }, status=400)
    
    try:
        # Limpar CPF (remover pontos e hífens)
        cpf_limpo = cpf.replace('.', '').replace('-', '').replace(' ', '')
        
        # Buscar perfil pelo CPF (tentar com e sem formatação)
        profile = Profile.objects.filter(CPF=cpf).first()
        if not profile:
            profile = Profile.objects.filter(CPF=cpf_limpo).first()
        
        if not profile:
            return JsonResponse({
                'success': False,
                'message': f'Participante com CPF {cpf} não encontrado'
            }, status=404)
        
        # Buscar documentos do participante
        documentos = DocumentoFiscal.objects.filter(
            user=profile.user
        ).order_by('-dataCadastro')
        
        # Preparar dados do participante
        participante_data = {
            'id': profile.user.id,
            'nome': profile.nome,
            'cpf': profile.CPF,
            'email': profile.user.email,
            'telefone': profile.foneCelular1 or profile.foneFixo or 'N/A',
            'data_cadastro': profile.user.date_joined.strftime('%d/%m/%Y %H:%M'),
            'documentos_count': documentos.count()
        }
        
        # Preparar lista de documentos (limitada para performance)
        documentos_list = []
        for doc in documentos[:10]:  # Limitar a 10 documentos mais recentes
            documentos_list.append({
                'id': doc.id,
                'numero': doc.numeroDocumento,
                'tipo': doc.lojista.fantasiaLojista if doc.lojista else 'N/A',
                'valor': float(doc.valorDocumento),
                'status': doc.status,
                'data_documento': doc.dataDocumento.strftime('%d/%m/%Y'),
                'data_cadastro': doc.dataCadastro.strftime('%d/%m/%Y %H:%M'),
                'lojista': doc.lojista.fantasiaLojista if doc.lojista else 'N/A',
                'cupons_count': doc.get_cupons(),
                'has_cupons': doc.get_cupons() > 0
            })
        
        return JsonResponse({
            'success': True,
            'participante': participante_data,
            'documentos': documentos_list,
            'total_documentos': documentos.count()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao buscar participante: {str(e)}'
        }, status=500)


@login_required
@suporte_required
@require_http_methods(["GET"])
def buscar_documento_numero(request):
    """
    Busca documento específico por número para o suporte.
    """
    numero = request.GET.get('numero', '').strip()
    
    if not numero:
        return JsonResponse({
            'success': False,
            'message': 'Número do documento é obrigatório'
        }, status=400)
    
    try:
        # Buscar documento pelo número
        documento = DocumentoFiscal.objects.filter(
            numeroDocumento=numero
        ).first()
        
        if not documento:
            return JsonResponse({
                'success': False,
                'message': f'Documento {numero} não encontrado'
            }, status=404)
        
        # Buscar cupons do documento
        cupons = Cupom.objects.filter(documentoFiscal=documento)
        
        # Preparar dados do documento
        documento_data = {
            'id': documento.id,
            'numero': documento.numeroDocumento,
            'tipo': documento.lojista.fantasiaLojista if documento.lojista else 'N/A',
            'valor': float(documento.valorDocumento),
            'status': documento.status,
            'data_documento': documento.dataDocumento.strftime('%d/%m/%Y'),
            'data_cadastro': documento.dataCadastro.strftime('%d/%m/%Y %H:%M'),
            'lojista': {
                'fantasia': documento.lojista.fantasiaLojista if documento.lojista else 'N/A',
                'cnpj': documento.lojista.CNPJLojista if documento.lojista else 'N/A'
            },
            'participante': {
                'nome': documento.user.profile.nome,
                'cpf': documento.user.profile.CPF,
                'email': documento.user.email
            },
            'cupons': {
                'total': cupons.count(),
                'impressos': cupons.filter(impresso=True).count(),
                'nao_impressos': cupons.filter(impresso=False).count()
            }
        }
        
        return JsonResponse({
            'success': True,
            'documento': documento_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao buscar documento: {str(e)}'
        }, status=500)


@login_required
@suporte_required
@ensure_csrf_cookie
@require_http_methods(["POST"])
def reverter_documento_suporte(request, doc_id):
    """
    Reverte documento específico - apaga cupons e coloca como pendente.
    Acesso exclusivo para suporte.
    """
    try:
        # Processar dados da requisição
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            motivo = data.get('motivo', 'Reversão pelo suporte')
        else:
            motivo = request.POST.get('motivo', 'Reversão pelo suporte')
        
        # Buscar documento
        documento = get_object_or_404(DocumentoFiscal, id=doc_id)
        
        # Verificar se tem cupons
        cupons = Cupom.objects.filter(documentoFiscal=documento)
        
        if not cupons.exists():
            return JsonResponse({
                'success': False,
                'message': 'Documento não possui cupons para reverter'
            }, status=400)
        
        # Contar cupons antes de apagar
        cupons_deletados = cupons.count()
        
        # APAGAR TODOS OS CUPONS
        cupons.delete()
        
        # COLOCAR DOCUMENTO COMO PENDENTE
        documento.status = StatusChoices.PENDENTE
        documento.save()
        
        # Registrar ação na auditoria (se existir)
        try:
            from participante.models import Auditoria
            Auditoria.objects.create(
                usuario=request.user,
                acao='REVERSAO_SUPORTE',
                detalhes=f'Documento {documento.numeroDocumento} revertido pelo suporte. Motivo: {motivo}. Cupons removidos: {cupons_deletados}',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        except Exception as audit_error:
            print(f"Erro ao registrar auditoria: {audit_error}")
        
        return JsonResponse({
            'success': True,
            'message': f'Documento revertido com sucesso! {cupons_deletados} cupon(s) removido(s). Documento agora está pendente para revalidação.',
            'documento': {
                'id': documento.id,
                'numero': documento.numeroDocumento,
                'status': documento.status,
                'cupons_removidos': cupons_deletados
            }
        })
        
    except DocumentoFiscal.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': f'Documento {doc_id} não encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }, status=500)


@login_required
@suporte_required
@require_http_methods(["GET"])
def listar_documentos_recentes(request):
    """
    Lista documentos recentes para o suporte.
    """
    try:
        # Parâmetros de paginação
        page = request.GET.get('page', 1)
        per_page = request.GET.get('per_page', 20)
        
        # Buscar documentos recentes
        documentos = DocumentoFiscal.objects.select_related(
            'user__profile', 'lojista'
        ).prefetch_related(
            'cupom_set'
        ).order_by('-dataCadastro')
        
        # Paginação
        paginator = Paginator(documentos, per_page)
        page_obj = paginator.get_page(page)
        
        # Preparar dados
        documentos_list = []
        for doc in page_obj:
            cupons = doc.cupom_set.all()
            documentos_list.append({
                'id': doc.id,
                'numero': doc.numeroDocumento,
                'tipo': doc.lojista.fantasiaLojista if doc.lojista else 'N/A',
                'valor': float(doc.valorDocumento),
                'status': doc.status,
                'data_documento': doc.dataDocumento.strftime('%d/%m/%Y'),
                'data_cadastro': doc.dataCadastro.strftime('%d/%m/%Y %H:%M'),
                'lojista': doc.lojista.fantasiaLojista if doc.lojista else 'N/A',
                'participante': {
                    'nome': doc.user.profile.nome,
                    'cpf': doc.user.profile.CPF
                },
                'cupons_count': cupons.count(),
                'cupons_impressos': cupons.filter(impresso=True).count()
            })
        
        return JsonResponse({
            'success': True,
            'documentos': documentos_list,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao listar documentos: {str(e)}'
        }, status=500)
