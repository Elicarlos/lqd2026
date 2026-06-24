# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('participante', '0024_update_card_types'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuracaosecao',
            name='cor',
            field=models.CharField(
                default='#0d6efd',
                help_text='Código hexadecimal (ex: #0d6efd)',
                max_length=7,
                verbose_name='Cor do Cabeçalho'
            ),
        ),
    ]
