from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from cupom.models import Cupom
from .models import SorteioResultado


def _is_authorized(user):
    try:
        from participante.permissions import is_suporte
        return user.is_superuser or is_suporte(user)
    except Exception:
        # Fallback seguro: apenas superuser
        return user.is_superuser


@login_required
@user_passes_test(_is_authorized)
def sorteio_home(request):
    """
    Tela segura para realização/visualização do sorteio.
    Acesso restrito a staff/superuser.
    
    """
    # Se envio via POST/AJAX para buscar cupom
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Salvar resultado
        if request.POST.get('action') == 'salvar':
            try:
                cupom_id = int(request.POST.get('cupom_id'))
            except Exception:
                return JsonResponse({"success": False, "message": "Cupom inválido."}, status=400)
            try:
                cupom = Cupom.objects.select_related('user', 'user__profile').get(id=cupom_id)
            except Cupom.DoesNotExist:
                return JsonResponse({"success": False, "message": "Cupom não encontrado ou invalidado."}, status=404)
            cpf = getattr(cupom.user.profile, 'CPF', '')
            # Evitar duplicidade por cupom
            if SorteioResultado.objects.filter(cupom=cupom).exists():
                return JsonResponse({"success": False, "message": "Este cupom já foi salvo como sorteado."}, status=400)
            resultado = SorteioResultado.objects.create(
                cupom=cupom,
                participante=cupom.user,
                cpf=cpf,
                criado_por=request.user,
                valido=True,
                motivo_invalidacao=''
            )
            return JsonResponse({"success": True, "message": "Resultado salvo com sucesso.", "id": resultado.id})

        numero = (request.POST.get('numero') or '').strip()
        if not numero.isdigit():
            return JsonResponse({"success": False, "message": "Informe um número válido."}, status=400)
        try:
            cupom = Cupom.objects.select_related('user', 'user__profile', 'documentoFiscal', 'documentoFiscal__lojista').get(id=int(numero))
        except Cupom.DoesNotExist:
            return JsonResponse({"success": False, "message": "Cupom não encontrado ou invalidado."}, status=404)

        # Verificação de elegibilidade (excluir organização, staff e superuser)
        elegivel = True
        motivo = ''
        is_cdl = False
        try:
            from organizacao.models import PessoaOrganizacao
            def only_digits(val: str) -> str:
                return ''.join(ch for ch in (val or '') if ch.isdigit())
            cpf_digits = only_digits(getattr(cupom.user.profile, 'CPF', ''))
            if cpf_digits:
                # Comparar por dígitos para não depender da máscara salvo no banco
                registros = list(PessoaOrganizacao.objects.values_list('cpf', 'origem'))
                is_org = any(only_digits(cpf) == cpf_digits for cpf, _o in registros)
                is_cdl_origin = any((only_digits(cpf) == cpf_digits and o == 'CDL') for cpf, o in registros)
                if is_org:
                    elegivel = False
                    motivo = 'CPF pertence à organização'
                # CDL deve ser SIM se for organização (qualquer origem) ou origem CDL
                is_cdl = is_org or is_cdl_origin
        except Exception:
            # se o app não existir, apenas ignora esta checagem
            pass

        if cupom.user.is_superuser:
            elegivel = False
            motivo = 'Usuário superadmin'
        elif cupom.user.is_staff and elegivel:
            elegivel = False
            motivo = 'Usuário staff - coloborador'
        data = {
            "success": True,
            "cupom": {
                "id": cupom.id,
                "participante": getattr(cupom.user.profile, 'nome', cupom.user.username),
                "cpf": getattr(cupom.user.profile, 'CPF', ''),
                "telefone": getattr(cupom.user.profile, 'foneCelular1', '') or getattr(cupom.user.profile, 'whatsapp', ''),
                "documento": cupom.documentoFiscal.numeroDocumento,
                "lojista": cupom.documentoFiscal.lojista.fantasiaLojista,
                "data_doc": cupom.documentoFiscal.dataDocumento.strftime('%d/%m/%Y'),
                "valor": float(cupom.documentoFiscal.valorDocumento),
                "elegivel": elegivel,
                "motivo": motivo,
                "cielo": 'SIM' if getattr(cupom.documentoFiscal, 'compradoCielo', False) else 'NÃO',
                "vendedor": getattr(cupom.documentoFiscal, 'vendedor', '') or '-',
                "operador": 'SIM' if (cupom.user.is_staff or cupom.user.is_superuser) else 'NÃO',
                "cdl": 'SIM' if is_cdl else 'NÃO',
            }
        }
        return JsonResponse(data)

    return render(request, 'sorteio/sorteio.html', {"section": "sorteio"})


@login_required
@user_passes_test(_is_authorized)
def sorteio_resultados(request):
    qs = SorteioResultado.objects.select_related('cupom', 'participante', 'participante__profile', 'cupom__documentoFiscal', 'cupom__documentoFiscal__lojista').all()

    # Filtros básicos
    cpf = (request.GET.get('cpf') or '').strip()
    cupom_id = (request.GET.get('cupom') or '').strip()
    data_ini = (request.GET.get('data_inicio') or '').strip()
    data_fim = (request.GET.get('data_fim') or '').strip()

    if cpf:
        qs = qs.filter(cpf__icontains=''.join([c for c in cpf if c.isdigit()]))
    if cupom_id and cupom_id.isdigit():
        qs = qs.filter(cupom_id=int(cupom_id))
    from datetime import datetime
    def parse(d):
        try:
            return datetime.strptime(d, '%Y-%m-%d')
        except Exception:
            return None
    di = parse(data_ini)
    df = parse(data_fim)
    if di:
        qs = qs.filter(criado_em__date__gte=di.date())
    if df:
        qs = qs.filter(criado_em__date__lte=df.date())

    # Export CSV
    if request.GET.get('export') == 'csv':
        import csv
        from django.http import HttpResponse
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename=resultados_sorteio.csv'
        w = csv.writer(resp)
        w.writerow(['id', 'cupom', 'cpf', 'participante', 'data'])
        for r in qs.order_by('criado_em', 'id'):
            nome = getattr(getattr(r.participante, 'profile', None), 'nome', r.participante.username)
            w.writerow([r.id, r.cupom_id, r.cpf, nome, r.criado_em.strftime('%d/%m/%Y %H:%M')])
        return resp

    # Paginação
    from django.core.paginator import Paginator
    paginator = Paginator(qs.order_by('criado_em', 'id'), 30)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    ctx = {
        'page_obj': page_obj,
        'cpf': cpf,
        'cupom': cupom_id,
        'data_inicio': data_ini,
        'data_fim': data_fim,
    }
    return render(request, 'sorteio/resultados.html', ctx)
