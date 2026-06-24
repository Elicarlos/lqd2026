from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from datetime import datetime


class Command(BaseCommand):
    help = 'Configura a tarefa de finalização automática de jornadas'

    def handle(self, *args, **options):
        self.stdout.write('🔧 Configurando finalização automática de jornadas...')
        
        # Criar ou atualizar o agendamento para executar a cada 5 minutos
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )
        
        if created:
            self.stdout.write('✅ Agendamento criado: a cada 5 minutos')
        else:
            self.stdout.write('✅ Agendamento já existe: a cada 5 minutos')
        
        # Criar ou atualizar a tarefa periódica
        task, created = PeriodicTask.objects.get_or_create(
            name='Finalizar Jornadas Automáticas',
            defaults={
                'task': 'participante.tasks.finalizar_jornadas_automaticas',
                'interval': schedule,
                'enabled': True,
            }
        )
        
        if not created:
            # Atualizar a tarefa existente
            task.task = 'participante.tasks.finalizar_jornadas_automaticas'
            task.interval = schedule
            task.enabled = True
            task.save()
            self.stdout.write('✅ Tarefa atualizada')
        else:
            self.stdout.write('✅ Tarefa criada')
        
        self.stdout.write(
            self.style.SUCCESS(
                '🎉 Configuração concluída! A finalização automática de jornadas será executada a cada 5 minutos.'
            )
        )
        
        # Mostrar informações sobre a configuração
        self.stdout.write('\n📋 Informações da configuração:')
        self.stdout.write(f'   - Tarefa: {task.task}')
        self.stdout.write(f'   - Intervalo: {schedule.every} {schedule.period}')
        self.stdout.write(f'   - Ativa: {task.enabled}')
        self.stdout.write(f'   - Próxima execução: {task.next_run_at or "Não agendada"}')
        
        self.stdout.write('\n💡 Como funciona:')
        self.stdout.write('   1. A cada 5 minutos, o sistema verifica jornadas ativas')
        self.stdout.write('   2. Para cada jornada, calcula o horário limite (fim + tolerância)')
        self.stdout.write('   3. Se passou do limite, finaliza automaticamente')
        self.stdout.write('   4. Desloga o usuário e limpa o posto de trabalho')
