import django_filters

from .models import DocumentoFiscal, Profile


class UserFilter(django_filters.FilterSet):
    nome = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Nome',
        help_text='Buscar por nome do participante'
    )
    CPF = django_filters.CharFilter(
        lookup_expr='icontains',
        label='CPF',
        help_text='Buscar por CPF'
    )
    RG = django_filters.CharFilter(
        lookup_expr='icontains',
        label='RG',
        help_text='Buscar por RG'
    )
    endereco = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Endereço',
        help_text='Buscar por endereço'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Garantir que apenas participantes normais sejam mostrados
        if self.queryset is not None:
            self.queryset = self.queryset.filter(is_colaborador=False)

    class Meta:
        model = Profile
        fields = ["nome", "CPF", "RG", "endereco"]
        exclude = ["Email", "photo"]


class DocFilter(django_filters.FilterSet):
    class Meta:
        model = DocumentoFiscal
        fields = [
            "numeroDocumento",
            "lojista",
            "dataDocumento",
            "valorDocumento",
            "vendedor",
            "status",
        ]
