# Generated manually to fix autorizar_lojista permissions

from django.db import migrations

def fix_autorizar_lojista_permissions(apps, schema_editor):
    """Corrige permissões do card autorizar_lojista para incluir Backoffice"""
    CardDinamico = apps.get_model('participante', 'CardDinamico')
    Group = apps.get_model('auth', 'Group')
    
    try:
        # Buscar o card autorizar_lojista
        card = CardDinamico.objects.get(nome='autorizar_lojista')
        
        # Buscar grupos importantes
        grupos_importantes = ['Backoffice', 'Gerente', 'Supervisor', 'Gerente Solve', 'Operador']
        
        for nome_grupo in grupos_importantes:
            try:
                grupo = Group.objects.get(name=nome_grupo)
                if grupo not in card.grupos_permitidos.all():
                    card.grupos_permitidos.add(grupo)
                    print(f"[OK] Adicionado grupo {nome_grupo} ao card autorizar_lojista")
            except Group.DoesNotExist:
                print(f"[AVISO] Grupo {nome_grupo} não encontrado")
                
    except CardDinamico.DoesNotExist:
        print("[AVISO] Card autorizar_lojista não encontrado")

def reverse_fix_autorizar_lojista_permissions(apps, schema_editor):
    """Reverte as permissões (opcional)"""
    CardDinamico = apps.get_model('participante', 'CardDinamico')
    Group = apps.get_model('auth', 'Group')
    
    try:
        card = CardDinamico.objects.get(nome='autorizar_lojista')
        grupo_backoffice = Group.objects.get(name='Backoffice')
        card.grupos_permitidos.remove(grupo_backoffice)
        print("[OK] Removido grupo Backoffice do card autorizar_lojista")
    except (CardDinamico.DoesNotExist, Group.DoesNotExist):
        pass

class Migration(migrations.Migration):

    dependencies = [
        ('participante', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            fix_autorizar_lojista_permissions,
            reverse_fix_autorizar_lojista_permissions
        ),
    ]
