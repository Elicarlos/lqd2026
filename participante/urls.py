from . import views
from django.urls import path, re_path, reverse_lazy
from django.contrib.auth.views import (
    logout_then_login,
    PasswordChangeView,
    PasswordChangeDoneView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
    LogoutView,
)
from .views import consulta_cep, search_cpf_ajax, handle_invalid_participante_url
from .views import PoliticaPrivacidadeView, TermosUsoView
app_name = "participante"

urlpatterns = [
    path('politica-privacidade/', PoliticaPrivacidadeView.as_view(), name='politica-privacidade'),
    path('termos-uso/', TermosUsoView.as_view(), name='termos-uso'),

    # API routes (devem vir PRIMEIRO para evitar conflitos)
    path(
        "api/participante/confirmar_impressao/<int:doc_id>/",
        views.confirmar_impressao,
        name="confirmar_impressao",
    ),
    path(
        "api/participante/test/",
        views.test_api,
        name="test_api",
    ),
    path(
        "api/participante/confirmar_impressao_simple/<int:doc_id>/",
        views.confirmar_impressao_simple,
        name="confirmar_impressao_simple",
    ),
    path(
        "api/participante/reverter_impressao_simple/<int:id>/",
        views.reverter_impressao_simple,
        name="reverter_impressao_simple",
    ),
    path(
        "api/participante/registrar-cancelamento/<int:doc_id>/",
        views.registrar_cancelamento_impressao,
        name="registrar_cancelamento_impressao",
    ),
    path("contador/", views.cupons_count_view, name="contador"),
    path("login/", views.user_login, name="login"),
    path(
        "logout/", LogoutView.as_view(next_page="participante:homepage"), name="logout"
    ),
    # Relatórios
    path(
        "finalizar_campanha/<int:id>/",
        views.finalizar_campanha,
        name="finalizar_campanha",
    ),
    path("dados_campanha/", views.dados_campanha, name="dados_campanha"),
    path("graficos_campanha/", views.graficos_campanha, name="graficos_campanha"),
    path("resumo_lojistas/", views.resumo_lojistas, name="resumo_lojistas"),
    path("relatorios_camp/", views.relatorios_camp, name="relatorios_camp"),
    path("relatorio-jornada/", views.relatorio_jornada, name="relatorio_jornada"),
    path("relatorio-jornada/pdf/", views.relatorio_jornada_pdf, name="relatorio_jornada_pdf"),
    path("graficos/", views.graficos, name="graficos"),
    path("", views.homepage, name="homepage"),
    path("main/", views.main_page, name="main_page"),
    path("dash/", views.dashboard, name="dashboard"),
    # path('lojista/', views.lojista, name='notfound'),
    # path('search/', FilterView.as_view(filterset_class=UserFilter,
    #     template_name='participante/participante_list.html'), name='search'),
    path("search/", views.search, name="search"),

    path("participante/cpf/", views.search_by_cpf, name="search_by_cpf"),
    re_path(r"^list$", views.participante_list, name="list"),
    path("update_observacao_docfiscal/", views.update_observacao_docfiscal, name="update_observacao_docfiscal"),
    path("backoffice/", views.backoffice, name="backoffice"),
    path("backoffice/editar/<int:id>/", views.editar_documento_backoffice, name="editar_documento_backoffice"),
    path("backoffice/participante/<int:user_id>/", views.documentos_participante, name="documentos_participante"),
    path("backoffice/suspeitos/", views.documentos_equivalentes_suspeitos, name="documentos_suspeitos"),
    path(
        "impressao_backoffice/", views.impressao_backoffice, name="impressao_backoffice"
    ),
    path("impressao/", views.print_detail, name="impressao"),
    # URLs específicas de participantes (devem vir ANTES do catch-all)
    re_path(r"^participante/(?P<id>\d+)/$", views.user_detail, name="user_detail"),
    re_path(r"^participante/edit/(?P<id>\d+)/$", views.user_edit, name="user_edit"),
    re_path(
        r"^participante/reverter_impressao/(?P<id>[-\w]+)/$",
        views.reverter_impressao_cupons,
        name="reverter_impressao_cupons",
    ),
    # Seleção de posto de trabalho (deve vir ANTES do catch-all)
    path("participante/selecionar-posto/", views.selecionar_posto, name="selecionar_posto"),
    # Catch-all para URLs inválidas de participantes (deve vir DEPOIS das específicas)
    # Excluir URLs que começam com 'api/' para evitar conflitos
    re_path(r"^participante/(?!api/)(?P<invalid_path>.+)/$", views.handle_invalid_participante_url, name="invalid_participante_url"),
    # Coupons paths
    path("docsfiscais/", views.doclist, name="docsfiscais"),
    # Coupons paths
    path("coupons/", views.coupons, name="coupons"),
    # Premios paths
    path("premios/", views.premios, name="premios"),
    # path('cadastrar/', views.register, name='register'),
    # Removido final de campanha
    path("cadastros/", views.register, name="register"),
    path("cadastro-concluido/", views.register_done, name="register_done"),
    path("cadastro-participante-operador/", views.cadastro_participante_operador, name="cadastro-participante-operador"),
    path("edit/", views.edit, name="edit"),
    path("confirmar-jornada/", views.confirmar_jornada, name="confirmar_jornada"),
    path("finalizar-jornada/", views.finalizar_jornada, name="finalizar_jornada"),
    # Documentos Fiscais paths
    path("adddocfiscal/", views.adddocfiscal, name="adddocfiscal"),
    path("upload_file/", views.upload_file, name="upload_file"),
    re_path(
        r"^editdocfiscal/(?P<id>[-\w]+)/$", views.editdocfiscal, name="editdocfiscal"
    ),
    re_path(
        r"^editdocfiscalbyop/(?P<id>[-\w]+)/$",
        views.editdocfiscalbyop,
        name="editdocfiscalbyop",
    ),
    re_path(
        r"^validadocfiscal/(?P<id>[-\w]+)/$",
        views.validadocfiscal,
        name="validadocfiscal",
    ),
    # Auditoria
    path("auditoria/", views.auditoria_view, name="auditoria"),
    re_path(
        r"^marcar_inconsistente/(?P<id>[-\w]+)/$",
        views.marcar_inconsistente,
        name="marcar_inconsistente",
    ),
    # login / logout paths
    # path('logout/', logout, name='logout'),
    path("logout-then-login/", logout_then_login, name="logout_then_login"),
    # change password paths
    re_path(
        r"^password-change/$",
        PasswordChangeView.as_view(
            template_name="registration/password_change_form.html",
            success_url=reverse_lazy("participante:password_change_done"),
        ),
        name="password_change",
    ),
    re_path(
        r"^password-change/done/$",
        PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html", extra_context=None
        ),
        name="password_change_done",
    ),
    # restore password paths
    # REMOVIDO
    # re_path(r'^password-reset/
    # ,PasswordResetView.as_view(
    #     template_name='registration/password_reset_form.html',
    #     email_template_name='registration/password_reset_email.html',
    #     success_url = reverse_lazy('participante:password_reset_done')),name='password_reset'),
    path(
        "password-reset/",
        views.CustomPasswordResetView.as_view(),
        name="password_reset",
    ),
    re_path(
        r"^password-reset/done/$",
        PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html", extra_context=None
        ),
        name="password_reset_done",
    ),
    re_path(
        r"^password-reset/confirm/(?P<uidb64>[-\w]+)/(?P<token>[-\w]+)/$",
        PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("participante:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    re_path(
        r"^password-reset/complete/$",
        PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html",
            extra_context=None,
        ),
        name="password_reset_complete",
    ),
    re_path(
        r"^edit_by_id/(?P<id>\d+)/$", views.user_edit_by_id, name="user_edit_by_id"
    ),
    path("consulta-cep/", consulta_cep, name="consulta_cep"),
    path("search-cpf/", search_cpf_ajax, name="search_cpf"),
    path("calcular-cupons-preview/", views.calcular_cupons_preview, name="calcular_cupons_preview"),
    path("registro_ponto/", views.registro_ponto, name="registro-ponto"),
    path(
        "registro_ponto_filtros/",
        views.registro_ponto_filtros,
        name="registro-ponto-filtros",
    ),
    path("gerar_pdf_batidas/", views.gerar_pdf_batidas, name="gerar_pdf_batidas"),
    path(
        "gerar_pdf_batidas_filtros/",
        views.gerar_pdf_batidas_filtros,
        name="gerar_pdf_batidas_filtros",
    ),
    # Adicionando a URL para a view de confirmação
    path(
        "doc_fiscal_done/<int:doc_id>/", views.doc_fiscal_done, name="doc_fiscal_done"
    ),
    path(
        "atualizar-status-impresso/<int:doc_id>/",
        views.atualizar_status_impresso,
        name="atualizar_status_impresso",
    ),
    path("gestao/colaboradores/", views.gerenciar_colaboradores, name="gestao_colaboradores"),
    path("change-password/", views.change_password, name="change_password"),
    path("roles/", views.manage_roles, name="manage_roles"),
    path("limpar-mensagens/", views.limpar_mensagens, name="limpar_mensagens"),
    path("update_observacao/", views.update_observacao, name="update_observacao"),
    path("reprint/<int:doc_id>/", views.reprint_document, name="reprint_document"),
    
    # ===== URLs PARA GERENCIAMENTO DE FUNCIONALIDADES E CARDS =====
    
    # Funcionalidades
    path("funcionalidades/", views.funcionalidades_list, name="funcionalidades_list"),
    path("funcionalidades/criar/", views.funcionalidade_create, name="funcionalidade_create"),
    path("funcionalidades/<int:pk>/editar/", views.funcionalidade_edit, name="funcionalidade_edit"),
    path("funcionalidades/<int:pk>/excluir/", views.funcionalidade_delete, name="funcionalidade_delete"),
    
    # Cards
    path("cards/", views.cards_list, name="cards_list"),
    path("cards/criar/", views.card_create, name="card_create"),
    path("cards/<int:pk>/editar/", views.card_edit, name="card_edit"),
    path("cards/<int:pk>/excluir/", views.card_delete, name="card_delete"),
    path("cards/reordenar/", views.reorder_cards, name="reorder_cards"),
    
    # Seções
    path("secoes/", views.secoes_list, name="secoes_list"),
    path("secoes/<int:pk>/editar/", views.secao_edit, name="secao_edit"),
    path("secoes/<int:pk>/toggle/", views.secao_toggle, name="secao_toggle"),
    
    # URLs de Cadastro Público
    path('cadastro/<str:hash_url>/', views.cadastro_publico, name='cadastro_publico'),
    path('cadastro/<str:hash_url>/sucesso/', views.cadastro_sucesso, name='cadastro_sucesso'),

    
    # Documento Validado - Operador
    path('documento-validado/<int:doc_id>/', views.documento_validado_op, name='documento_validado_op'),
    
    # Finalizar Jornada
    path('finalizar-jornada-colaborador/', views.finalizar_jornada_colaborador, name='finalizar_jornada_colaborador'),
    
    # Página de Aviso/E erro elegante
    path('aviso/', views.exibir_aviso, name='exibir_aviso'),
    
    # Exemplos de uso da nova funcionalidade (para demonstração)
    path('exemplo-aviso/', views.exemplo_uso_aviso_elegante, name='exemplo_aviso'),
    path('exemplo-aviso-direto/', views.exemplo_uso_direto_aviso, name='exemplo_aviso_direto'),
]
