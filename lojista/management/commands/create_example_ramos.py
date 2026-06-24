from django.core.management.base import BaseCommand
from lojista.models import RamoAtividade


class Command(BaseCommand):
    help = 'Cria ramos de atividade de exemplo para o sistema'

    def handle(self, *args, **options):
        ramos_exemplo = [
            'ALIMENTAÇÃO',
            'VESTUÁRIO',
            'CALÇADOS',
            'ACESSÓRIOS',
            'COSMÉTICOS',
            'PERFUMARIA',
            'ELETRÔNICOS',
            'INFORMÁTICA',
            'BRINQUEDOS',
            'LIVROS',
            'PAPELARIA',
            'CASA E DECORAÇÃO',
            'ESPORTES',
            'FARMÁCIA',
            'ÓTICA',
            'JÓIAS',
            'RELÓGIOS',
            'AUTOMOTIVO',
            'CONSTRUÇÃO',
            'SERVIÇOS'
        ]

        ramos_criados = 0
        for atividade in ramos_exemplo:
            ramo, created = RamoAtividade.objects.get_or_create(
                atividade=atividade,
                defaults={'ativo': True}
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Ramo criado: {ramo.atividade}')
                )
                ramos_criados += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Ramo já existe: {ramo.atividade}')
                )

        total_ramos = RamoAtividade.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'\n🎯 Resumo: {ramos_criados} novos ramos criados')
        )
        self.stdout.write(
            self.style.SUCCESS(f'📊 Total de ramos no sistema: {total_ramos}')
        ) 