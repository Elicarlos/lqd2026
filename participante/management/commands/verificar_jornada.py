from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from participante.models import JornadaColaborador, TipoJornada, Profile
from datetime import date

class Command(BaseCommand):
    help = 'Verifica a jornada de trabalho de um usuario por CPF'

    def add_arguments(self, parser):
        parser.add_argument('cpf', type=str, help='CPF do usuario')

    def handle(self, *args, **options):
        cpf = options['cpf']
        
        try:
            # Buscar pelo CPF no Profile
            profile = Profile.objects.get(CPF=cpf)
            user = profile.user
            
            self.stdout.write(f"=== VERIFICACAO DE JORNADA PARA CPF {cpf} ===")
            self.stdout.write(f"Username: {user.username}")
            self.stdout.write(f"Nome: {user.get_full_name() or user.username}")
            self.stdout.write(f"Email: {user.email}")
            self.stdout.write(f"Ativo: {user.is_active}")
            self.stdout.write(f"Staff: {user.is_staff}")
            self.stdout.write(f"Superuser: {user.is_superuser}")
            
            # Verificar grupos
            grupos = list(user.groups.all())
            self.stdout.write(f"Grupos: {[g.name for g in grupos]}")
            
            # Verificar UserRoles
            from participante.models import UserRole
            user_roles = UserRole.objects.filter(user=user).values_list('role__name', flat=True)
            self.stdout.write(f"UserRoles: {list(user_roles)}")
            
            # Verificar se precisa de jornada
            grupos_jornada = ["Operador", "Operadores", "Backoffice", "Supervisor", "Suporte"]
            precisa_jornada = (
                any(user.groups.filter(name=grupo).exists() for grupo in grupos_jornada) or
                any(role in grupos_jornada for role in user_roles)
            )
            self.stdout.write(f"Precisa de jornada: {precisa_jornada}")
            
            if not precisa_jornada:
                self.stdout.write(self.style.SUCCESS("OK - Usuario nao precisa de controle de jornada"))
                return
            
            # Verificar jornadas atribuidas
            hoje = date.today()
            self.stdout.write(f"\n--- JORNADAS ATRIBUIDAS (Data: {hoje}) ---")
            
            jornadas = JornadaColaborador.objects.filter(colaborador=user)
            if not jornadas.exists():
                self.stdout.write(self.style.ERROR("ERRO - Nenhuma jornada atribuida encontrada"))
                
                # Listar tipos disponiveis
                tipos = TipoJornada.objects.filter(ativo=True)
                self.stdout.write("\nTipos de jornada disponiveis:")
                for tipo in tipos:
                    self.stdout.write(f"ID {tipo.id}: {tipo.nome} ({tipo.hora_inicio} - {tipo.hora_fim})")
                return
            
            for jornada in jornadas:
                self.stdout.write(f"\nJornada ID: {jornada.id}")
                self.stdout.write(f"Tipo: {jornada.tipo_jornada.nome}")
                self.stdout.write(f"Data inicio: {jornada.data_inicio}")
                self.stdout.write(f"Data fim: {jornada.data_fim or 'Indefinido'}")
                self.stdout.write(f"Ativo: {jornada.ativo}")
                self.stdout.write(f"Vigente hoje: {jornada.is_vigente(hoje)}")
                
                if jornada.is_vigente(hoje):
                    self.stdout.write(self.style.SUCCESS("OK - Esta jornada esta vigente hoje"))
                    
                    # Verificar horario
                    pode_logar, mensagem = jornada.tipo_jornada.pode_logar_agora()
                    self.stdout.write(f"Pode logar agora: {pode_logar}")
                    self.stdout.write(f"Mensagem: {mensagem}")
                else:
                    self.stdout.write(self.style.ERROR("ERRO - Esta jornada nao esta vigente hoje"))
            
            # Verificar jornada ativa
            jornada_ativa = JornadaColaborador.get_jornada_ativa(user, hoje)
            if jornada_ativa:
                self.stdout.write(self.style.SUCCESS(f"\nOK - JORNADA ATIVA ENCONTRADA: {jornada_ativa}"))
            else:
                self.stdout.write(self.style.ERROR(f"\nERRO - NENHUMA JORNADA ATIVA ENCONTRADA"))
                
        except Profile.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"ERRO - Usuario com CPF '{cpf}' nao encontrado"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"ERRO: {e}"))
