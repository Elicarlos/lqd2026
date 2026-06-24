from django.core.management.base import BaseCommand
from participante.tasks import finalizar_jornadas_automaticas


class Command(BaseCommand):
    help = 'Testa a finalização automática de jornadas manualmente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa em modo de teste (não finaliza realmente)',
        )

    def handle(self, *args, **options):
        self.stdout.write('🧪 Testando finalização automática de jornadas...')
        
        if options['dry_run']:
            self.stdout.write('🔍 Modo de teste ativado (não finalizará jornadas)')
        
        # Executar a tarefa
        try:
            result = finalizar_jornadas_automaticas.delay()
            self.stdout.write(f'✅ Tarefa executada com sucesso! ID: {result.id}')
            
            # Aguardar o resultado
            result.get(timeout=30)
            self.stdout.write('✅ Tarefa concluída!')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erro ao executar tarefa: {e}')
            )
