from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.urls import reverse, NoReverseMatch
from participante.models import CardDinamico

class Command(BaseCommand):
    help = 'Gerencia cards completos: verifica, corrige e atualiza URLs em sequência'

    def add_arguments(self, parser):
        parser.add_argument(
            '--acao',
            type=str,
            choices=['verificar', 'corrigir', 'atualizar', 'tudo'],
            default='tudo',
            help='Ação a ser executada: verificar, corrigir, atualizar ou tudo'
        )

    def handle(self, *args, **options):
        acao = options['acao']
        
        if acao == 'verificar' or acao == 'tudo':
            self.verificar_urls_cards()
        
        if acao == 'corrigir' or acao == 'tudo':
            self.corrigir_urls_invalidas()
        
        if acao == 'atualizar' or acao == 'tudo':
            self.atualizar_cards_grupos()
        
        if acao == 'tudo':
            self.verificar_urls_cards()  # Verificar novamente após correções

    def verificar_urls_cards(self):
        """Verifica se as URLs dos cards existem no sistema"""
        
        self.stdout.write(self.style.SUCCESS('\n🔍 VERIFICANDO URLs dos cards...'))
        
        # Buscar todos os cards
        cards = CardDinamico.objects.all().order_by('nome')
        
        if not cards.exists():
            self.stdout.write("❌ Nenhum card encontrado no sistema!")
            return
        
        self.stdout.write(f"📋 Encontrados {cards.count()} cards para verificar")
        self.stdout.write()
        
        urls_validas = []
        urls_invalidas = []
        
        for card in cards:
            url = card.url.strip()
            
            if not url:
                self.stdout.write(f"⚠️  Card '{card.nome}': URL vazia")
                urls_invalidas.append(card)
                continue
            
            # Remover barra inicial se existir
            if url.startswith('/'):
                url = url[1:]
            
            # Tentar resolver a URL
            try:
                # Se a URL contém ':', é um nome de URL do Django
                if ':' in url:
                    reverse(url)
                    status = "✅ VÁLIDA"
                    urls_validas.append(card)
                else:
                    # URL simples, verificar se começa com http ou é uma rota válida
                    if url.startswith('http'):
                        status = "✅ VÁLIDA (URL externa)"
                        urls_validas.append(card)
                    else:
                        # Tentar como URL interna
                        reverse(url)
                        status = "✅ VÁLIDA"
                        urls_validas.append(card)
                        
            except NoReverseMatch:
                status = "❌ INVÁLIDA"
                urls_invalidas.append(card)
            except Exception as e:
                status = f"❌ ERRO: {str(e)}"
                urls_invalidas.append(card)
            
            grupos = [g.name for g in card.grupos_permitidos.all()]
            self.stdout.write(f"{status} | {card.nome:30} | {card.url:40} | Grupos: {grupos}")
        
        # Resumo
        self.stdout.write()
        self.stdout.write("📊 RESUMO DA VERIFICAÇÃO:")
        self.stdout.write(f"  ✅ URLs válidas: {len(urls_validas)}")
        self.stdout.write(f"  ❌ URLs inválidas: {len(urls_invalidas)}")
        
        if urls_invalidas:
            self.stdout.write()
            self.stdout.write("🔧 CARDS COM URLs INVÁLIDAS:")
            for card in urls_invalidas:
                self.stdout.write(f"  • {card.nome}: {card.url}")

    def corrigir_urls_invalidas(self):
        """Corrige as URLs inválidas identificadas"""
        
        self.stdout.write(self.style.SUCCESS('\n🔧 CORRIGINDO URLs inválidas...'))
        
        # Mapeamento baseado nas URLs inválidas identificadas
        correcoes_urls = {
            # URLs de jornada
            'participante:cadastrar_jornada': 'lojista:jornadas_gestao',
            'participante:gestao_jornadas': 'lojista:jornadas_gestao',
            
                         # URLs de lojista
             'lojista:cadastrar_lojista': 'lojista:cadastro_lojista',
             'lojista:listar_localizacoes': 'lojista:lista_localizao',
             'lojista:listar_ramos': 'lojista:registeratividade',
            
            # URLs de postos
            'participante:cadastrar_posto': 'lojista:register_posto',
            
            # URLs de cupom
            'cupom:list': 'participante:backoffice',  # Alternativa para reimpressão
        }
        
        # Buscar todos os cards
        cards = CardDinamico.objects.all()
        total_corrigidos = 0
        
        for card in cards:
            url_atual = card.url.strip()
            
            # Verificar se precisa de correção
            if url_atual in correcoes_urls:
                url_nova = correcoes_urls[url_atual]
                card.url = url_nova
                card.save()
                
                self.stdout.write(f'  ✅ Corrigido: {card.nome}')
                self.stdout.write(f'     {url_atual} → {url_nova}')
                total_corrigidos += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n🎉 Correção concluída!'))
        self.stdout.write(f'📊 Total de URLs corrigidas: {total_corrigidos}')

    def atualizar_cards_grupos(self):
        """Atualiza os cards conforme os grupos específicos"""
        
        self.stdout.write(self.style.SUCCESS('\n🎯 ATUALIZANDO cards por grupos...'))
        
        # Configuração dos cards por grupo
        cards_config = {
            'Operador': [
                {
                    'nome': 'cadastro_participante',
                    'titulo': 'Cadastro Participante',
                    'descricao': 'Cadastrar novos participantes no sistema',
                    'tipo': 'PARTICIPANTE',
                    'icone': 'fas fa-user-plus',
                    'cor': 'primary',
                    'url': 'participante:register',
                    'ordem': 1
                },
                {
                    'nome': 'buscar_participante_cpf',
                    'titulo': 'Buscar Participante por CPF',
                    'descricao': 'Buscar participantes pelo número do CPF',
                    'tipo': 'PARTICIPANTE',
                    'icone': 'fas fa-search',
                    'cor': 'info',
                    'url': 'participante:search_by_cpf',
                    'ordem': 2
                },
                {
                    'nome': 'cadastro_lojista',
                    'titulo': 'Cadastro Lojista',
                    'descricao': 'Cadastrar novos lojistas no sistema',
                    'tipo': 'LOJISTA',
                    'icone': 'fas fa-store',
                    'cor': 'success',
                    'url': 'lojista:cadastro_lojista',
                    'ordem': 3
                },
                {
                    'nome': 'reimpressao_cupons',
                    'titulo': 'Reimpressão de Cupons',
                    'descricao': 'Reimprimir cupons perdidos ou danificados',
                    'tipo': 'OPERACOES',
                    'icone': 'fas fa-print',
                    'cor': 'warning',
                    'url': 'participante:backoffice',
                    'ordem': 4
                },
                {
                    'nome': 'relatorio_jornada_individual',
                    'titulo': 'Relatório de Jornada (Individual)',
                    'descricao': 'Visualizar relatório de jornada individual',
                    'tipo': 'RELATORIO',
                    'icone': 'fas fa-clock',
                    'cor': 'secondary',
                    'url': 'participante:relatorio_jornada',
                    'ordem': 5
                }
            ],
            
            'Backoffice': [
                {
                    'nome': 'validar_documentos_pendentes',
                    'titulo': 'Validar Documentos Pendentes',
                    'descricao': 'Validar documentos fiscais pendentes de aprovação',
                    'tipo': 'BACKOFFICE',
                    'icone': 'fas fa-check-circle',
                    'cor': 'success',
                    'url': 'participante:backoffice',
                    'ordem': 1
                },
                {
                    'nome': 'imprimir_documentos_validados',
                    'titulo': 'Imprimir Documentos Validados',
                    'descricao': 'Imprimir cupons de documentos já validados',
                    'tipo': 'BACKOFFICE',
                    'icone': 'fas fa-print',
                    'cor': 'primary',
                    'url': 'participante:impressao_backoffice',
                    'ordem': 2
                },
                {
                    'nome': 'reimpressao_cupons_backoffice',
                    'titulo': 'Reimpressão de Cupons',
                    'descricao': 'Reimprimir cupons perdidos ou danificados',
                    'tipo': 'BACKOFFICE',
                    'icone': 'fas fa-print',
                    'cor': 'warning',
                    'url': 'participante:backoffice',
                    'ordem': 3
                },

            ],
            
            'Supervisor': [
                {
                    'nome': 'cadastro_lojista_supervisor',
                    'titulo': 'Cadastro Lojista',
                    'descricao': 'Cadastrar novos lojistas no sistema',
                    'tipo': 'LOJISTA',
                    'icone': 'fas fa-store',
                    'cor': 'success',
                    'url': 'lojista:cadastro_lojista',
                    'ordem': 1
                },
                                 {
                     'nome': 'cadastro_ramo_atividade',
                     'titulo': 'Cadastro Ramo Atividade',
                     'descricao': 'Cadastrar novos ramos de atividade',
                     'tipo': 'CONFIGURACAO',
                     'icone': 'fas fa-tags',
                     'cor': 'info',
                     'url': 'lojista:registeratividade',
                     'ordem': 2
                 },
                {
                    'nome': 'cadastro_postos_trabalho',
                    'titulo': 'Cadastro Postos de Trabalho',
                    'descricao': 'Cadastrar novos postos de trabalho',
                    'tipo': 'CONFIGURACAO',
                    'icone': 'fas fa-building',
                    'cor': 'primary',
                    'url': 'lojista:register_posto',
                    'ordem': 3
                },
                {
                    'nome': 'cadastro_localizacao_lojista',
                    'titulo': 'Cadastro Localização do Lojista',
                    'descricao': 'Cadastrar localizações para lojistas',
                    'tipo': 'CONFIGURACAO',
                    'icone': 'fas fa-map-marker-alt',
                    'cor': 'warning',
                    'url': 'lojista:lista_localizao',
                    'ordem': 4
                },
                {
                    'nome': 'autorizar_lojista',
                    'titulo': 'Autorizar Lojista',
                    'descricao': 'Autorizar lojistas pendentes',
                    'tipo': 'LOJISTA',
                    'icone': 'fas fa-user-check',
                    'cor': 'success',
                    'url': 'lojista:autorizar_lojistas',
                    'ordem': 5
                },

            ],
            
            'Recursos Humanos': [
                {
                    'nome': 'cadastro_operador',
                    'titulo': 'Cadastro Operador',
                    'descricao': 'Cadastrar novos operadores no sistema',
                    'tipo': 'RECURSOS_HUMANOS',
                    'icone': 'fas fa-user-plus',
                    'cor': 'primary',
                    'url': 'participante:cadastro-participante-operador',
                    'ordem': 1
                },
                {
                    'nome': 'cadastro_jornada',
                    'titulo': 'Cadastro de Jornada',
                    'descricao': 'Cadastrar novas jornadas de trabalho',
                    'tipo': 'RECURSOS_HUMANOS',
                    'icone': 'fas fa-calendar-plus',
                    'cor': 'info',
                    'url': 'lojista:jornadas_gestao',
                    'ordem': 2
                },
                {
                    'nome': 'gestao_jornadas',
                    'titulo': 'Gestão de Jornadas',
                    'descricao': 'Gerenciar jornadas de trabalho',
                    'tipo': 'RECURSOS_HUMANOS',
                    'icone': 'fas fa-clock',
                    'cor': 'warning',
                    'url': 'lojista:jornadas_gestao',
                    'ordem': 3
                },
                {
                    'nome': 'relatorio_jornada',
                    'titulo': 'Relatório de Jornada',
                    'descricao': 'Visualizar relatórios de jornada individual e geral',
                    'tipo': 'RELATORIO',
                    'icone': 'fas fa-chart-bar',
                    'cor': 'secondary',
                    'url': 'participante:relatorio_jornada',
                    'ordem': 4
                }
            ],
            
            'Gerente': [
                {
                    'nome': 'dashboard_campanha',
                    'titulo': 'Dashboard da Campanha',
                    'descricao': 'Visualizar dashboard com dados da campanha',
                    'tipo': 'RELATORIO',
                    'icone': 'fas fa-tachometer-alt',
                    'cor': 'primary',
                    'url': 'participante:dados_campanha',
                    'ordem': 1
                },
                {
                    'nome': 'graficos',
                    'titulo': 'Gráficos',
                    'descricao': 'Visualizar gráficos e estatísticas da campanha',
                    'tipo': 'RELATORIO',
                    'icone': 'fas fa-chart-pie',
                    'cor': 'info',
                    'url': 'participante:graficos_campanha',
                    'ordem': 2
                },
                {
                    'nome': 'relatorio_jornada',
                    'titulo': 'Relatório de Jornada',
                    'descricao': 'Visualizar relatórios de jornada individual e geral',
                    'tipo': 'RELATORIO',
                    'icone': 'fas fa-chart-line',
                    'cor': 'success',
                    'url': 'participante:relatorio_jornada',
                    'ordem': 3
                }
            ],
            
            'Gerente Solve': [
                {
                    'nome': 'dashboard_campanha_solve',
                    'titulo': 'Dashboard da Campanha',
                    'descricao': 'Visualizar dashboard com dados da campanha',
                    'tipo': 'RELATORIO',
                    'icone': 'fas fa-tachometer-alt',
                    'cor': 'primary',
                    'url': 'participante:dados_campanha',
                    'ordem': 1
                },
                {
                    'nome': 'graficos_solve',
                    'titulo': 'Gráficos',
                    'descricao': 'Visualizar gráficos e estatísticas da campanha',
                    'tipo': 'RELATORIO',
                    'icone': 'fas fa-chart-pie',
                    'cor': 'info',
                    'url': 'participante:graficos_campanha',
                    'ordem': 2
                }
            ],
            
            'Suporte': [
                {
                    'nome': 'editar_participante',
                    'titulo': 'Editar Participante',
                    'descricao': 'Editar dados de participantes',
                    'tipo': 'PARTICIPANTE',
                    'icone': 'fas fa-user-edit',
                    'cor': 'warning',
                    'url': 'participante:edit',
                    'ordem': 1
                },
                {
                    'nome': 'cadastro_lojista_suporte',
                    'titulo': 'Cadastro Lojista',
                    'descricao': 'Cadastrar novos lojistas no sistema',
                    'tipo': 'LOJISTA',
                    'icone': 'fas fa-store',
                    'cor': 'success',
                    'url': 'lojista:cadastro_lojista',
                    'ordem': 2
                },
                                 {
                     'nome': 'cadastro_ramo_atividade_suporte',
                     'titulo': 'Cadastro Ramo Atividade',
                     'descricao': 'Cadastrar novos ramos de atividade',
                     'tipo': 'CONFIGURACAO',
                     'icone': 'fas fa-tags',
                     'cor': 'info',
                     'url': 'lojista:registeratividade',
                     'ordem': 3
                 },
                {
                    'nome': 'cadastro_posto_trabalho_suporte',
                    'titulo': 'Cadastro de Posto de Trabalho',
                    'descricao': 'Cadastrar novos postos de trabalho',
                    'tipo': 'CONFIGURACAO',
                    'icone': 'fas fa-building',
                    'cor': 'primary',
                    'url': 'lojista:register_posto',
                    'ordem': 4
                },
                {
                    'nome': 'cadastro_jornada_trabalho',
                    'titulo': 'Cadastro de Jornada de Trabalho',
                    'descricao': 'Cadastrar novas jornadas de trabalho',
                    'tipo': 'RECURSOS_HUMANOS',
                    'icone': 'fas fa-calendar-plus',
                    'cor': 'info',
                    'url': 'lojista:jornadas_gestao',
                    'ordem': 5
                },
                {
                    'nome': 'gestao_jornada_suporte',
                    'titulo': 'Gestão de Jornada',
                    'descricao': 'Gerenciar jornadas de trabalho',
                    'tipo': 'RECURSOS_HUMANOS',
                    'icone': 'fas fa-clock',
                    'cor': 'warning',
                    'url': 'lojista:jornadas_gestao',
                    'ordem': 6
                }
            ]
        }
        
        # Criar ou atualizar cards
        total_cards = 0
        for grupo_nome, cards_do_grupo in cards_config.items():
            self.stdout.write(f'\n📋 Configurando cards para o grupo: {grupo_nome}')
            
            # Verificar se o grupo existe
            try:
                grupo = Group.objects.get(name=grupo_nome)
                self.stdout.write(f'  ✅ Grupo encontrado: {grupo.name}')
            except Group.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Grupo "{grupo_nome}" não encontrado. Criando...'))
                grupo = Group.objects.create(name=grupo_nome)
                self.stdout.write(f'  ✅ Grupo criado: {grupo.name}')
            
            # Criar cards para este grupo
            for card_config in cards_do_grupo:
                card, created = CardDinamico.objects.get_or_create(
                    nome=card_config['nome'],
                    defaults={
                        'titulo': card_config['titulo'],
                        'descricao': card_config['descricao'],
                        'tipo': card_config['tipo'],
                        'icone': card_config['icone'],
                        'cor': card_config['cor'],
                        'url': card_config['url'],
                        'ordem': card_config['ordem'],
                        'ativo': True
                    }
                )
                
                if created:
                    self.stdout.write(f'  ✅ Criado: {card.titulo}')
                else:
                    # Atualizar se já existe
                    card.titulo = card_config['titulo']
                    card.descricao = card_config['descricao']
                    card.tipo = card_config['tipo']
                    card.icone = card_config['icone']
                    card.cor = card_config['cor']
                    card.url = card_config['url']
                    card.ordem = card_config['ordem']
                    card.ativo = True
                    card.save()
                    self.stdout.write(f'  🔄 Atualizado: {card.titulo}')
                
                # Configurar permissões do grupo
                card.grupos_permitidos.clear()
                card.grupos_permitidos.add(grupo)
                
                total_cards += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n🎉 Atualização concluída!'))
        self.stdout.write(f'📊 Total de cards criados/atualizados: {total_cards}')
        
        # Mostrar resumo por grupo
        self.stdout.write('\n📋 RESUMO POR GRUPO:')
        for grupo_nome in cards_config.keys():
            try:
                grupo = Group.objects.get(name=grupo_nome)
                cards_count = CardDinamico.objects.filter(grupos_permitidos=grupo).count()
                self.stdout.write(f'  {grupo_nome}: {cards_count} cards')
            except Group.DoesNotExist:
                self.stdout.write(f'  {grupo_nome}: Grupo não encontrado')
