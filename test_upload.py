# test_upload.py (criar temporariamente)
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'liquida2018.settings')
django.setup()

from liquida2018.storage_backends import MediaStorage
from io import BytesIO

def main():
    # Criar um arquivo de teste
    test_content = b"Test file content"
    test_file = BytesIO(test_content)
    test_file.name = "test_upload.txt"

    # Tentar fazer upload
    storage = MediaStorage()
    try:
        file_path = storage.save("test/test_upload.txt", test_file)
        print(f"[OK] Upload bem-sucedido! Arquivo salvo em: {file_path}")
        print(f"URL: {storage.url(file_path)}")
    except Exception as e:
        print(f"[ERRO] Erro no upload: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()