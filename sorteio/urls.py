from django.urls import path
from . import views

app_name = 'sorteio'

urlpatterns = [
    path('', views.sorteio_home, name='home'),
    path('resultados/', views.sorteio_resultados, name='resultados'),
]


