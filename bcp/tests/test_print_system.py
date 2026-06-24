"""
Testes para o Sistema de Impressão de Cupons - BCP

Testa a função print_barcode_get e todo o fluxo de impressão
"""

import json
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.utils import timezone
import datetime
from django.conf import settings

from participante.models import DocumentoFiscal, Profile, Campanha
from cupom.models import Cupom
from lojista.models import Lojista
from bcp.views import print_barcode_get, confirm_print, serve_pdf_from_task
from bcp.tasks import generate_pdf_task


class PrintSystemTestCase(TestCase):
    """Testes para o sistema de impressão de cupons"""
    
    def setUp(self):
        """Configuração inicial para todos os testes"""
        # Criar Campanha ativa
        self.campanha = Campanha.objects.create(
            nome='Campanha Teste',
            data_inicio=timezone.now().date() - datetime.timedelta(days=10),
            data_fim=timezone.now().date() + datetime.timedelta(days=10),
            valor=Decimal('50.00'),
            ativa=True
        )

        # Criar usuário staff
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.user.is_staff = True
        self.user.save()
        
        # Criar perfil do usuário
        self.profile = Profile.objects.create(
            user=self.user,
            CPF='123.456.789-00',
            nome='Usuário Teste'
        )
        
        # Criar lojista
        self.lojista = Lojista.objects.create(
            CNPJLojista='12.345.678/0001-90',
            fantasiaLojista='Loja Teste',
            status='Sim'
        )
        
        # Criar documento fiscal
        self.documento = DocumentoFiscal.objects.create(
            user=self.user,
            lojista=self.lojista,
            numeroDocumento='123456789',
            dataDocumento=timezone.now().date(),
            valorDocumento=Decimal('100.00'),
            valorCielo=Decimal('50.00'),
            valorOutros=Decimal('50.00'),
            status='validado',
            compradoCielo=True
        )
        
        # Criar cupons
        self.cupons = []
        for i in range(3):
            cupom = Cupom.objects.create(
                documentoFiscal=self.documento,
                user=self.user,
                operador=self.user,
                impresso=False,
                em_impressao=False
            )
            self.cupons.append(cupom)
        
        # Cliente para testes
        self.client = Client()
        
    def test_print_barcode_get_access_denied(self):
        """Testa acesso negado para usuários não autenticados"""
        url = reverse('bcp:print_get', kwargs={'id_': self.documento.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirecionamento para login
        
    def test_print_barcode_get_non_staff_access_denied(self):
        """Testa acesso negado para usuários não-staff"""
        # Criar usuário não-staff
        non_staff_user = User.objects.create_user(
            username='nonstaff',
            password='testpass123'
        )
        self.client.login(username='nonstaff', password='testpass123')
        
        url = reverse('bcp:print_get', kwargs={'id_': self.documento.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirecionamento
        
    def test_print_barcode_get_document_not_found(self):
        """Testa erro quando documento não existe"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('bcp:print_get', kwargs={'id_': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        
    def test_print_barcode_get_success_sync(self):
        """Testa impressão síncrona bem-sucedida"""
        self.client.login(username='testuser', password='testpass123')
        
        # Mock settings para usar modo síncrono
        with patch('bcp.views.settings.USE_CELERY_FOR_PDF', False):
            url = reverse('bcp:print_get', kwargs={'id_': self.documento.id})
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'bcp/print_pdf.html')
            self.assertIn('pdf_url', response.context)
            self.assertIn('doc', response.context)
            self.assertEqual(response.context['doc'], self.documento)
            
            # Verificar headers
            self.assertIn('X-Frame-Options', response)
            self.assertEqual(response['X-Frame-Options'], 'SAMEORIGIN')
            
    @override_settings(USE_CELERY_FOR_PDF=True, PDF_SYNC_THRESHOLD=0)
    def test_print_barcode_get_success_celery(self):
        """Testa impressão com Celery bem-sucedida"""
        self.client.login(username='testuser', password='testpass123')
        
        # Mock task do Celery
        mock_task = MagicMock()
        mock_task.id = 'test-task-id-123'
        
        with patch('bcp.views.generate_pdf_task.delay', return_value=mock_task):
            url = reverse('bcp:print_get', kwargs={'id_': self.documento.id})
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'bcp/print_pdf.html')
            self.assertIn('pdf_url', response.context)
            
            # Verificar se a URL contém o task_id
            pdf_url = response.context['pdf_url']
            self.assertIn('serve_pdf_from_task', pdf_url)
            self.assertIn('test-task-id-123', pdf_url)
            
    def test_confirm_print_success(self):
        """Testa confirmação de impressão bem-sucedida"""
        self.client.login(username='testuser', password='testpass123')
        
        # Marcar cupons como em impressão
        for cupom in self.cupons:
            cupom.em_impressao = True
            cupom.save()
        
        url = reverse('bcp:confirm_print', kwargs={'id_': self.documento.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('marcados como impressos', data['message'])
        
        # Verificar se cupons foram marcados
        for cupom in Cupom.objects.filter(documentoFiscal=self.documento):
            self.assertTrue(cupom.impresso)
            self.assertFalse(cupom.em_impressao)
            
    def test_confirm_print_no_cupons_in_printing(self):
        """Testa erro quando não há cupons em impressão"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('bcp:confirm_print', kwargs={'id_': self.documento.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 404)
        
    def test_serve_pdf_from_task_success(self):
        """Testa servir PDF de task Celery bem-sucedida"""
        self.client.login(username='testuser', password='testpass123')
        
        # Mock AsyncResult
        mock_result = MagicMock()
        mock_result.state = 'SUCCESS'
        mock_result.result = b'%PDF-1.4\n...\n' + b'x' * 1000  # PDF válido com tamanho adequado
        
        with patch('bcp.views.AsyncResult', return_value=mock_result):
            url = reverse('bcp:serve_pdf_from_task', kwargs={'task_id': 'test-task-id'})
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/pdf')
            self.assertIn('X-Frame-Options', response)
            self.assertEqual(response['X-Frame-Options'], 'SAMEORIGIN')
            
    def test_serve_pdf_from_task_pending(self):
        """Testa redirecionamento quando task ainda está pendente"""
        self.client.login(username='testuser', password='testpass123')
        
        # Mock AsyncResult
        mock_result = MagicMock()
        mock_result.state = 'PENDING'
        
        with patch('bcp.views.AsyncResult', return_value=mock_result):
            url = reverse('bcp:serve_pdf_from_task', kwargs={'task_id': 'test-task-id'})
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 302)  # Redirecionamento
            
    def test_serve_pdf_from_task_invalid_pdf(self):
        """Testa erro quando PDF é inválido"""
        self.client.login(username='testuser', password='testpass123')
        
        # Mock AsyncResult com PDF inválido
        mock_result = MagicMock()
        mock_result.state = 'SUCCESS'
        mock_result.result = b'invalid content'  # Não é PDF
        
        with patch('bcp.views.AsyncResult', return_value=mock_result):
            url = reverse('bcp:serve_pdf_from_task', kwargs={'task_id': 'test-task-id'})
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 400)
            data = json.loads(response.content)
            self.assertFalse(data['status'] == 'SUCCESS')
            
    def test_check_task_status_success(self):
        """Testa verificação de status de task bem-sucedida"""
        self.client.login(username='testuser', password='testpass123')
        
        # Mock AsyncResult
        mock_result = MagicMock()
        mock_result.state = 'SUCCESS'
        mock_result.ready.return_value = True
        
        with patch('bcp.views.AsyncResult', return_value=mock_result):
            url = reverse('bcp:check_task_status', kwargs={'task_id': 'test-task-id'})
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertEqual(data['status'], 'SUCCESS')
            self.assertIn('pdf_url', data)
            
    def test_check_task_status_pending(self):
        """Testa verificação de status quando task está pendente"""
        self.client.login(username='testuser', password='testpass123')
        
        # Mock AsyncResult
        mock_result = MagicMock()
        mock_result.state = 'PENDING'
        mock_result.ready.return_value = False
        
        with patch('bcp.views.AsyncResult', return_value=mock_result):
            url = reverse('bcp:check_task_status', kwargs={'task_id': 'test-task-id'})
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertEqual(data['status'], 'PENDING')
            
    def test_generate_pdf_sync_function(self):
        """Testa função de geração síncrona de PDF"""
        from bcp.views import generate_pdf_sync
        
        # Mock da função de geração de PDF
        with patch('bcp.views.generate_pdf_sync') as mock_generate:
            mock_generate.return_value = b'%PDF-1.4\n...'
            
            # Criar um mock request para simular a chamada da view
            mock_request = MagicMock()
            mock_request.user = self.user
            
            response = generate_pdf_sync(mock_request, self.documento.id)
            
            self.assertIsNotNone(response)
            self.assertEqual(response['Content-Type'], 'application/pdf')
            
    def test_print_barcode_get_with_invalid_document_status(self):
        """Testa impressão com documento não validado"""
        # Criar documento não validado
        invalid_doc = DocumentoFiscal.objects.create(
            user=self.user,
            lojista=self.lojista,
            numeroDocumento='999999999',
            dataDocumento=timezone.now().date(),
            valorDocumento=Decimal('50.00'),
            status='pendente'
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('bcp:print_get', kwargs={'id_': invalid_doc.id})
        response = self.client.get(url)
        
        # Deve funcionar mesmo com documento não validado (para testes)
        self.assertEqual(response.status_code, 200)
        
    def test_template_context_variables(self):
        """Testa se todas as variáveis necessárias estão no contexto"""
        self.client.login(username='testuser', password='testpass123')
        
        with patch('bcp.views.settings.USE_CELERY_FOR_PDF', False):
            url = reverse('bcp:print_get', kwargs={'id_': self.documento.id})
            response = self.client.get(url)
            
            context = response.context
            self.assertIn('pdf_url', context)
            self.assertIn('doc', context)
            self.assertEqual(context['doc'], self.documento)
            
            # Verificar se pdf_url é uma URL válida
            pdf_url = context['pdf_url']
            self.assertIsInstance(pdf_url, str)
            self.assertIn('generate', pdf_url)
            
    @override_settings(USE_CELERY_FOR_PDF=True, PDF_SYNC_THRESHOLD=0)
    def test_celery_task_integration(self):
        """Testa integração com tasks do Celery"""
        # Mock da task do Celery
        with patch('bcp.views.generate_pdf_task.delay') as mock_delay:
            mock_task = MagicMock()
            mock_task.id = 'celery-task-123'
            mock_delay.return_value = mock_task
            
            self.client.login(username='testuser', password='testpass123')
            url = reverse('bcp:print_get', kwargs={'id_': self.documento.id})
            response = self.client.get(url)
            
            # Verificar se a task foi chamada
            mock_delay.assert_called_once_with(self.documento.id, auto_print=False)
            
            # Verificar se a URL contém o task_id
            context = response.context
            pdf_url = context['pdf_url']
            self.assertIn('celery-task-123', pdf_url)
                
    def test_error_handling_in_confirm_print(self):
        """Testa tratamento de erros na confirmação de impressão"""
        self.client.login(username='testuser', password='testpass123')
        
        # Testar com documento inexistente
        url = reverse('bcp:confirm_print', kwargs={'id_': 99999})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 404)
        
    def test_multiple_cupons_handling(self):
        """Testa impressão com múltiplos cupons"""
        # Criar mais cupons
        for i in range(5):
            Cupom.objects.create(
                documentoFiscal=self.documento,
                user=self.user,
                operador=self.user,
                impresso=False,
                em_impressao=False
            )
        
        self.client.login(username='testuser', password='testpass123')
        
        # Marcar todos como em impressão
        Cupom.objects.filter(documentoFiscal=self.documento).update(em_impressao=True)
        
        # Testar confirmação
        url = reverse('bcp:confirm_print', kwargs={'id_': self.documento.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verificar se todos os cupons foram marcados
        cupons_impressos = Cupom.objects.filter(
            documentoFiscal=self.documento, 
            impresso=True
        ).count()
        self.assertEqual(cupons_impressos, 8)  # 3 originais + 5 novos


class PrintSystemIntegrationTestCase(TestCase):
    """Testes de integração para o sistema de impressão"""
    
    def setUp(self):
        """Configuração para testes de integração"""
        # Criar Campanha ativa
        self.campanha = Campanha.objects.create(
            nome='Campanha Teste Integração',
            data_inicio=timezone.now().date() - datetime.timedelta(days=10),
            data_fim=timezone.now().date() + datetime.timedelta(days=10),
            valor=Decimal('50.00'),
            ativa=True
        )

        # Configuração similar ao TestCase anterior
        self.user = User.objects.create_user(
            username='integration_user',
            password='testpass123',
            email='integration@example.com'
        )
        self.user.is_staff = True
        self.user.save()
        
        self.profile = Profile.objects.create(
            user=self.user,
            CPF='987.654.321-00',
            nome='Usuário Integração'
        )
        
        self.lojista = Lojista.objects.create(
            CNPJLojista='98.765.432/0001-10',
            fantasiaLojista='Loja Integração',
            status='Sim'
        )
        
        self.documento = DocumentoFiscal.objects.create(
            user=self.user,
            lojista=self.lojista,
            numeroDocumento='INT123456',
            dataDocumento=timezone.now().date(),
            valorDocumento=Decimal('200.00'),
            valorCielo=Decimal('100.00'),
            valorOutros=Decimal('100.00'),
            status='validado',
            compradoCielo=True
        )
        
        # Criar cupons para integração
        for i in range(4):
            Cupom.objects.create(
                documentoFiscal=self.documento,
                user=self.user,
                operador=self.user,
                impresso=False,
                em_impressao=False
            )
        
        self.client = Client()
        
    @override_settings(USE_CELERY_FOR_PDF=False)
    def test_full_print_workflow_sync(self):
        """Testa fluxo completo de impressão síncrona"""
        self.client.login(username='integration_user', password='testpass123')
        
        # 1. Acessar página de impressão
        url = reverse('bcp:print_get', kwargs={'id_': self.documento.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'bcp/print_pdf.html')
        
        # 2. Simular confirmação de impressão
        confirm_url = reverse('bcp:confirm_print', kwargs={'id_': self.documento.id})
        
        # Marcar cupons como em impressão
        Cupom.objects.filter(documentoFiscal=self.documento).update(em_impressao=True)
        
        confirm_response = self.client.post(confirm_url)
        self.assertEqual(confirm_response.status_code, 200)
        
        # 3. Verificar se cupons foram marcados
        cupons_impressos = Cupom.objects.filter(
            documentoFiscal=self.documento, 
            impresso=True
        ).count()
        self.assertEqual(cupons_impressos, 4)
            
    @override_settings(USE_CELERY_FOR_PDF=True)
    def test_full_print_workflow_celery(self):
        """Testa fluxo completo de impressão com Celery"""
        self.client.login(username='integration_user', password='testpass123')
        
        # Mock da task do Celery
        mock_task = MagicMock()
        mock_task.id = 'integration-task-456'
        
        with patch('bcp.views.generate_pdf_task.delay', return_value=mock_task):
            
            # 1. Acessar página de impressão
            url = reverse('bcp:print_get', kwargs={'id_': self.documento.id})
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            
            # 2. Verificar status da task
            status_url = reverse('bcp:check_task_status', kwargs={'task_id': 'integration-task-456'})
            
            # Mock AsyncResult para status
            mock_result = MagicMock()
            mock_result.state = 'SUCCESS'
            mock_result.ready.return_value = True
            
            with patch('bcp.views.AsyncResult', return_value=mock_result):
                status_response = self.client.get(status_url)
                self.assertEqual(status_response.status_code, 200)
                
                data = json.loads(status_response.content)
                self.assertEqual(data['status'], 'SUCCESS')
                
            # 3. Servir PDF da task
            pdf_url = reverse('bcp:serve_pdf_from_task', kwargs={'task_id': 'integration-task-456'})
            
            # Mock AsyncResult para PDF
            mock_pdf_result = MagicMock()
            mock_pdf_result.state = 'SUCCESS'
            mock_pdf_result.result = b'%PDF-1.4\n...\n' + b'x' * 1000  # PDF válido com tamanho adequado
            
            with patch('bcp.views.AsyncResult', return_value=mock_pdf_result):
                pdf_response = self.client.get(pdf_url)
                self.assertEqual(pdf_response.status_code, 200)
                self.assertEqual(pdf_response['Content-Type'], 'application/pdf')
                
    def test_error_recovery_workflow(self):
        """Testa recuperação de erros no fluxo de impressão"""
        self.client.login(username='integration_user', password='testpass123')
        
        # Testar com task que falha
        mock_task = MagicMock()
        mock_task.id = 'failed-task-789'
        
        with patch('bcp.views.settings.USE_CELERY_FOR_PDF', True), \
             patch('bcp.views.generate_pdf_task.delay', return_value=mock_task):
            
            # 1. Acessar página de impressão
            url = reverse('bcp:print_get', kwargs={'id_': self.documento.id})
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            
            # 2. Verificar status de task que falhou
            status_url = reverse('bcp:check_task_status', kwargs={'task_id': 'failed-task-789'})
            
            mock_result = MagicMock()
            mock_result.state = 'FAILURE'
            mock_result.ready.return_value = True
            
            with patch('bcp.views.AsyncResult', return_value=mock_result):
                status_response = self.client.get(status_url)
                self.assertEqual(status_response.status_code, 200)
                
                data = json.loads(status_response.content)
                self.assertEqual(data['status'], 'FAILURE')
                self.assertIn('error', data)


if __name__ == '__main__':
    # Para executar os testes individualmente
    import django
    django.setup()
    
    # Executar testes
    import unittest
    unittest.main()
