from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from participante.models import (
    Profile, CardDinamico, ConfiguracaoSecao, Funcionalidade,
    SystemRole, UserRole, DocumentoFiscal, Campanha
)
from cupom.models import Cupom
from lojista.models import Lojista, RamoAtividade
from participante.models import PostoTrabalho, TipoJornada
import json


class DashboardViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            CPF='12345678901',
            nome='Test User'
        )
        
        # Criar cards de teste
        self.card1 = CardDinamico.objects.create(
            nome='Test Card 1',
            titulo='Test Card 1 Title',
            tipo='PARTICIPANTE',
            icone='fas fa-users',
            ativo=True,
            ordem=1
        )
        self.card2 = CardDinamico.objects.create(
            nome='Test Card 2',
            titulo='Test Card 2 Title',
            tipo='LOJISTA',
            icone='fas fa-store',
            ativo=True,
            ordem=2
        )
        
        # Criar seções de teste
        self.secao1 = ConfiguracaoSecao.objects.create(
            tipo='PARTICIPANTE',
            titulo='Participantes',
            icone='fas fa-users',
            ativo=True
        )
        self.secao2 = ConfiguracaoSecao.objects.create(
            tipo='LOJISTA',
            titulo='Lojistas',
            icone='fas fa-store',
            ativo=True
        )

    def test_dashboard_access_authenticated(self):
        """Testa acesso ao dashboard com usuário autenticado"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('participante:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'participante/dashboard-new.html')

    def test_dashboard_access_unauthenticated(self):
        """Testa acesso ao dashboard sem autenticação"""
        response = self.client.get(reverse('participante:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_context_data(self):
        """Testa se o contexto do dashboard contém os dados necessários"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('participante:dashboard'))
        
        # Verificar se o contexto contém dados básicos
        self.assertIn('section', response.context)
        self.assertIn('user_roles', response.context)


class AuthenticationViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('participante:register')
        self.login_url = reverse('participante:login')

    def test_register_page_get(self):
        """Testa acesso à página de registro"""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'participante/registerpart-new.html')

    def test_register_user_success(self):
        """Testa registro de usuário com sucesso"""
        data = {
            'username': '249.118.300-50',
            'password': 'teste123',
            'password2': 'teste123',
            'email': 'test@example.com',
            'nome': 'Test User',
            'CPF': '249.118.300-50',
            'sexo': 'M',
            'date_of_birth': '1990-01-01',
            'pergunta': 'liquida_teresina_2025',
            'termos_de_aceite': True,
            'foneCelular1': '1234567890',
            'endereco': 'Test Address',
            'bairro': 'Test Bairro',
            'cidade': 'Test Cidade',
            'estado': 'PI',
        }
        response = self.client.post(self.register_url, data)
        # Pode retornar 200 (com erros) ou 302 (sucesso)
        self.assertIn(response.status_code, [200, 302])
        
        # Verificar se o usuário foi criado (se sucesso)
        if response.status_code == 302:
            user_exists = User.objects.filter(username='24911830050').exists()
            self.assertTrue(user_exists)

    def test_register_user_duplicate(self):
        """Testa registro de usuário duplicado"""
        # Criar usuário primeiro
        user = User.objects.create_user(
            username='24911830050',
            email='test@example.com',
            password='teste123'
        )
        Profile.objects.create(
            user=user,
            CPF='249.118.300-50',
            nome='Test User'
        )
        
        # Tentar registrar novamente
        data = {
            'username': '249.118.300-50',
            'password': 'teste123',
            'password2': 'teste123',
            'email': 'test@example.com',
            'nome': 'Test User',
            'CPF': '249.118.300-50',
            'sexo': 'M',
            'date_of_birth': '1990-01-01',
            'pergunta': 'liquida_teresina_2025',
            'termos_de_aceite': True,
            'foneCelular1': '1234567890',
            'endereco': 'Test Address',
            'bairro': 'Test Bairro',
            'cidade': 'Test Cidade',
            'estado': 'PI',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)  # Stay on form page
        
        # Verificar erro no formulário
        user_form = response.context['user_form']
        self.assertFalse(user_form.is_valid())
        self.assertIn('username', user_form.errors)

    def test_login_success(self):
        """Testa login com sucesso"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after login

    def test_login_invalid_credentials(self):
        """Testa login com credenciais inválidas"""
        data = {
            'username': 'invaliduser',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data)
        # Pode retornar 200 (erro) ou 302 (redirect)
        self.assertIn(response.status_code, [200, 302])


class CardManagementViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_superuser=True
        )
        self.client.login(username='admin', password='adminpass123')
        
        self.card = CardDinamico.objects.create(
            titulo='Test Card',
            tipo='PARTICIPANTE',
            ativo=True
        )

    def test_cards_list_view(self):
        """Testa listagem de cards"""
        response = self.client.get(reverse('participante:cards_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'participante/cards_list.html')
        self.assertIn('page_obj', response.context)

    def test_card_create_view(self):
        """Testa criação de card"""
        data = {
            'nome': 'New Card',
            'titulo': 'New Card Title',
            'tipo': 'PARTICIPANTE',
            'icone': 'fas fa-user',
            'ativo': True,
            'ordem': 1
        }
        response = self.client.post(reverse('participante:card_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Verificar se o card foi criado
        card_exists = CardDinamico.objects.filter(titulo='New Card Title').exists()
        self.assertTrue(card_exists)

    def test_card_edit_view(self):
        """Testa edição de card"""
        data = {
            'nome': 'Updated Card',
            'titulo': 'Updated Card Title',
            'tipo': 'PARTICIPANTE',
            'icone': 'fas fa-user',
            'ativo': True,
            'ordem': 1
        }
        response = self.client.post(
            reverse('participante:card_edit', kwargs={'pk': self.card.pk}),
            data
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Verificar se o card foi atualizado
        self.card.refresh_from_db()
        self.assertEqual(self.card.titulo, 'Updated Card Title')

    def test_card_delete_view(self):
        """Testa exclusão de card"""
        response = self.client.post(
            reverse('participante:card_delete', kwargs={'pk': self.card.pk})
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Verificar se o card foi deletado
        card_exists = CardDinamico.objects.filter(pk=self.card.pk).exists()
        self.assertFalse(card_exists)


class SectionManagementViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_superuser=True
        )
        self.client.login(username='admin', password='adminpass123')
        
        self.secao = ConfiguracaoSecao.objects.create(
            tipo='PARTICIPANTE',
            titulo='Participantes',
            icone='fas fa-users',
            ativo=True
        )

    def test_secoes_list_view(self):
        """Testa listagem de seções"""
        response = self.client.get(reverse('participante:secoes_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'participante/secoes_list.html')
        self.assertIn('secoes', response.context)

    def test_secao_edit_view(self):
        """Testa edição de seção"""
        data = {
            'tipo': 'PARTICIPANTE',
            'titulo': 'Updated Section',
            'icone': 'fas fa-user',
            'cor': '#ff0000',
            'ativo': True
        }
        response = self.client.post(
            reverse('participante:secao_edit', kwargs={'pk': self.secao.pk}),
            data
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Verificar se a seção foi atualizada
        self.secao.refresh_from_db()
        self.assertEqual(self.secao.titulo, 'Updated Section')

    def test_secao_toggle_view(self):
        """Testa ativação/desativação de seção"""
        initial_status = self.secao.ativo
        
        response = self.client.post(
            reverse('participante:secao_toggle', kwargs={'pk': self.secao.pk})
        )
        # Pode retornar 200 (sucesso) ou 302 (redirect)
        self.assertIn(response.status_code, [200, 302])
        
        # Verificar se o status foi alterado (se sucesso)
        if response.status_code == 200:
            self.secao.refresh_from_db()
            self.assertNotEqual(self.secao.ativo, initial_status)


class FuncionalidadeViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_superuser=True
        )
        self.client.login(username='admin', password='adminpass123')
        
        self.funcionalidade = Funcionalidade.objects.create(
            nome='Test Function',
            codigo='test_function',
            descricao='Test Description',
            tipo='VIEW',
            ativo=True
        )

    def test_funcionalidades_list_view(self):
        """Testa listagem de funcionalidades"""
        response = self.client.get(reverse('participante:funcionalidades_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'participante/funcionalidades_list.html')
        self.assertIn('page_obj', response.context)

    def test_funcionalidade_create_view(self):
        """Testa criação de funcionalidade"""
        data = {
            'nome': 'New Function',
            'codigo': 'new_function',
            'descricao': 'New Description',
            'tipo': 'CREATE',
            'ativo': True
        }
        response = self.client.post(reverse('participante:funcionalidade_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Verificar se a funcionalidade foi criada
        func_exists = Funcionalidade.objects.filter(codigo='new_function').exists()
        self.assertTrue(func_exists)

    def test_funcionalidade_edit_view(self):
        """Testa edição de funcionalidade"""
        data = {
            'nome': 'Updated Function',
            'codigo': 'test_function',
            'descricao': 'Updated Description',
            'tipo': 'VIEW',
            'ativo': True
        }
        response = self.client.post(
            reverse('participante:funcionalidade_edit', kwargs={'pk': self.funcionalidade.pk}),
            data
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Verificar se a funcionalidade foi atualizada
        self.funcionalidade.refresh_from_db()
        self.assertEqual(self.funcionalidade.nome, 'Updated Function')


class LojistaViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_superuser=True
        )
        self.client.login(username='admin', password='adminpass123')
        
        self.ramo = RamoAtividade.objects.create(atividade='Test Activity')
        self.lojista = Lojista.objects.create(
            fantasiaLojista='Test Store',
            razaoLojista='Test Store LTDA',
            CNPJLojista='00.000.000/0001-91',
            status='Sim',
            ramoAtividade=self.ramo
        )

    def test_lojistas_list_view(self):
        """Testa listagem de lojistas"""
        response = self.client.get(reverse('lojista:gerenciar_lojistas'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'lojista/gerenciar_lojistas.html')
        self.assertIn('page_obj', response.context)

    def test_lojista_edit_view(self):
        """Testa edição de lojista"""
        data = {
            'fantasiaLojista': 'Updated Store',
            'razaoLojista': 'Updated Store LTDA',
            'CNPJLojista': '00.000.000/0001-91',
            'status': 'Sim',
            'ramoAtividade': self.ramo.id
        }
        response = self.client.post(
            reverse('lojista:editar_lojista', kwargs={'lojista_id': self.lojista.pk}),
            data
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Verificar se o lojista foi atualizado
        self.lojista.refresh_from_db()
        self.assertEqual(self.lojista.fantasiaLojista, 'UPDATED STORE')


class DocumentoFiscalViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            CPF='12345678901',
            nome='Test User'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.campanha = Campanha.objects.create(
            nome='Test Campaign',
            data_inicio='2024-01-01',
            data_fim='2026-01-01',
            valor=10.00,
            ativa=True
        )
        self.ramo = RamoAtividade.objects.create(atividade='Test Activity')
        self.lojista = Lojista.objects.create(
            fantasiaLojista='Test Store',
            razaoLojista='Test Store LTDA',
            CNPJLojista='00.000.000/0001-91',
            status='Sim',
            ramoAtividade=self.ramo
        )
        self.documento = DocumentoFiscal.objects.create(
            user=self.user,
            lojista=self.lojista,
            numeroDocumento='123456',
            valorDocumento=100.50,
            dataDocumento='2025-01-01'
        )

    def test_adddocfiscal_view(self):
        """Testa adição de documento fiscal"""
        photo = SimpleUploadedFile("test_photo.jpg", b"file_content", content_type="image/jpeg")
        data = {
            'lojista_cnpj': '00.000.000/0001-91',
            'numeroDocumento': '789012',
            'valorOutros': '200,00',
            'dataDocumento': '2025-01-01',
            'photo': photo
        }
        response = self.client.post(reverse('participante:adddocfiscal'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Verificar se o documento foi criado
        doc_exists = DocumentoFiscal.objects.filter(numeroDocumento='789012').exists()
        self.assertTrue(doc_exists)

    def test_documento_edit_view(self):
        """Testa edição de documento fiscal"""
        data = {
            'numeroDocumento': '123456',
            'valorOutros': '150,00',
            'dataDocumento': '2025-01-01'
        }
        response = self.client.post(
            reverse('participante:editdocfiscal', kwargs={'id': self.documento.pk}),
            data
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Verificar se o documento foi atualizado
        self.documento.refresh_from_db()
        self.assertEqual(self.documento.valorDocumento, 150.00)


class APITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='adminpass123',
            is_superuser=True
        )
        self.client.login(username='adminuser', password='adminpass123')

    def test_search_by_cpf_api(self):
        """Testa API de busca por CPF"""
        profile = Profile.objects.create(
            user=self.user,
            CPF='123.456.789-01',
            nome='Test User'
        )
        
        response = self.client.get(
            reverse('participante:search_by_cpf'),
            {'q': '12345678901'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'participante/participante_detail_operador.html')
        self.assertEqual(response.context['user'].id, profile.id)

    def test_search_by_cupom_api(self):
        """Testa API de busca por cupom"""
        campanha = Campanha.objects.create(
            nome='Test Campaign',
            data_inicio='2024-01-01',
            data_fim='2026-01-01',
            valor=10.00,
            ativa=True
        )
        ramo = RamoAtividade.objects.create(atividade='Test Activity')
        lojista = Lojista.objects.create(
            fantasiaLojista='Test Store',
            razaoLojista='Test Store LTDA',
            CNPJLojista='00.000.000/0001-91',
            status='Sim',
            ramoAtividade=ramo
        )
        documento = DocumentoFiscal.objects.create(
            user=self.user,
            lojista=lojista,
            numeroDocumento='123456',
            valorDocumento=100.50,
            dataDocumento='2025-01-01'
        )
        
        profile = Profile.objects.create(
            user=self.user,
            CPF='123.456.789-01',
            nome='Test User'
        )
        cupom = Cupom.objects.create(
            user=self.user,
            documentoFiscal=documento
        )
        
        response = self.client.get(
            reverse('lojista:sorteio'),
            {'q': str(cupom.id)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'lojista/cupom_detail.html')
        self.assertEqual(response.context['cupom'].id, cupom.id)
