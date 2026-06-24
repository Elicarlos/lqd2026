from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from .models import PessoaOrganizacao
from .forms import PessoaOrganizacaoForm


def _is_staff(user):
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(_is_staff)
def pessoas_list(request):
    pessoas = PessoaOrganizacao.objects.all().order_by('nome')
    q = (request.GET.get('q') or '').strip()
    origem = (request.GET.get('origem') or '').strip()

    if q:
        digits = ''.join(ch for ch in q if ch.isdigit())
        filtros = Q(nome__icontains=q) | Q(cpf__icontains=q)
        if digits:
            filtros |= Q(cpf__icontains=digits)
        pessoas = pessoas.filter(filtros)

    if origem:
        pessoas = pessoas.filter(origem=origem)

    context = {
        "pessoas": pessoas,
        "q": q,
        "origem": origem,
    }
    return render(request, 'organizacao/pessoas_list.html', context)


@login_required
@user_passes_test(_is_staff)
def pessoa_create(request):
    if request.method == 'POST':
        form = PessoaOrganizacaoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pessoa cadastrada com sucesso!')
            return redirect('organizacao:pessoas_list')
    else:
        form = PessoaOrganizacaoForm()
    return render(request, 'organizacao/pessoa_form.html', {"form": form, "is_new": True})


@login_required
@user_passes_test(_is_staff)
def pessoa_update(request, pk):
    pessoa = get_object_or_404(PessoaOrganizacao, pk=pk)
    if request.method == 'POST':
        form = PessoaOrganizacaoForm(request.POST, instance=pessoa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cadastro atualizado com sucesso!')
            return redirect('organizacao:pessoas_list')
    else:
        form = PessoaOrganizacaoForm(instance=pessoa)
    return render(request, 'organizacao/pessoa_form.html', {"form": form, "is_new": False})


@login_required
@user_passes_test(_is_staff)
def pessoa_delete(request, pk):
    pessoa = get_object_or_404(PessoaOrganizacao, pk=pk)
    if request.method == 'POST':
        pessoa.delete()
        messages.success(request, 'Cadastro removido com sucesso!')
        return redirect('organizacao:pessoas_list')
    return render(request, 'organizacao/pessoa_confirm_delete.html', {"pessoa": pessoa})


