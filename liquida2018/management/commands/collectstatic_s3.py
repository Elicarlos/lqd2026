from django.core.management.base import BaseCommand
from django.core.management import call_command
from liquida2018.storage_backends import StaticStorage
from django.core.files.base import ContentFile
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Coleta arquivos estáticos e faz upload para S3'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-upload',
            action='store_true',
            help='Apenas coletar, não fazer upload para S3',
        )

    def handle(self, *args, **options):
        # 1. Coletar arquivos
        self.stdout.write('📦 Coletando arquivos estáticos...')
        call_command('collectstatic', '--noinput', verbosity=1)
        
        # 2. Upload para S3 (se USE_S3 estiver ativo)
        if getattr(settings, 'USE_S3', False) and not options['no_upload']:
            self.stdout.write('☁️  Fazendo upload para S3...')
            storage = StaticStorage()
            static_root = settings.STATIC_ROOT
            uploaded = 0
            skipped = 0
            errors = 0
            
            if not os.path.exists(static_root):
                self.stdout.write(self.style.ERROR(f'❌ STATIC_ROOT não existe: {static_root}'))
                return
            
            for root, dirs, files in os.walk(static_root):
                for file in files:
                    local_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_path, static_root)
                    s3_path = relative_path.replace('\\', '/')
                    
                    try:
                        if storage.exists(s3_path):
                            skipped += 1
                            continue
                        
                        with open(local_path, 'rb') as f:
                            storage.save(s3_path, ContentFile(f.read()))
                        uploaded += 1
                        
                        if uploaded % 50 == 0:
                            self.stdout.write(f'   ✅ {uploaded} arquivos enviados...')
                    except Exception as e:
                        errors += 1
                        self.stdout.write(self.style.ERROR(f'   ❌ Erro em {s3_path}: {e}'))
            
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Upload concluído! '
                f'Enviados: {uploaded} | Pulados: {skipped} | Erros: {errors}'
            ))
        else:
            self.stdout.write('ℹ️  Upload para S3 pulado (USE_S3=False ou --no-upload)')