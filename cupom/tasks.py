from celery import shared_task
from django.contrib.auth.models import User
from django.db import transaction

from cupom.models import Cupom
from participante.models import DocumentoFiscal


@shared_task
def gerar_cupons_async(doc_id, operador_id):

    try:
        doc = DocumentoFiscal.objects.get(id=doc_id)
        qtde = int(doc.get_cupons())
        operador = User.objects.get(id=operador_id)
        print("Estou execultado minha task")

        # Cria uma lista de objetos Cupom a serem criados
        cupons = [
            Cupom(
                documentoFiscal=doc,
                user=doc.user,
                operador=operador,
                posto_trabalho=operador.profile.posto_trabalho,
            )
            for _ in range(qtde)
        ]

        # Utiliza bulk_create para criar todos os cupons de uma vez
        with transaction.atomic():
            Cupom.objects.bulk_create(cupons)

    except DocumentoFiscal.DoesNotExist:
        pass
    except User.DoesNotExist:
        pass
