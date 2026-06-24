import os
import django
from django.conf import settings

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'liquida2018.settings')
    django.setup()

    print("=" * 60)
    print("DIAGNOSTICO DETALHADO S3")
    print("=" * 60)

    # 1. Verificar configurações
    print("\n1 CONFIGURACOES DJANGO")
    print(f"   USE_S3: {settings.USE_S3}")
    print(f"   DEBUG: {settings.DEBUG}")
    print(f"   DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
    print(f"   STATICFILES_STORAGE: {settings.STATICFILES_STORAGE}")

    # 2. Verificar credenciais
    print("\n2 CREDENCIAIS AWS")
    print(f"   AWS_ACCESS_KEY_ID: {settings.AWS_ACCESS_KEY_ID[:10]}..." if settings.AWS_ACCESS_KEY_ID else "   [ERRO] NAO CONFIGURADO")
    print(f"   AWS_SECRET_ACCESS_KEY: {'[OK]' if settings.AWS_SECRET_ACCESS_KEY else '[ERRO]'}")
    print(f"   AWS_STORAGE_BUCKET_NAME: {settings.AWS_STORAGE_BUCKET_NAME}")
    print(f"   AWS_S3_REGION_NAME: {settings.AWS_S3_REGION_NAME}")
    print(f"   AWS_S3_CUSTOM_DOMAIN: {settings.AWS_S3_CUSTOM_DOMAIN}")
    print(f"   AWS_DEFAULT_ACL: {settings.AWS_DEFAULT_ACL}")

    # 3. Testar com boto3 direto
    print("\n3 TESTE COM BOTO3 (Conexao direta)")
    try:
        import boto3
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        response = s3_client.list_objects_v2(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            MaxKeys=5
        )
        
        print(f"   [OK] Conexao S3 bem-sucedida!")
        print(f"   Objetos no bucket: {response.get('KeyCount', 0)}")
        
    except Exception as e:
        print(f"   [ERRO] Erro na conexao: {e}")

    # 4. Testar upload com boto3 direto (SEM ACL)
    print("\n4 TESTE DE UPLOAD COM BOTO3 (SEM ACL)")
    try:
        import boto3
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        # Upload SEM ACL - REMOVA QUALQUER MENÇÃO A ACL
        s3_client.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key='teste_direto.txt',
            Body=b'Teste de upload direto'
        )
        
        print(f"   [OK] Upload com boto3 bem-sucedido!")
        url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/teste_direto.txt"
        print(f"   URL: {url}")
        
    except Exception as e:
        print(f"   [ERRO] Erro no upload: {e}")
        import traceback
        traceback.print_exc()

    # 5. Testar com Django storage
    print("\n5 TESTE COM DJANGO STORAGE")
    try:
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        
        content = ContentFile("Teste Django Storage")
        path = default_storage.save('teste_django.txt', content)
        url = default_storage.url(path)
        
        print(f"   [OK] Upload com Django bem-sucedido!")
        print(f"   Caminho: {path}")
        print(f"   URL: {url}")
        
    except Exception as e:
        print(f"   [ERRO] Erro: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("FIM DO DIAGNOSTICO")
    print("=" * 60)

if __name__ == "__main__":
    main()