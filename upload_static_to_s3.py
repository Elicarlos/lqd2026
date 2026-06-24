# upload_static_to_s3.py
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'liquida2018.settings')
django.setup()

from liquida2018.storage_backends import StaticStorage
from django.core.files.base import ContentFile
from django.conf import settings

storage = StaticStorage()
static_root = settings.STATIC_ROOT
uploaded = 0
errors = 0
skipped = 0

print("=" * 60)
print("UPLOAD DE ARQUIVOS ESTÁTICOS PARA S3")
print("=" * 60)
print(f"STATIC_ROOT: {static_root}")
print(f"S3 Bucket: {storage.bucket_name}")
print(f"S3 Location: {storage.location}")
print("=" * 60)

if not os.path.exists(static_root):
    print(f"❌ STATIC_ROOT não existe: {static_root}")
    print("Execute 'python manage.py collectstatic' primeiro!")
    exit(1)

# Percorrer todos os arquivos em STATIC_ROOT
for root, dirs, files in os.walk(static_root):
    for file in files:
        # Caminho completo do arquivo local
        local_path = os.path.join(root, file)
        
        # Caminho relativo (sem STATIC_ROOT)
        relative_path = os.path.relpath(local_path, static_root)
        
        # Normalizar caminho para usar / no S3
        s3_path = relative_path.replace('\\', '/')
        
        try:
            # Verificar se já existe no S3
            if storage.exists(s3_path):
                skipped += 1
                if skipped % 50 == 0:
                    print(f"Pulados {skipped} arquivos (já existem)...")
                continue
            
            # Ler arquivo
            with open(local_path, 'rb') as f:
                content = f.read()
            
            # Upload para S3
            storage.save(s3_path, ContentFile(content))
            uploaded += 1
            
            if uploaded % 10 == 0:
                print(f"✅ Uploaded {uploaded} files... (último: {s3_path})")
                
        except Exception as e:
            errors += 1
            print(f"❌ Erro ao fazer upload de {s3_path}: {e}")

print("=" * 60)
print(f"✅ Upload concluído!")
print(f"   Arquivos enviados: {uploaded}")
print(f"   Arquivos pulados (já existem): {skipped}")
print(f"   Erros: {errors}")
print("=" * 60)