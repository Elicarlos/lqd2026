from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportActionModelAdmin, ImportExportModelAdmin

from .models import Cupom

# Register your models here.


class CupomResource(resources.ModelResource):

    class Meta:
        model = Cupom


class CupomAdmin(
    ImportExportActionModelAdmin, ImportExportModelAdmin, admin.ModelAdmin
):
    list_display = (
        "id",
        "user",
        "documentoFiscal",
        "operador",
        "dataCriacao",
        "impresso",
        "dataImpressao",
        "reimpresso_em",
        "posto_trabalho",
    )
    search_fields = (
        "documentoFiscal__numeroDocumento",
        "id",
        "user__username",
        "operador__username",
        "documentoFiscal__lojista__CNPJLojista",
        "posto_trabalho__nome",
    )
    readonly_fields = ("operador", "posto_trabalho")
    list_filter = ("impresso", "posto_trabalho")
    resource_class = CupomResource

    def get_search_results(self, request, queryset, search_term):
        """
        Permite buscas personalizadas, incluindo CNPJ formatado (xx.xxx.xxx/xxxx-xx).
        """
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )

        # Verifica se o termo buscado segue o formato de um CNPJ
        if (
            search_term.count("/") == 1
            and search_term.count("-") == 1
            and "." in search_term
        ):
            queryset |= self.model.objects.filter(
                documentoFiscal__lojista__CNPJLojista__icontains=search_term
            )
        return queryset, use_distinct


admin.site.register(Cupom, CupomAdmin)
