from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from participante.models import PostoTrabalho, RegistroJornada, Profile

class ParticipanteAPIV1TestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpassword123"
        )
        self.profile = Profile.objects.create(
            user=self.user,
            CPF="98765432109",
            nome="Test User"
        )
        self.posto = PostoTrabalho.objects.create(
            nome="Posto de Teste",
            descricao="Descricao do posto de teste"
        )
        self.profile.posto_trabalho = self.posto
        self.profile.save()
        self.client.force_authenticate(user=self.user)

    def test_list_posto_trabalho(self):
        url = reverse("postotrabalho-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["nome"], self.posto.nome)

    def test_create_posto_trabalho(self):
        url = reverse("postotrabalho-list")
        data = {
            "nome": "Novo Posto",
            "descricao": "Nova Descricao"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PostoTrabalho.objects.count(), 2)

    def test_detail_posto_trabalho(self):
        url = reverse("postotrabalho-detail", kwargs={"pk": self.posto.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nome"], self.posto.nome)

    def test_update_posto_trabalho(self):
        url = reverse("postotrabalho-detail", kwargs={"pk": self.posto.pk})
        data = {
            "nome": "Posto Atualizado",
            "descricao": "Descricao atualizada"
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.posto.refresh_from_db()
        self.assertEqual(self.posto.nome, "Posto Atualizado")

    def test_delete_posto_trabalho(self):
        url = reverse("postotrabalho-detail", kwargs={"pk": self.posto.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(PostoTrabalho.objects.count(), 0)

    def test_bater_ponto_iniciar_sucesso(self):
        url = reverse("ponto_registrar")
        data = {"acao": "iniciar"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "iniciado")
        self.assertTrue(RegistroJornada.objects.filter(user=self.user, horario_fim__isnull=True).exists())

    def test_bater_ponto_iniciar_duplicado(self):
        url = reverse("ponto_registrar")
        self.client.post(url, {"acao": "iniciar"})
        response = self.client.post(url, {"acao": "iniciar"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_bater_ponto_finalizar_sucesso(self):
        url = reverse("ponto_registrar")
        self.client.post(url, {"acao": "iniciar"})
        response = self.client.post(url, {"acao": "finalizar"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "finalizado")
        self.assertFalse(RegistroJornada.objects.filter(user=self.user, horario_fim__isnull=True).exists())

    def test_bater_ponto_finalizar_sem_jornada_ativa(self):
        url = reverse("ponto_registrar")
        response = self.client.post(url, {"acao": "finalizar"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_bater_ponto_acao_invalida(self):
        url = reverse("ponto_registrar")
        response = self.client.post(url, {"acao": "invalida"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_historico_ponto(self):
        url = reverse("ponto_registrar")
        self.client.post(url, {"acao": "iniciar"})
        self.client.post(url, {"acao": "finalizar"})
        
        url_historico = reverse("ponto_historico")
        response = self.client.get(url_historico)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["status"], "ATIVA")  # O status padrão do RegistroJornada no models é ATIVA
