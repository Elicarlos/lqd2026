"""
Função para adicionar documentos fiscais ao CPF 017.614.323-89 no lojista 92.753.095/0001-32

Uso no shell do Django:
python manage.py shell
from utils.add_documents import add_documents_to_cpf
add_documents_to_cpf(quantidade=5, valor_min=50, valor_max=200)
"""

import os
import sys
import django
import random
from decimal import Decimal
from datetime import date, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'liquida2018.settings')
django.setup()

from django.contrib.auth import get_user_model
from participante.models import DocumentoFiscal, Campanha
from lojista.models import Lojista
from cupom.models import Cupom

User = get_user_model()


def add_documents_to_cpf(quantidade=5, valor_min=50.0, valor_max=200.0, 
                        data_inicio='2024-06-28', data_fim='2024-07-07'):
    """
    Adiciona documentos fiscais ao CPF 017.614.323-89 no lojista 92.753.095/0001-32
    
    Args:
        quantidade (int): Quantidade de documentos a serem criados
        valor_min (float): Valor mínimo dos documentos
        valor_max (float): Valor máximo dos documentos
        data_inicio (str): Data de início no formato YYYY-MM-DD
        data_fim (str): Data de fim no formato YYYY-MM-DD
    
    Returns:
        list: Lista dos documentos criados
    """
    
    # CPF e CNPJ fixos
    cpf = '01761432389'
    cnpj = '92753095000132'
    
    print(f"🚀 Iniciando criação de {quantidade} documentos...")
    
    try:
        # Buscar usuário pelo CPF
        try:
            user = User.objects.get(username=cpf)
            print(f"✅ Usuário encontrado: {user.username}")
        except User.DoesNotExist:
            print(f"❌ Usuário com CPF {cpf} não encontrado!")
            return []
        
        # Buscar lojista pelo CNPJ
        try:
            lojista = Lojista.objects.get(CNPJLojista=cnpj)
            print(f"✅ Lojista encontrado: {lojista.fantasiaLojista} ({lojista.CNPJLojista})")
        except Lojista.DoesNotExist:
            print(f"❌ Lojista com CNPJ {cnpj} não encontrado!")
            return []
        
        # Verificar se há campanha ativa
        try:
            campanha = Campanha.objects.get(ativa=True)
            print(f"✅ Campanha ativa: {campanha.nome}")
        except Campanha.DoesNotExist:
            print("❌ Nenhuma campanha ativa encontrada!")
            return []
        
        # Converter datas
        data_inicio = date.fromisoformat(data_inicio)
        data_fim = date.fromisoformat(data_fim)
        
        # Gerar documentos
        documentos_criados = []
        
        for i in range(quantidade):
            # Gerar valor aleatório
            valor = Decimal(str(random.uniform(float(valor_min), float(valor_max))))
            valor = valor.quantize(Decimal('0.01'))  # Arredondar para 2 casas decimais
            
            # Gerar data aleatória dentro do período
            dias_aleatorios = random.randint(0, (data_fim - data_inicio).days)
            data_documento = data_inicio + timedelta(days=dias_aleatorios)
            
            # Gerar número de documento único
            numero_documento = f"DOC{user.id:03d}{i+1:03d}{random.randint(1000, 9999)}"
            
            # Verificar se o número já existe
            while DocumentoFiscal.objects.filter(numeroDocumento=numero_documento, lojista=lojista).exists():
                numero_documento = f"DOC{user.id:03d}{i+1:03d}{random.randint(1000, 9999)}"
            
            # Criar documento fiscal
            documento = DocumentoFiscal.objects.create(
                user=user,
                lojista=lojista,
                vendedor=f"Vendedor {i+1}",
                numeroDocumento=numero_documento,
                dataDocumento=data_documento,
                valorDocumento=valor,
                compradoREDE=random.choice([True, False]),
                compradoMASTERCARD=random.choice([True, False]),
                compradoCielo=random.choice([True, False]),
                valorCielo=valor if random.choice([True, False]) else Decimal('0.00'),
                valorOutros=Decimal('0.00'),
                status='pendente',
                observacao=f"Documento criado automaticamente - Teste {i+1}",
                cadastrado_por=user
            )
            
            documentos_criados.append(documento)
            
            print(f"✅ Documento {i+1}/{quantidade} criado: R$ {valor:.2f} - {numero_documento} - {data_documento.strftime('%d/%m/%Y')}")
        
        # Resumo final
        total_valor = sum(doc.valorDocumento for doc in documentos_criados)
        print("\n" + "="*60)
        print("📊 RESUMO DA CRIAÇÃO:")
        print(f"👤 Usuário: {user.username}")
        print(f"🏪 Lojista: {lojista.fantasiaLojista}")
        print(f"📄 Documentos criados: {len(documentos_criados)}")
        print(f"💰 Valor total: R$ {total_valor:.2f}")
        print(f"📅 Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
        print("="*60)
        
        # Criar cupons para cada documento (1 cupom por documento)
        cupons_criados = []
        for documento in documentos_criados:
            cupom = Cupom.objects.create(
                user=user,
                documentoFiscal=documento,
                operador=user,  # Usuário que criou o documento
                impresso=False,
                em_impressao=False
            )
            cupons_criados.append(cupom)
            print(f"🎫 Cupom {cupom.id} criado para documento {documento.id}")
        
        print(f"🎫 Total de cupons criados: {len(cupons_criados)} (1 por documento)")
        
        print(f"\n🎉 Sucesso! {quantidade} documentos e {len(cupons_criados)} cupons criados para o CPF {cpf}")
        
        return documentos_criados
        
    except Exception as e:
        print(f"❌ Erro ao criar documentos: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def list_user_documents(cpf='01761432389'):
    """
    Lista todos os documentos de um usuário
    
    Args:
        cpf (str): CPF do usuário (sem formatação)
    
    Returns:
        QuerySet: Documentos do usuário
    """
    try:
        user = User.objects.get(username=cpf)
        documentos = DocumentoFiscal.objects.filter(user=user).order_by('-dataCadastro')
        
        print(f"📄 Documentos do usuário {cpf}:")
        print("="*80)
        
        for doc in documentos:
            status_emoji = "✅" if doc.status == 'validado' else "⏳" if doc.status == 'pendente' else "❌"
            print(f"{status_emoji} ID: {doc.id} | R$ {doc.valorDocumento:.2f} | {doc.numeroDocumento} | {doc.dataDocumento.strftime('%d/%m/%Y')} | {doc.lojista.fantasiaLojista}")
        
        total_valor = sum(doc.valorDocumento for doc in documentos)
        print("="*80)
        print(f"💰 Total: {documentos.count()} documentos | R$ {total_valor:.2f}")
        
        return documentos
        
    except User.DoesNotExist:
        print(f"❌ Usuário com CPF {cpf} não encontrado!")
        return []


if __name__ == "__main__":
    # Se executado diretamente, criar 5 documentos
    add_documents_to_cpf(quantidade=5, valor_min=50, valor_max=200)
