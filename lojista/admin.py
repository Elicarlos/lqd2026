import csv

from django import forms
from django.contrib import admin
from django.db import transaction
from django.http import HttpResponse
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from .models import AdesaoLojista, Localizacao, Lojista, RamoAtividade


class AdesaoLojistaResouce(resources.ModelResource):
    class Meta:
        model = AdesaoLojista


class AdesaoAdmin(ImportExportModelAdmin):
    list_display = [
        "cnpj",
        "razao_social",
        "fantasia",
        "email",
        "telefone",
        "data_contato",
    ]
    resource_class = AdesaoLojistaResouce


class LocalizacaoResource(resources.ModelResource):
    class Meta:
        model = Localizacao


class LocalizacaoAdmin(ImportExportModelAdmin):
    list_display = ["nome", "descricao"]
    resource_class = LocalizacaoResource


from import_export import resources, fields
from django.db import transaction, IntegrityError
from django.contrib.auth.models import User
from lojista.models import Lojista, RamoAtividade, Localizacao
import re

class LojistaResource(resources.ModelResource):
    # Lemos as colunas, mas não deixamos o lib setar no objeto temporário
    ramoAtividade = fields.Field(column_name="ramoAtividade", readonly=True)
    localizacao   = fields.Field(column_name="localizacao",   readonly=True)

    validos = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Inicializa os atributos que serão usados durante a importação
        self.validos = []
        self._cnpjs_vistos = set()

    class Meta:
        model = Lojista
        import_id_fields = ["CNPJLojista"]
        skip_unchanged = True
        report_skipped = True
        fields = (
            "ramoAtividade",
            "localizacao",
            "CNPJLojista",
            "IELojista",
            "razaoLojista",
            "fantasiaLojista",
            "endereco",
            "telefone",
            "status",
        )
        exclude = ("cadastrado_por", "autorizado_por", "dataCadastro", "lojista_cielo")

    # ---------- utils ----------
    @staticmethod
    def _digits_only(s: str) -> str:
        return re.sub(r"\D", "", s or "")

    @staticmethod
    def _format_cnpj(digits: str) -> str:
        """XX.XXX.XXX/XXXX-XX"""
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"

    # ---------- desligar atribuição automática ----------
    def import_obj(self, obj, data, dry_run, **kwargs):
        # Não deixamos o django-import-export setar atributos no obj temporário
        return

    def save_instance(self, instance, *args, **kwargs):
        """
        Override save_instance para evitar que o django-import-export salve automaticamente.
        Aceita todos os argumentos via *args e **kwargs para evitar conflito de argumentos duplicados.
        """
        # Não salva aqui, será salvo manualmente no after_import
        return instance

    def get_or_init_instance(self, instance_loader, row):
        # Sempre devolve uma instância vazia (nunca None)
        return self._meta.model(), True

    # ---------- pipeline ----------
    def before_import(self, dataset, **kwargs):
        """
        Inicializa os atributos antes da importação.
        Aceita kwargs para compatibilidade com diferentes versões do django-import-export.
        """
        # Garante que os atributos estejam inicializados
        if not hasattr(self, 'validos'):
            self.validos = []
        if not hasattr(self, '_cnpjs_vistos'):
            self._cnpjs_vistos = set()
        
        # Reseta para nova importação
        self.validos = []
        self._cnpjs_vistos = set()   # 👈 evita duplicados no próprio arquivo
        
        # Chama o método pai apenas com dataset e kwargs (sem argumentos posicionais extras)
        return super().before_import(dataset, **kwargs)

    def _safe_str(self, value):
        """Converte valor para string de forma segura, tratando None e tipos numéricos."""
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return str(value)
        return str(value) if value else ""
    
    def _safe_strip(self, value):
        """Aplica strip de forma segura, tratando None e tipos numéricos."""
        s = self._safe_str(value)
        return s.strip() if s else ""

    def before_import_row(self, row, **kwargs):
        # Garante que _cnpjs_vistos está inicializado
        if not hasattr(self, '_cnpjs_vistos'):
            self._cnpjs_vistos = set()
        if not hasattr(self, 'validos'):
            self.validos = []
        
        # pula linha vazia (trata valores numéricos corretamente)
        if all(v is None or self._safe_strip(v) == "" for v in row.values()):
            return

        # Função auxiliar para buscar valor case-insensitive
        def find_value(row_dict, search_keys):
            """Busca valor em row_dict usando múltiplas variações de chave (case-insensitive)"""
            # Lista de possíveis variações
            variations = []
            for key in search_keys:
                variations.extend([
                    key,
                    key.lower(),
                    key.upper(),
                    key.capitalize(),
                    key.replace("_", ""),
                    key.replace("-", ""),
                ])
            
            # Primeiro tenta busca direta
            for var in variations:
                if var in row_dict:
                    val = self._safe_strip(row_dict.get(var))
                    if val:
                        return val
            
            # Se não encontrou, busca case-insensitive em todas as chaves
            search_lower = [k.lower().replace("_", "").replace("-", "") for k in search_keys]
            for key in row_dict.keys():
                if key and key.lower().replace("_", "").replace("-", "") in search_lower:
                    val = self._safe_strip(row_dict.get(key))
                    if val:
                        return val
            
            return None
        
        # CNPJ: 14 dígitos + máscara (busca case-insensitive)
        raw_cnpj = find_value(row, ["CNPJLojista", "cnpjlojista", "cnpjLojista", "CNPJLOJISTA"])
        if not raw_cnpj:
            print("❌ CNPJ vazio - ignorado")
            return

        digits = self._digits_only(raw_cnpj)
        if len(digits) != 14:
            print(f"❌ CNPJ inválido ({digits}) - esperado 14 dígitos")
            return

        cnpj_masked = self._format_cnpj(digits)

        # dedupe dentro do arquivo
        if cnpj_masked in self._cnpjs_vistos:
            print(f"⚠️  CNPJ duplicado no arquivo: {cnpj_masked} - ignorando segunda ocorrência")
            return
        self._cnpjs_vistos.add(cnpj_masked)

        row["CNPJLojista"] = cnpj_masked

        # já existe no banco?
        if Lojista.objects.filter(CNPJLojista=cnpj_masked).exists():
            print(f"⚠️  Lojista {cnpj_masked} já existe no banco - ignorando")
            return

        # textos - trata valores que podem vir como int/float do Excel (busca case-insensitive)
        fantasia = find_value(row, ["fantasiaLojista", "FANTASIALOJISTA", "fantasia"])
        razao = find_value(row, ["razaoLojista", "RAZAOLOJISTA", "razao"])
        if not fantasia:
            fantasia = razao or "NÃO INFORMADO"
        row["fantasiaLojista"] = fantasia
        row["razaoLojista"] = razao
        row["IELojista"] = find_value(row, ["IELojista", "IELOJISTA", "ie"]) or ""
        row["endereco"] = find_value(row, ["endereco", "ENDERECO", "endereço", "ENDEREÇO"]) or ""
        row["telefone"] = find_value(row, ["telefone", "TELEFONE"]) or ""

        # guardar FKs cruas (ID ou nome) pra resolver depois
        # Busca ramoAtividade (usa a função find_value já definida acima)
        ramo_val = find_value(row, ["ramoAtividade", "ramoatividade", "RAMOATIVIDADE", "ramo"])
        
        # Busca localizacao
        loc_val = find_value(row, ["localizacao", "localização", "LOCALIZACAO", "LOCALIZAÇÃO", "local"])
        
        # Debug: mostra as chaves disponíveis se não encontrar
        if not ramo_val:
            print(f"🔍 Chaves disponíveis no row: {list(row.keys())}")
            print(f"🔍 Valores no row: {[(k, v) for k, v in row.items() if k and 'ramo' in k.lower()]}")
            print(f"⚠️  Ramo de atividade não encontrado ou vazio")
        
        # Se ramo estiver vazio, rejeita a linha (obrigatório)
        if not ramo_val:
            print("❌ Ramo vazio - ignorado")
            return
        
        # Se localização estiver vazia, usa valor padrão (opcional)
        if not loc_val:
            loc_val = "NÃO INFORMADO"
            print(f"⚠️  Localização vazia - usando padrão: '{loc_val}'")

        row["_ramo_val"] = ramo_val
        row["_loc_val"] = loc_val
        print(f"📝 Ramo: '{ramo_val}' | Localização: '{loc_val}'")

        self.validos.append(row)
        print(f"✅ Registro válido: {fantasia} ({cnpj_masked})")

    def after_import(self, dataset, result, using_transactions, dry_run, **kwargs):
        print(f"▶️ after_import(dry_run={dry_run}) com {len(self.validos)} linha(s) válida(s)")
        print(f"🔍 DEBUG: using_transactions={using_transactions}, kwargs={kwargs}")
        
        if dry_run:
            print("🧪 Modo teste - não salvar")
            return super().after_import(dataset, result, **kwargs)

        print("💾 Modo REAL - iniciando salvamento...")
        
        # pegar usuário: admin OU primeiro superuser
        admin_user = (
            User.objects.filter(username="admin").first()
            or User.objects.filter(is_superuser=True).first()
        )
        if not admin_user:
            print("❌ Nenhum usuário admin/superuser encontrado; abortando import.")
            return super().after_import(dataset, result, **kwargs)

        print(f"👤 Usuário admin encontrado: {admin_user.username} (ID: {admin_user.id})")
        print(f"📊 Processando {len(self.validos)} registro(s)...")

        novos = 0
        erros = []
        
        try:
            with transaction.atomic():
                for i, row in enumerate(self.validos, start=1):
                    sp = transaction.savepoint()  # 👈 isola cada linha
                    try:
                        print(f"🔄 Processando linha {i}/{len(self.validos)}: {row.get('fantasiaLojista', 'N/A')}")
                        
                        # Ramo
                        rv = row["_ramo_val"]
                        print(f"   📍 Buscando ramo: '{rv}'")
                        if rv.isdigit():
                            ramo = RamoAtividade.objects.get(id=int(rv))
                        else:
                            ramo, created = RamoAtividade.objects.get_or_create(
                                atividade__iexact=rv,
                                defaults={"atividade": rv.upper(), "ativo": True},
                            )
                            if created:
                                print(f"   ✅ Ramo criado: {ramo.atividade}")
                            else:
                                print(f"   ✅ Ramo encontrado: {ramo.atividade}")
                        
                        # Localização
                        lv = row["_loc_val"]
                        print(f"   📍 Buscando localização: '{lv}'")
                        if lv.isdigit():
                            loc = Localizacao.objects.get(id=int(lv))
                        else:
                            loc, created = Localizacao.objects.get_or_create(
                                nome__iexact=lv,
                                defaults={"nome": lv.upper(), "descricao": f"Localização: {lv}"},
                            )
                            if created:
                                print(f"   ✅ Localização criada: {loc.nome}")
                            else:
                                print(f"   ✅ Localização encontrada: {loc.nome}")

                        # Criar lojista
                        print(f"   💾 Criando lojista: {row['fantasiaLojista']} ({row['CNPJLojista']})")
                        lojista = Lojista.objects.create(
                            fantasiaLojista=row["fantasiaLojista"],
                            razaoLojista=row.get("razaoLojista", ""),
                            CNPJLojista=row["CNPJLojista"],  # com máscara
                            IELojista=row.get("IELojista", ""),
                            endereco=row.get("endereco", ""),
                            telefone=row.get("telefone", ""),
                            ramoAtividade=ramo,
                            localizacao=loc,
                            status="Sim",
                            cadastrado_por=admin_user,
                            autorizado_por=admin_user,
                        )
                        
                        # Verifica se foi salvo
                        if lojista.pk:
                            transaction.savepoint_commit(sp)
                            novos += 1
                            print(f"   ✅ Lojista salvo com ID: {lojista.pk}")
                            print(f"✅ {i}/{len(self.validos)} salvo: {row['fantasiaLojista']} ({row['CNPJLojista']}) - ID: {lojista.pk}")
                        else:
                            raise Exception("Lojista criado mas sem ID (não foi salvo)")

                    except IntegrityError as e:
                        transaction.savepoint_rollback(sp)
                        erro_msg = f"Linha {i} ignorada por integridade (provável duplicado): {e}"
                        erros.append(erro_msg)
                        print(f"   ⚠️  {erro_msg}")
                    except Exception as e:
                        transaction.savepoint_rollback(sp)
                        erro_msg = f"Erro ao salvar {i}: {e}"
                        erros.append(erro_msg)
                        print(f"   ❌ {erro_msg}")
                        import traceback
                        traceback.print_exc()
        except Exception as e:
            print(f"❌ ERRO CRÍTICO na transação: {e}")
            import traceback
            traceback.print_exc()
            erros.append(f"Erro crítico: {e}")

        # Verifica quantos realmente foram salvos no banco
        cnpjs_importados = [row["CNPJLojista"] for row in self.validos]
        salvos_no_banco = Lojista.objects.filter(CNPJLojista__in=cnpjs_importados).count()
        
        print(f"🎉 Importação concluída: {novos} novo(s) | Verificação no banco: {salvos_no_banco} encontrado(s)")
        if erros:
            print(f"⚠️  {len(erros)} erro(s) durante a importação:")
            for erro in erros:
                print(f"   - {erro}")

        # faz o painel do admin mostrar a contagem correta
        try:
            result.totals["new"] = novos
        except Exception:
            pass

        # Chama super() no final para não interferir (apenas dataset e result)
        return super().after_import(dataset, result, **kwargs)




class RamoAtividadeResource(resources.ModelResource):

    class Meta:
        model = RamoAtividade


class LojistaAdmin(ImportExportModelAdmin):
    list_display = [
        "id",
        "CNPJLojista",
        "IELojista",
        "razaoLojista",
        "fantasiaLojista",
        "ramoAtividade",
        "dataCadastro",
        "cadastrado_por",
        "status",
    ]
    list_filter = [
        "status",
        "ramoAtividade",
        "localizacao",
        "lojista_cielo",
        "dataCadastro",
    ]
    search_fields = ("fantasiaLojista", "ramoAtividade__atividade", "CNPJLojista")
    readonly_fields = ("cadastrado_por",)
    resource_class = LojistaResource
    
    def import_action(self, request, *args, **kwargs):
        """
        Override import_action to handle encoding issues for Excel and CSV files.
        """
        from django.contrib import messages
        from django.core.files.uploadedfile import InMemoryUploadedFile
        from io import BytesIO
        
        try:
            # Get the uploaded file
            if 'import_file' in request.FILES:
                import_file = request.FILES['import_file']
                file_name = import_file.name.lower()
                
                # For Excel files, ensure they're read as binary
                if file_name.endswith(('.xlsx', '.xls')):
                    # Reset file pointer to beginning
                    import_file.seek(0)
                    
                    # Read the file as binary to avoid encoding issues
                    try:
                        file_content = import_file.read()
                        import_file.seek(0)
                        
                        # Verifica se o arquivo não está vazio
                        if not file_content or len(file_content) == 0:
                            messages.error(
                                request,
                                "O arquivo Excel está vazio ou corrompido. "
                                "Por favor, verifique o arquivo e tente novamente."
                            )
                            return None
                        
                        # Tenta validar o arquivo Excel antes de processar
                        try:
                            from openpyxl import load_workbook
                            # Tenta carregar o workbook para validar
                            test_workbook = load_workbook(BytesIO(file_content), read_only=True, data_only=True)
                            test_workbook.close()
                        except Exception as validation_error:
                            error_type = type(validation_error).__name__
                            if 'InvalidDimensions' in str(validation_error) or 'InvalidDimensions' in error_type:
                                messages.error(
                                    request,
                                    "Erro ao ler arquivo Excel: InvalidDimensions. "
                                    "O arquivo pode estar corrompido ou em formato incompatível. "
                                    "Soluções: 1) Abra o arquivo no Excel e salve novamente, "
                                    "2) Converta para CSV, ou 3) Verifique se o arquivo não está corrompido."
                                )
                            else:
                                messages.error(
                                    request,
                                    f"Erro ao validar arquivo Excel: {str(validation_error)}. "
                                    "O arquivo pode estar corrompido."
                                )
                            return None
                        
                        # Create a new file object that ensures binary mode
                        # This prevents any text encoding issues
                        binary_file = BytesIO(file_content)
                        new_file = InMemoryUploadedFile(
                            binary_file, None, import_file.name,
                            import_file.content_type, len(file_content), None
                        )
                        
                        # Replace the file in request.FILES
                        request.FILES['import_file'] = new_file
                        
                        # Now try to import
                        return super().import_action(request, *args, **kwargs)
                        
                    except UnicodeDecodeError as e:
                        # If we still get encoding error, try to handle it
                        messages.error(
                            request,
                            f"Erro de encoding ao processar arquivo Excel: {str(e)}. "
                            "Tente abrir o arquivo no Excel e salvá-lo novamente, ou converta para CSV."
                        )
                        return None
                    except Exception as e:
                        error_msg = str(e)
                        error_type = type(e).__name__
                        
                        # Trata erro específico InvalidDimensions do openpyxl
                        if 'InvalidDimensions' in error_msg or 'InvalidDimensions' in error_type:
                            messages.error(
                                request,
                                "Erro ao ler arquivo Excel: InvalidDimensions. "
                                "Isso geralmente ocorre quando o arquivo está corrompido ou em formato incompatível. "
                                "Tente: 1) Abrir o arquivo no Excel e salvá-lo novamente, "
                                "2) Converter para CSV, ou 3) Verificar se o arquivo não está corrompido."
                            )
                        # Check if it's an encoding-related error
                        elif 'decode' in error_msg.lower() or 'encoding' in error_msg.lower() or 'unicode' in error_msg.lower():
                            messages.error(
                                request,
                                f"Erro de encoding ao processar arquivo Excel: {error_msg}. "
                                "Tente abrir o arquivo no Excel e salvá-lo novamente."
                            )
                        else:
                            messages.error(
                                request,
                                f"Erro ao processar arquivo Excel ({error_type}): {error_msg}. "
                                "Verifique se o arquivo não está corrompido ou tente convertê-lo para CSV."
                            )
                        import traceback
                        print(f"❌ ERRO ao processar Excel: {error_type}: {error_msg}")
                        traceback.print_exc()
                        return None
                
                # For CSV files, try multiple encodings
                elif file_name.endswith('.csv'):
                    import_file.seek(0)
                    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1', 'windows-1252', 'cp1252']
                    
                    for encoding in encodings:
                        try:
                            import_file.seek(0)
                            content = import_file.read()
                            
                            # If content is bytes, decode it
                            if isinstance(content, bytes):
                                content = content.decode(encoding)
                            
                            # Create a new file-like object with decoded content
                            from django.core.files.uploadedfile import InMemoryUploadedFile
                            from io import BytesIO
                            import io
                            
                            # Encode back to UTF-8 for consistency
                            encoded_content = content.encode('utf-8')
                            decoded_file = BytesIO(encoded_content)
                            
                            new_file = InMemoryUploadedFile(
                                decoded_file, None, import_file.name,
                                import_file.content_type, len(encoded_content), None
                            )
                            
                            # Replace the file in request.FILES
                            request.FILES['import_file'] = new_file
                            
                            # Try to import with the decoded file
                            return super().import_action(request, *args, **kwargs)
                            
                        except (UnicodeDecodeError, UnicodeError):
                            # Try next encoding
                            continue
                        except Exception as e:
                            # If it's not an encoding error, check if it's a different issue
                            if 'decode' not in str(e).lower() and 'encoding' not in str(e).lower():
                                # Not an encoding error, re-raise
                                raise
                            # Otherwise, try next encoding
                            continue
                    
                    # If all encodings failed
                    messages.error(
                        request,
                        "Não foi possível decodificar o arquivo CSV. "
                        "Por favor, salve o arquivo como UTF-8 e tente novamente."
                    )
                    return None
            
            # If no file or other format, use default behavior
            return super().import_action(request, *args, **kwargs)
            
        except UnicodeDecodeError as e:
            messages.error(
                request,
                f"Erro de encoding ao processar arquivo: {str(e)}. "
                "Verifique se o arquivo está no formato correto (Excel ou CSV UTF-8)."
            )
            return None
        except Exception as e:
            # For other errors, let the parent handle it
            return super().import_action(request, *args, **kwargs)


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={}.csv".format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected"


class CsvImportForm(forms.Form):
    csv_file = forms.FileField()


class RamoAtividadeAdmin(ImportExportModelAdmin):
    list_display = ["atividade", "dataCadastro", "cadastrado_por", "ativo"]
    actions = ["export_as_csv"]
    resource_class = RamoAtividadeResource


admin.site.register(Lojista, LojistaAdmin)
admin.site.register(RamoAtividade, RamoAtividadeAdmin)
admin.site.register(AdesaoLojista, AdesaoAdmin)
admin.site.register(Localizacao, LocalizacaoAdmin)
