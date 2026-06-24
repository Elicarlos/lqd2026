from django.core.management.base import BaseCommand
from participante.models import CardDinamico
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Corrige permissões do card autorizar_lojista para incluir Backoffice'

    def handle(self, *args, **options):
        self.stdout.write("🔧 Corrigindo permissões do card autorizar_lojista...")
        
        try:
            # Buscar o card autorizar_lojista
            card = CardDinamico.objects.get(nome='autorizar_lojista')
            self.stdout.write(f"✅ Card encontrado: {card.nome}")
            
            # Verificar grupos atuais
            grupos_atuais = card.grupos_permitidos.all()
            self.stdout.write(f"   - Grupos atuais: {[g.name for g in grupos_atuais]}")
            
            # Grupos que devem ter acesso
            grupos_importantes = ['Backoffice', 'Gerente', 'Supervisor', 'Gerente Solve', 'Operador']
            
            for nome_grupo in grupos_importantes:
                try:
                    grupo = Group.objects.get(name=nome_grupo)
                    if grupo not in card.grupos_permitidos.all():
                        card.grupos_permitidos.add(grupo)
                        self.stdout.write(
                            self.style.SUCCESS(f"✅ Adicionado grupo {nome_grupo}")
                        )
                    else:
                        self.stdout.write(f"✅ Grupo {nome_grupo} já existe")
                except Group.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️ Grupo {nome_grupo} não encontrado")
                    )
            
            # Verificar resultado final
            grupos_finais = card.grupos_permitidos.all()
            self.stdout.write(
                self.style.SUCCESS(f"\n🎉 PERMISSÕES CORRIGIDAS!")
            )
            self.stdout.write(f"   - Grupos finais: {[g.name for g in grupos_finais]}")
            
            # Testar com usuário Backoffice
            try:
                grupo_backoffice = Group.objects.get(name='Backoffice')
                usuarios_backoffice = grupo_backoffice.user_set.all()
                if usuarios_backoffice:
                    user = usuarios_backoffice[0]
                    pode_ver = card.pode_ver(user)
                    self.stdout.write(f"   - {user.username} pode ver: {pode_ver}")
                    
                    if pode_ver:
                        self.stdout.write(
                            self.style.SUCCESS("🎉 SUCESSO! Usuários Backoffice agora podem acessar!")
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR("❌ PROBLEMA: Usuário ainda não pode acessar")
                        )
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING("⚠️ Grupo Backoffice não encontrado")
                )
                
        except CardDinamico.DoesNotExist:
            self.stdout.write(
                self.style.ERROR("❌ Card 'autorizar_lojista' NÃO EXISTE!")
            )
