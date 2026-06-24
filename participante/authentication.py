from django.contrib.auth.models import User


class CPFAuthBackend:
    """
    Authenticate using CPF.
    """

    def authenticate(self, request, username=None, password=None):
        try:
            # Tenta encontrar o usuário com o CPF formatado
            user = User.objects.get(username=username)
            if user.check_password(password):
                return user
            return None
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
