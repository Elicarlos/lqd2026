import django_filters

from .models import Lojista


class LojistaFilter(django_filters.FilterSet):
    class Meta:
        model = Lojista
        fields = [
            "CNPJLojista",
            "IELojista",
            "razaoLojista",
            "fantasiaLojista",
            "ramoAtividade",
        ]
