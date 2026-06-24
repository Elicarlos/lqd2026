from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from participante.models import (
    Profile, CardDinamico, ConfiguracaoSecao, Funcionalidade,
    SystemRole, UserRole, DocumentoFiscal, PostoTrabalho, 
    TipoJornada, ConfiguracaoJornada, Campanha
)
from cupom.models import Cupom
from lojista.models import Lojista
import datetime
from datetime import time


class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            CPF='12345678901',
            nome='Test User',
            sexo='M',
            foneCelular1='1234567890',
            endereco='Test Address',
            bairro='Test Bairro',
            cidade='Test City',
            estado='PI'
        )

    def test_profile_creation(self):
        """Testa se o perfil é criado corretamente"""
        self.assertEqual(self.profile.user.username, 'testuser')
        self.assertEqual(self.profile.CPF, '12345678901')
        self.assertEqual(self.profile.nome, 'Test User')

    def test_profile_str_representation(self):
        """Testa a representação string do perfil"""
        # O __str__ do Profile retorna 'Nome completo {username}'
        expected = f"Nome completo {self.profile.user.username}"
        self.assertEqual(str(self.profile), expected)

    def test_profile_is_colaborador_property(self):
        """Testa a propriedade is_colaborador"""
        self.assertFalse(self.profile.is_colaborador)
        
        # Definir is_colaborador como True
        self.profile.is_colaborador = True
        self.profile.save()
        
        # Recarregar o perfil do banco
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.is_colaborador)


class CardDinamicoModelTest(TestCase):
    def setUp(self):
        self.card = CardDinamico.objects.create(
            nome='Test Card',
            titulo='Test Card Title',
            descricao='Test Description',
            url='http://example.com',
            tipo='PARTICIPANTE',
            icone='fas fa-users',
            ativo=True,
            ordem=1
        )

    def test_card_creation(self):
        """Testa se o card é criado corretamente"""
        self.assertEqual(self.card.nome, 'Test Card')
        self.assertEqual(self.card.tipo, 'PARTICIPANTE')
        self.assertTrue(self.card.ativo)

    def test_card_str_representation(self):
        """Testa a representação string do card"""
        # O __str__ do CardDinamico retorna self.nome
        expected = self.card.nome
        self.assertEqual(str(self.card), expected)

    def test_card_tipo_choices(self):
        """Testa se os tipos de card são válidos"""
        valid_types = ['PARTICIPANTE', 'LOJISTA', 'RECURSOS_HUMANOS', 
                      'BACKOFFICE', 'RELATORIO', 'CONFIGURACAO', 'OPERACOES']
        
        for tipo in valid_types:
            card = CardDinamico.objects.create(
                nome=f'Card {tipo}',
                titulo=f'Card {tipo} Title',
                tipo=tipo,
                icone='fas fa-users',
                ativo=True
            )
            self.assertEqual(card.tipo, tipo)

    def test_card_ordem_default(self):
        """Testa se a ordem padrão é aplicada corretamente"""
        card2 = CardDinamico.objects.create(
            nome='Test Card 2',
            titulo='Test Card 2 Title',
            tipo='LOJISTA',
            icone='fas fa-store',
            ativo=True
        )
        self.assertIsNotNone(card2.ordem)


class ConfiguracaoSecaoModelTest(TestCase):
    def setUp(self):
        self.secao = ConfiguracaoSecao.objects.create(
            tipo='PARTICIPANTE',
            titulo='Participantes',
            icone='fas fa-users',
            cor='#007bff',
            ativo=True
        )

    def test_secao_creation(self):
        """Testa se a seção é criada corretamente"""
        self.assertEqual(self.secao.tipo, 'PARTICIPANTE')
        self.assertEqual(self.secao.titulo, 'Participantes')
        self.assertTrue(self.secao.ativo)

    def test_secao_str_representation(self):
        """Testa a representação string da seção"""
        expected = f"{self.secao.get_tipo_display()} - {self.secao.titulo}"
        self.assertEqual(str(self.secao), expected)

    def test_secao_tipo_choices(self):
        """Testa se os tipos de seção são válidos"""
        self.secao.delete()  # Deletar para evitar colisão UNIQUE no tipo
        valid_types = ['PARTICIPANTE', 'LOJISTA', 'RECURSOS_HUMANOS', 
                      'BACKOFFICE', 'RELATORIO', 'CONFIGURACAO', 'OPERACOES']
        
        for tipo in valid_types:
            secao = ConfiguracaoSecao.objects.create(
                tipo=tipo,
                titulo=f'Seção {tipo}',
                icone='fas fa-icon',
                ativo=True
            )
            self.assertEqual(secao.tipo, tipo)

    def test_get_config_class_method(self):
        """Testa o método de classe get_config"""
        config = ConfiguracaoSecao.get_config('PARTICIPANTE')
        self.assertEqual(config, self.secao)

    def test_get_config_nonexistent(self):
        """Testa get_config para tipo inexistente"""
        config = ConfiguracaoSecao.get_config('NONEXISTENT')
        self.assertIsNotNone(config)  # Retorna configuração padrão


class FuncionalidadeModelTest(TestCase):
    def setUp(self):
        self.funcionalidade = Funcionalidade.objects.create(
            nome='Test Function',
            codigo='test_function',
            descricao='Test Description',
            tipo='VIEW',
            ativo=True
        )

    def test_funcionalidade_creation(self):
        """Testa se a funcionalidade é criada corretamente"""
        self.assertEqual(self.funcionalidade.nome, 'Test Function')
        self.assertEqual(self.funcionalidade.codigo, 'test_function')
        self.assertTrue(self.funcionalidade.ativo)

    def test_funcionalidade_str_representation(self):
        """Testa a representação string da funcionalidade"""
        expected = f"{self.funcionalidade.nome} ({self.funcionalidade.get_tipo_display()})"
        self.assertEqual(str(self.funcionalidade), expected)

    def test_codigo_unique_constraint(self):
        """Testa se o codigo deve ser único"""
        with self.assertRaises(IntegrityError):
            Funcionalidade.objects.create(
                nome='Another Function',
                codigo='test_function',  # Mesmo codigo
                descricao='Another Description',
                tipo='CREATE',
                ativo=True
            )


class SystemRoleModelTest(TestCase):
    def setUp(self):
        self.role = SystemRole.objects.create(
            name='Test Role',
            description='Test Role Description'
        )

    def test_role_creation(self):
        """Testa se o role é criado corretamente"""
        self.assertEqual(self.role.name, 'Test Role')
        self.assertEqual(self.role.description, 'Test Role Description')

    def test_role_str_representation(self):
        """Testa a representação string do role"""
        self.assertEqual(str(self.role), self.role.name)


class LojistaModelTest(TestCase):
    def setUp(self):
        self.lojista = Lojista.objects.create(
            fantasiaLojista='Test Store',
            razaoLojista='Test Store LTDA',
            CNPJLojista='12345678901234',
            status='Sim'
        )

    def test_lojista_creation(self):
        """Testa se o lojista é criado corretamente"""
        # O método clean() converte para maiúsculas
        self.assertEqual(self.lojista.fantasiaLojista, 'TEST STORE')
        self.assertEqual(self.lojista.CNPJLojista, '12.345.678/9012-34')
        self.assertEqual(self.lojista.status, 'Sim')

    def test_lojista_str_representation(self):
        """Testa a representação string do lojista"""
        # O __str__ retorna apenas fantasiaLojista
        expected = self.lojista.fantasiaLojista
        self.assertEqual(str(self.lojista), expected)

    def test_cnpj_unique_constraint(self):
        """Testa se o CNPJ deve ser único"""
        with self.assertRaises(IntegrityError):
            Lojista.objects.create(
                fantasiaLojista='Another Store',
                razaoLojista='Another Store LTDA',
                CNPJLojista='12345678901234',  # Mesmo CNPJ
                status='Sim'
            )


class PostoTrabalhoModelTest(TestCase):
    def setUp(self):
        self.posto = PostoTrabalho.objects.create(
            nome='Test Post',
            descricao='Test Post Description'
        )

    def test_posto_creation(self):
        """Testa se o posto é criado corretamente"""
        self.assertEqual(self.posto.nome, 'Test Post')
        self.assertEqual(self.posto.descricao, 'Test Post Description')

    def test_posto_str_representation(self):
        """Testa a representação string do posto"""
        self.assertEqual(str(self.posto), self.posto.nome)


class TipoJornadaModelTest(TestCase):
    def setUp(self):
        self.jornada = TipoJornada.objects.create(
            nome='Test Journey',
            hora_inicio=time(8, 0),  # 08:00
            hora_fim=time(18, 0),    # 18:00
            dias_semana=[1, 2, 3, 4, 5]  # Segunda a Sexta
        )

    def test_jornada_creation(self):
        """Testa se a jornada é criada corretamente"""
        self.assertEqual(self.jornada.nome, 'Test Journey')
        self.assertEqual(self.jornada.hora_inicio, time(8, 0))
        self.assertEqual(self.jornada.hora_fim, time(18, 0))
        self.assertEqual(self.jornada.dias_semana, [1, 2, 3, 4, 5])

    def test_jornada_str_representation(self):
        """Testa a representação string da jornada"""
        expected = f"{self.jornada.nome} ({self.jornada.hora_inicio.strftime('%H:%M')} - {self.jornada.hora_fim.strftime('%H:%M')})"
        self.assertEqual(str(self.jornada), expected)


class DocumentoFiscalModelTest(TestCase):
    def setUp(self):
        self.campanha = Campanha.objects.create(
            nome='Test Campaign',
            data_inicio='2024-01-01',
            data_fim='2026-01-01',
            valor=10.00,
            ativa=True
        )
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
        self.lojista = Lojista.objects.create(
            fantasiaLojista='Test Store',
            CNPJLojista='12.345.678/9012-34'
        )
        self.documento = DocumentoFiscal.objects.create(
            user=self.user,
            lojista=self.lojista,
            numeroDocumento='123456',
            dataDocumento=datetime.date(2025, 1, 1),
            valorDocumento=100.50
        )

    def test_documento_creation(self):
        """Testa se o documento é criado corretamente"""
        self.assertEqual(self.documento.numeroDocumento, '123456')
        self.assertEqual(self.documento.valorDocumento, 100.50)
        self.assertEqual(self.documento.user, self.user)

    def test_documento_str_representation(self):
        """Testa a representação string do documento"""
        # Verificar se o __str__ existe e funciona
        str_repr = str(self.documento)
        self.assertIsInstance(str_repr, str)


class CupomModelTest(TestCase):
    def setUp(self):
        self.campanha = Campanha.objects.create(
            nome='Test Campaign',
            data_inicio='2024-01-01',
            data_fim='2026-01-01',
            valor=10.00,
            ativa=True
        )
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
        self.lojista = Lojista.objects.create(
            fantasiaLojista='Test Store',
            CNPJLojista='12.345.678/9012-34'
        )
        self.documento = DocumentoFiscal.objects.create(
            user=self.user,
            lojista=self.lojista,
            numeroDocumento='123456',
            dataDocumento=datetime.date(2025, 1, 1),
            valorDocumento=100.50
        )
        self.cupom = Cupom.objects.create(
            user=self.user,
            documentoFiscal=self.documento
        )

    def test_cupom_creation(self):
        """Testa se o cupom é criado corretamente"""
        self.assertEqual(self.cupom.user, self.user)
        self.assertEqual(self.cupom.documentoFiscal, self.documento)
        self.assertFalse(self.cupom.impresso)

    def test_cupom_str_representation(self):
        """Testa a representação string do cupom"""
        expected = f"Cupom número: {self.cupom.id}"
        self.assertEqual(str(self.cupom), expected)
