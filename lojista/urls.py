from django.urls import path, re_path

from . import views

app_name = "lojista"

urlpatterns = [
    # Lojistas urlpatterns = [
    path("", views.homepage, name="homepage"),
    path("lojistas/", views.lojistas_home, name="lojistas_home"),

    path("cadastro-lojista/", views.cadastro_lojista, name="cadastro_lojista"),
    path("edit/", views.edit, name="edit"),
    path("list/", views.lojistalist, name="list"),
    re_path(r"^edit/(?P<id>[-\w]+)/$", views.editlojista, name="editlojista"),
    # path('search/', FilterView.as_view(filterset_class=LojistaFilter,
    #     template_name='lojista/lojistas_list.html'), name='search'),
    path("search/", views.search, name="search"),
    path("cupons/", views.cupons, name="cupons"),
    path("sorteio/", views.search_cupom, name="sorteio"),
    # re_path(r'^search/(?P<cpf>[-\w]+)$', views.search_cpf, name='searchbycpf'),
    # Ramo de atividades pathpatterns
    path("registeratividade/", views.registeratividade, name="registeratividade"),
    path(
        "registerlocalizacao/", views.register_localizacao, name="register_localizacao"
    ),
    path("listatividade/", views.listatividade, name="listatividade"),
    path("lista_localizacao/", views.lista_localizacao, name="lista_localizao"),
    path("lojistas-interessados/", views.lista_interessado, name="lista_interessado"),
    path(
        "marcar_como_atendido/<int:adesao_id>/",
        views.marcar_como_atendido,
        name="marcar_como_atendido",
    ),
    path(
        "autorizar-lojista/<int:lojista_id>/",
        views.autorizar_lojista,
        name="autorizar_lojista",
    ),
    path(
        "editar-lojista/<int:lojista_id>/", views.editar_lojista, name="editar_lojista"
    ),
    path("gerenciar_lojistas/", views.gerenciar_lojistas, name="gerenciar_lojistas"),
    path("search/doc", views.reprint, name="search_by_doc"),
    path(
        "atualizar_status/<int:interessado_id>/",
        views.atualizar_status,
        name="atualizar_status",
    ),
    path(
        "excluir-localizacao/<int:localizacao_id>/",
        views.excluir_localizacao,
        name="excluir_localizacao",
    ),
    # Postos de trabalho
    path("register-posto/", views.register_posto, name="register_posto"),
    path("listar-postos/", views.listar_postos, name="listar_postos"),
    path("editar-posto/<int:posto_id>/", views.editar_posto, name="editar_posto"),
    path("excluir-posto/<int:posto_id>/", views.excluir_posto, name="excluir_posto"),
    # Ramos de atividade
    path("editar-ramo-atividade/<int:ramo_id>/", views.editar_ramo_atividade, name="editar_ramo_atividade"),
    path("excluir-ramo-atividade/<int:ramo_id>/", views.excluir_ramo_atividade, name="excluir_ramo_atividade"),
    # Localizações
    path("editar-localizacao/<int:localizacao_id>/", views.editar_localizacao, name="editar_localizacao"),
    # Solicitação de materiais
    path("solicitar-materiais/", views.solicitar_materiais, name="solicitar_materiais"),
    path("gestao/colaboradores/cadastrar/", views.cadastrar_colaborador, name="gestao_colaborador_cadastrar"),
    path("gestao/colaboradores/cadastrar-massa/", views.cadastrar_colaboradores_massa, name="gestao_colaboradores_massa"),
    path("gestao/colaboradores/upload-lote/", views.upload_colaboradores_lote, name="gestao_colaboradores_upload"),
    path("gestao/colaboradores/cadastro-rapido/", views.cadastrar_colaborador_rapido, name="gestao_colaborador_rapido"),
    
    # URLs de Treinamento
    path("treinamento/criar-url/", views.criar_url_treinamento, name="criar_url_treinamento"),
    path("treinamento/gerenciar-urls/", views.gerenciar_urls_treinamento, name="gerenciar_urls_treinamento"),
    path("treinamento/colaboradores/<str:hash_url>/", views.colaboradores_url_treinamento, name="colaboradores_url_treinamento"),
    path("gestao/colaboradores/pendentes/", views.gerenciar_colaboradores_pendentes, name="gestao_colaboradores_pendentes"),
    path("gestao/colaboradores/dashboard/", views.gestao_colaboradores_dashboard, name="gestao_colaboradores_dashboard"),
    path("gestao/colaboradores/configurar/<int:colaborador_id>/", views.configurar_colaborador_unificado, name="configurar_colaborador_unificado"),
    path("gestao/colaboradores/configurar/", views.configurar_colaborador_unificado, name="configurar_colaborador_novo"),
    path("autorizar-lojistas/", views.autorizar_lojistas, name="autorizar_lojistas"),
    
    # URLs de gestão de jornadas
    path("jornadas/", views.jornadas_gestao, name="jornadas_gestao"),
    path("jornadas/tipos/", views.tipos_jornada_list, name="tipos_jornada_list"),
    path("jornadas/tipos/novo/", views.tipo_jornada_create, name="tipo_jornada_create"),
    path("jornadas/tipos/<int:pk>/editar/", views.tipo_jornada_edit, name="tipo_jornada_edit"),
    path("jornadas/colaboradores/", views.jornadas_colaboradores_list, name="jornadas_colaboradores_list"),
    path("jornadas/colaboradores/novo/", views.jornada_colaborador_create, name="jornada_colaborador_create"),
    path("jornadas/colaboradores/<int:jornada_id>/editar/", views.jornada_colaborador_edit, name="jornada_colaborador_edit"),
    path("jornadas/colaboradores/<int:jornada_id>/toggle-status/", views.jornada_colaborador_toggle_status, name="jornada_colaborador_toggle_status"),
    
    # Configurações de Jornada
    path("jornadas/configuracoes/", views.configuracoes_jornada_list, name="configuracoes_jornada_list"),
    path("jornadas/configuracoes/novo/", views.configuracao_jornada_create, name="configuracao_jornada_create"),
    path("jornadas/configuracoes/<int:config_id>/editar/", views.configuracao_jornada_edit, name="configuracao_jornada_edit"),
    path("jornadas/configuracoes/<int:config_id>/toggle-status/", views.configuracao_jornada_toggle_status, name="configuracao_jornada_toggle_status"),
    
    # Exceções de Jornada
    path("jornadas/excecoes/", views.excecoes_jornada_list, name="excecoes_jornada_list"),
    path("jornadas/excecoes/novo/", views.excecao_jornada_create, name="excecao_jornada_create"),
    path("jornadas/excecoes/<int:excecao_id>/editar/", views.excecao_jornada_edit, name="excecao_jornada_edit"),
    path("jornadas/excecoes/<int:excecao_id>/toggle-status/", views.excecao_jornada_toggle_status, name="excecao_jornada_toggle_status"),
    
    # URLs AJAX para lojistas
    path("ajax/buscar-lojista/", views.buscar_lojista_ajax, name="buscar_lojista_ajax"),
    path("ajax/cadastrar-lojista/", views.cadastrar_lojista_ajax, name="cadastrar_lojista_ajax"),
    path("ajax/buscar-ramos-atividade/", views.buscar_ramos_atividade_ajax, name="buscar_ramos_atividade_ajax"),
    path("ajax/buscar-localizacoes/", views.buscar_localizacoes_ajax, name="buscar_localizacoes_ajax"),
    path("jornadas/finalizar-automaticas/", views.finalizar_jornadas_automaticas_manual, name="finalizar_jornadas_automaticas"),
    
    # Gestão de Registros de Jornada
    path("jornadas/registros/", views.gestao_registros_jornada, name="gestao_registros_jornada"),
    path("jornadas/registros/exportar-pdf/", views.exportar_registros_jornada_pdf, name="exportar_registros_jornada_pdf"),
    path("jornadas/registros/<int:registro_id>/editar/", views.editar_registro_jornada, name="editar_registro_jornada"),
    path("jornadas/finalizar-esquecidas/", views.finalizar_jornadas_esquecidas, name="finalizar_jornadas_esquecidas"),
]
