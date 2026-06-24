# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('participante', '0013_increase_phone_field_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='DashboardCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('codename', models.CharField(max_length=50, unique=True)),
                ('card_type', models.CharField(choices=[('participantes', 'Participantes'), ('lojistas', 'Lojistas'), ('configuracoes', 'Configurações'), ('backoffice', 'Backoffice'), ('relatorios', 'Relatórios'), ('documentos', 'Documentos'), ('usuarios', 'Usuários'), ('campanha', 'Campanha'), ('ponto', 'Registro de Ponto'), ('impressao', 'Impressão'), ('estatisticas', 'Estatísticas')], max_length=20)),
                ('title', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('url_name', models.CharField(blank=True, max_length=100)),
                ('icon', models.CharField(default='fas fa-cog', max_length=50)),
                ('color', models.CharField(default='blue', max_length=20)),
                ('order', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('is_system_card', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Card do Dashboard',
                'verbose_name_plural': 'Cards do Dashboard',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='RoleCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='participante.dashboardcard')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='participante.systemrole')),
            ],
            options={
                'verbose_name': 'Card da Função',
                'verbose_name_plural': 'Cards das Funções',
                'unique_together': {('role', 'card')},
            },
        ),
    ] 