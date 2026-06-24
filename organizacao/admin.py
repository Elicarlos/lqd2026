from django.contrib import admin
from .models import PessoaOrganizacao


@admin.register(PessoaOrganizacao)
class PessoaOrganizacaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf", "origem", "created_at")
    list_filter = ("origem",)
    search_fields = ("nome", "cpf")
    ordering = ("nome",)


