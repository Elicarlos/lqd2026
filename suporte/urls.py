"""
URLs específicas para o suporte.
Rotas seguras e acessíveis apenas para usuários do grupo 'Suporte' e superusers.
"""

from django.urls import path
from . import views

app_name = 'suporte'

urlpatterns = [
    # Dashboard principal do suporte
    path('dashboard/', views.suporte_dashboard, name='dashboard'),
    
    # Busca de participantes
    path('buscar-participante/', views.buscar_participante_cpf, name='buscar_participante'),
    
    # Busca de documentos
    path('buscar-documento/', views.buscar_documento_numero, name='buscar_documento'),
    
    # Reversão de documentos
    path('reverter-documento/<int:doc_id>/', views.reverter_documento_suporte, name='reverter_documento'),
    
    # Listagem de documentos recentes
    path('documentos-recentes/', views.listar_documentos_recentes, name='documentos_recentes'),
]
