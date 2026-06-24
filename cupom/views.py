from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from bcp.views import print_qrcode
from participante.models import DocumentoFiscal

from .forms import AddCupomForm
from .models import Cupom


@login_required
@user_passes_test(lambda u: u.is_superuser)
def detail(request):
    return render(request, "cupom/detail.html", {"section": "cupom-detail"})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def addcupom(request, numerodocumento):
    if request.method == "POST":
        cupom_form = AddCupomForm(request.POST)

        if cupom_form.is_valid():
            doc = get_object_or_404(DocumentoFiscal, numeroDocumento=numerodocumento)
            new_cupom = cupom_form.save(commit=False)
            new_cupom.documentoFiscal = doc
            new_cupom.user = doc.user
            new_cupom.operador = request.user
            new_cupom.save()
            messages.success(request, "Cupom gerado com sucesso")
        else:
            messages.success(request, "Erro ao gerar o cupom")
    return redirect("/")


@login_required
@user_passes_test(lambda u: u.is_superuser)
def gerarcupons(request, numerodocumento):
    if request.method == "POST":
        doc = get_object_or_404(DocumentoFiscal, numeroDocumento=numerodocumento)
        qtde = int(doc.get_cupons())
        with transaction.atomic():
            cupons = [
                Cupom(documentoFiscal=doc, user=doc.user, operador=request.user)
                for _ in range(qtde)
            ]
            Cupom.objects.bulk_create(cupons)
        messages.success(request, "Cupons gerados com sucesso!")
    return HttpResponse("/")


@login_required
@user_passes_test(lambda u: u.is_superuser)
def cupomlist(request, username):
    user = get_object_or_404(User, username=username)
    cupons = Cupom.objects.filter(user=user)
    return render(
        request, "cupom/list.html", {"section": "cuponslist", "cupons": cupons}
    )


@login_required
@user_passes_test(lambda u: u.is_superuser)
def printCupom(request, numerodocumento):
    doc_instance = get_object_or_404(DocumentoFiscal, numeroDocumento=numerodocumento)
    cupons = Cupom.objects.filter(documentoFiscal=doc_instance)
    for cupom in cupons:
        print_qrcode(request, cupom.get_token(), numerodocumento)
    return HttpResponse("/")
