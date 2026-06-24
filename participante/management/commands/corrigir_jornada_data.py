from django.core.management.base import BaseCommand
from participante.models import JornadaColaborador, Profile
from datetime import date

class Command(BaseCommand):
    help = 'Corrige a data de inicio da jornada para hoje'

    def add_arguments(self, parser):
        parser.add_argument('cpf', type=str, help='CPF do usuario')

    def handle(self, *args, **options):
        cpf = options['cpf']
        
        try:
            # Buscar pelo CPF no Profile
            profile = Profile.objects.get(CPF=cpf)
            user = profile.user
            
            self.stdout.write(f"=== CORRIGINDO JORNADA PARA CPF {cpf} ===")
            
            # Buscar jornadas do usuario
            jornadas = JornadaColaborador.objects.filter(colaborador=user, ativo=True)
            
            if not jornadas.exists():
                self.stdout.write(self.style.ERROR("Nenhuma jornada ativa encontrada"))
                return
            
            hoje = date.today()
            
            for jornada in jornadas:
                self.stdout.write(f"Jornada ID: {jornada.id}")
                self.stdout.write(f"Tipo: {jornada.tipo_jornada.nome}")
                self.stdout.write(f"Data inicio atual: {jornada.data_inicio}")
                self.stdout.write(f"Data inicio nova: {hoje}")
                
                # Alterar data de inicio para hoje
                jornada.data_inicio = hoje
                jornada.save()
                
                self.stdout.write(self.style.SUCCESS(f"Jornada {jornada.id} corrigida com sucesso!"))
                self.stdout.write(f"Vigente hoje: {jornada.is_vigente(hoje)}")
                
        except Profile.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Usuario com CPF '{cpf}' nao encontrado"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"ERRO: {e}"))
