# lojista/tests/test_models.py

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from lojista.models import Lojista, RamoAtividade, Localizacao


class LojistaModelTest(TestCase):
    def setUp(self):
        """Configuração inicial para os testes"""
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        
        self.ramo_atividade = RamoAtividade.objects.create(
            atividade='TESTE',
            cadastrado_por=self.user
        )
        
        self.localizacao = Localizacao.objects.create(
            nome='TESTE',
            descricao='Localização de teste',
            cadastrado_por=self.user
        )

    def test_cnpj_formatacao_automatica(self):
        """Testa se o CNPJ é formatado automaticamente ao salvar"""
        # CNPJ sem máscara
        cnpj_sem_mascara = "12345678000195"
        
        print(f"\n[INFO] Teste: Formatação automática")
        print(f"   Entrada:  '{cnpj_sem_mascara}'")
        
        lojista = Lojista.objects.create(
            CNPJLojista=cnpj_sem_mascara,
            razaoLojista="EMPRESA TESTE LTDA",
            fantasiaLojista="EMPRESA TESTE",
            ramoAtividade=self.ramo_atividade,
            cadastrado_por=self.user
        )
        
        print(f"   Saída:    '{lojista.CNPJLojista}'")
        print(f"   Esperado: '12.345.678/0001-95'")
        
        # Verifica se foi formatado corretamente
        self.assertEqual(lojista.CNPJLojista, "12.345.678/0001-95")
        print(f"   OK - PASSOU")

    def test_cnpj_com_mascara_ja_formatado(self):
        """Testa se CNPJ já formatado permanece no formato correto"""
        # CNPJ já com máscara
        cnpj_com_mascara = "12.345.678/0001-95"
        
        lojista = Lojista.objects.create(
            CNPJLojista=cnpj_com_mascara,
            razaoLojista="EMPRESA TESTE LTDA",
            fantasiaLojista="EMPRESA TESTE",
            ramoAtividade=self.ramo_atividade,
            cadastrado_por=self.user
        )
        
        # Verifica se permaneceu formatado
        self.assertEqual(lojista.CNPJLojista, "12.345.678/0001-95")

    def test_cnpj_com_espacos_e_caracteres_especiais(self):
        """Testa se CNPJ com espaços e caracteres especiais é limpo e formatado"""
        # CNPJ com espaços e caracteres especiais
        cnpj_sujo = " 12.345.678/0001-95 "
        
        print(f"\n[INFO] Teste: Limpeza de espaços")
        print(f"   Entrada:  '{cnpj_sujo}'")
        
        lojista = Lojista.objects.create(
            CNPJLojista=cnpj_sujo,
            razaoLojista="EMPRESA TESTE LTDA",
            fantasiaLojista="EMPRESA TESTE",
            ramoAtividade=self.ramo_atividade,
            cadastrado_por=self.user
        )
        
        print(f"   Saída:    '{lojista.CNPJLojista}'")
        print(f"   Esperado: '12.345.678/0001-95'")
        
        # Verifica se foi limpo e formatado
        self.assertEqual(lojista.CNPJLojista, "12.345.678/0001-95")
        print(f"   OK - PASSOU")

    def test_cnpj_invalido_menos_digitos(self):
        """Testa se CNPJ com menos de 14 dígitos gera erro"""
        # CNPJ com apenas 13 dígitos
        cnpj_invalido = "1234567800019"
        
        with self.assertRaises(ValidationError):
            lojista = Lojista(
                CNPJLojista=cnpj_invalido,
                razaoLojista="EMPRESA TESTE LTDA",
                fantasiaLojista="EMPRESA TESTE",
                ramoAtividade=self.ramo_atividade,
                cadastrado_por=self.user
            )
            lojista.full_clean()  # Chama o método clean()

    def test_cnpj_invalido_mais_digitos(self):
        """Testa se CNPJ com mais de 14 dígitos gera erro"""
        # CNPJ com 15 dígitos
        cnpj_invalido = "123456780001951"
        
        with self.assertRaises(ValidationError):
            lojista = Lojista(
                CNPJLojista=cnpj_invalido,
                razaoLojista="EMPRESA TESTE LTDA",
                fantasiaLojista="EMPRESA TESTE",
                ramoAtividade=self.ramo_atividade,
                cadastrado_por=self.user
            )
            lojista.full_clean()  # Chama o método clean()

    def test_cnpj_vazio_nao_gera_erro(self):
        """Testa se CNPJ vazio não gera erro (pois pode ser null=True)"""
        lojista = Lojista.objects.create(
            CNPJLojista="",  # CNPJ vazio
            razaoLojista="EMPRESA TESTE LTDA",
            fantasiaLojista="EMPRESA TESTE",
            ramoAtividade=self.ramo_atividade,
            cadastrado_por=self.user
        )
        
        # Verifica se foi salvo sem erro
        self.assertIsNotNone(lojista.id)

    def test_cnpj_none_nao_gera_erro(self):
        """Testa se CNPJ None não gera erro (pois pode ser null=True)"""
        lojista = Lojista.objects.create(
            CNPJLojista=None,  # CNPJ None
            razaoLojista="EMPRESA TESTE LTDA",
            fantasiaLojista="EMPRESA TESTE",
            ramoAtividade=self.ramo_atividade,
            cadastrado_por=self.user
        )
        
        # Verifica se foi salvo sem erro
        self.assertIsNotNone(lojista.id)

    def test_cnpj_diferentes_formatos(self):
        """Testa diferentes formatos de entrada de CNPJ"""
        formatos_teste = [
            ("12345678000195", "12.345.678/0001-95"),      # Sem máscara
            ("98765432000187", "98.765.432/0001-87"),      # Com máscara
            ("11111111000111", "11.111.111/0001-11"),      # Com pontos
            ("22222222000222", "22.222.222/0002-22"),      # Sem pontos
            (" 33333333000333 ", "33.333.333/0003-33"),    # Com espaços
        ]
        
        print("\n" + "="*60)
        print("TESTE DE FORMATAÇÃO DE CNPJ")
        print("="*60)
        
        for i, (formato_entrada, formato_esperado) in enumerate(formatos_teste):
            print(f"\n[INFO] Teste {i+1}:")
            print(f"   Entrada:  '{formato_entrada}'")
            
            lojista = Lojista.objects.create(
                CNPJLojista=formato_entrada,
                razaoLojista=f"EMPRESA TESTE {i} LTDA",
                fantasiaLojista=f"EMPRESA TESTE {i}",
                ramoAtividade=self.ramo_atividade,
                cadastrado_por=self.user
            )
            
            print(f"   Saída:    '{lojista.CNPJLojista}'")
            print(f"   Esperado: '{formato_esperado}'")
            
            # Verifica se foi formatado corretamente
            self.assertEqual(lojista.CNPJLojista, formato_esperado)
            
            if lojista.CNPJLojista == formato_esperado:
                print(f"   OK - PASSOU")
            else:
                print(f"   FAIL - FALHOU")
        
        print("\n" + "="*60)
        print("FIM DO TESTE")
        print("="*60)

    def test_campos_texto_convertidos_para_maiusculo(self):
        """Testa se campos de texto são convertidos para maiúsculo"""
        lojista = Lojista.objects.create(
            CNPJLojista="12345678000195",
            razaoLojista="empresa teste ltda",
            fantasiaLojista="empresa teste",
            endereco="rua teste, 123",
            ramoAtividade=self.ramo_atividade,
            cadastrado_por=self.user
        )
        
        # Verifica se foram convertidos para maiúsculo
        self.assertEqual(lojista.razaoLojista, "EMPRESA TESTE LTDA")
        self.assertEqual(lojista.fantasiaLojista, "EMPRESA TESTE")
        self.assertEqual(lojista.endereco, "RUA TESTE, 123")

    def test_telefone_e_ie_limpos(self):
        """Testa se telefone e IE são limpos (removem espaços)"""
        lojista = Lojista.objects.create(
            CNPJLojista="12345678000195",
            razaoLojista="EMPRESA TESTE LTDA",
            fantasiaLojista="EMPRESA TESTE",
            telefone=" (85) 3212-0000 ",
            IELojista=" 123456789 ",
            ramoAtividade=self.ramo_atividade,
            cadastrado_por=self.user
        )
        
        # Verifica se foram limpos
        self.assertEqual(lojista.telefone, "(85) 3212-0000")
        self.assertEqual(lojista.IELojista, "123456789")