from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class RegisterViewTestCase(TestCase):
    def setUp(self):
        self.register_url = reverse("participante:register")
        self.user_data = {
            "username": "249.118.300-50",  # CPF válido com 11 caracteres
            "password": "teste123",  # Ajustado para password1 e password2
            "password2": "teste123",
            "email": "testuser@example.com",
            "nome": "Test User",
            "CPF": "249.118.300-50",  # Supondo que CPF é username e válido
            "sexo": "M",
            "date_of_birth": "1990-01-01",  # Campo obrigatório
            "pergunta": "liquida_teresina_2025",  # Campo obrigatório
            "termos_de_aceite": True,  # Campo obrigatório
            "foneCelular1": "1234567890",
            "endereco": "Test Address",
            "bairro": "Test Bairro",
            "cidade": "Test Cidade",
            "estado": "PI",
        }

    def test_register_page_accessible(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "participante/registerpart-new.html")

    def test_register_user_success(self):
        self.client.post(self.register_url, self.user_data)
        cpf_limpo = "".join(filter(str.isdigit, self.user_data["username"]))
        user_exists = User.objects.filter(username=cpf_limpo).exists()
        self.assertTrue(user_exists, "Usuário não foi criado corretamente")

    def test_register_user_duplicate(self):
        # Primeiro, criar um usuário com os dados fornecidos
        self.client.post(self.register_url, self.user_data)

        # Tentar registrar o mesmo usuário novamente
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, 200)
        
        user_form = response.context["user_form"]
        self.assertFalse(user_form.is_valid())
        self.assertIn("username", user_form.errors)
