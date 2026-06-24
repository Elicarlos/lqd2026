from storages.backends.s3boto3 import S3Boto3Storage
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os


class MediaStorage(S3Boto3Storage):
    location = "media"
    file_overwrite = False
    querystring_auth = False
    default_acl = None  # Bucket não permite ACLs, acesso público via política do bucket


class StaticStorage(S3Boto3Storage):
    location = "static"
    querystring_auth = False
    file_overwrite = False
    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)  # Usa getattr para segurança


class HybridStorage(FileSystemStorage):
    """
    Storage híbrido que tenta local primeiro, depois S3
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.s3_storage = MediaStorage() if hasattr(settings, 'AWS_ACCESS_KEY_ID') and settings.AWS_ACCESS_KEY_ID else None
    
    def _open(self, name, mode='rb'):
        """Tenta abrir localmente, se não encontrar, tenta S3"""
        try:
            return super()._open(name, mode)
        except FileNotFoundError:
            if self.s3_storage:
                try:
                    return self.s3_storage._open(name, mode)
                except:
                    pass
            raise FileNotFoundError(f"File {name} not found in local or S3 storage")
    
    def exists(self, name):
        """Verifica se existe localmente ou no S3"""
        if super().exists(name):
            return True
        if self.s3_storage:
            return self.s3_storage.exists(name)
        return False
    
    def url(self, name):
        """Retorna URL local se existir, senão URL do S3"""
        if super().exists(name):
            return super().url(name)
        if self.s3_storage and self.s3_storage.exists(name):
            return self.s3_storage.url(name)
        return super().url(name)