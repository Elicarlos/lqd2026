from django.core.management.base import BaseCommand
from participante.models import PostoTrabalho


class Command(BaseCommand):
    help = 'Cria postos de trabalho de exemplo para o sistema'

    def handle(self, *args, **options):
        postos_exemplo = [
            {
                'nome': 'Posto 1 - Entrada Principal',
                'descricao': 'Posto localizado na entrada principal do shopping, responsável pelo primeiro atendimento aos participantes.'
            },
            {
                'nome': 'Posto 2 - Centro Comercial',
                'descricao': 'Posto localizado no centro do shopping, próximo às principais lojas.'
            },
            {
                'nome': 'Posto 3 - Praça de Alimentação',
                'descricao': 'Posto localizado na praça de alimentação, para atendimento durante horários de refeição.'
            },
            {
                'nome': 'Posto 4 - Estacionamento',
                'descricao': 'Posto localizado no estacionamento, para atendimento de motoristas.'
            },
            {
                'nome': 'Posto 5 - Backoffice',
                'descricao': 'Posto administrativo para operações internas e suporte.'
            }
        ]

        postos_criados = 0
        for posto_data in postos_exemplo:
            posto, created = PostoTrabalho.objects.get_or_create(
                nome=posto_data['nome'],
                defaults={'descricao': posto_data['descricao']}
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Posto criado: {posto.nome}')
                )
                postos_criados += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Posto já existe: {posto.nome}')
                )

        total_postos = PostoTrabalho.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'\n🎯 Resumo: {postos_criados} novos postos criados')
        )
        self.stdout.write(
            self.style.SUCCESS(f'📊 Total de postos no sistema: {total_postos}')
        ) 