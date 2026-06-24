from django.core.management.base import BaseCommand
from lojista.models import Localizacao


class Command(BaseCommand):
    help = 'Cria localizações de exemplo para o sistema'

    def handle(self, *args, **options):
        localizacoes_exemplo = [
            {
                'nome': 'SHOPPING RIO POTY',
                'descricao': 'Shopping localizado na zona sul de Teresina, próximo ao Rio Poty'
            },
            {
                'nome': 'SHOPPING TERESINA',
                'descricao': 'Shopping localizado no centro de Teresina'
            },
            {
                'nome': 'CENTRO',
                'descricao': 'Região central da cidade de Teresina'
            },
            {
                'nome': 'ZONA SUL',
                'descricao': 'Região sul de Teresina'
            },
            {
                'nome': 'ZONA NORTE',
                'descricao': 'Região norte de Teresina'
            },
            {
                'nome': 'ZONA LESTE',
                'descricao': 'Região leste de Teresina'
            },
            {
                'nome': 'ZONA OESTE',
                'descricao': 'Região oeste de Teresina'
            },
            {
                'nome': 'PRAÇA DE ALIMENTAÇÃO',
                'descricao': 'Área de alimentação dos shoppings'
            },
            {
                'nome': 'ESTACIONAMENTO',
                'descricao': 'Área de estacionamento dos estabelecimentos'
            },
            {
                'nome': 'ÁREA EXTERNA',
                'descricao': 'Área externa dos estabelecimentos'
            }
        ]

        localizacoes_criadas = 0
        for loc_data in localizacoes_exemplo:
            localizacao, created = Localizacao.objects.get_or_create(
                nome=loc_data['nome'],
                defaults={'descricao': loc_data['descricao']}
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Localização criada: {localizacao.nome}')
                )
                localizacoes_criadas += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Localização já existe: {localizacao.nome}')
                )

        total_localizacoes = Localizacao.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'\n🎯 Resumo: {localizacoes_criadas} novas localizações criadas')
        )
        self.stdout.write(
            self.style.SUCCESS(f'📊 Total de localizações no sistema: {total_localizacoes}')
        ) 