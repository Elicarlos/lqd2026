from django.urls import path
from . import views


app_name = 'organizacao'

urlpatterns = [
    path('', views.pessoas_list, name='pessoas_list'),
    path('nova/', views.pessoa_create, name='pessoa_create'),
    path('<int:pk>/editar/', views.pessoa_update, name='pessoa_update'),
    path('<int:pk>/excluir/', views.pessoa_delete, name='pessoa_delete'),
]


