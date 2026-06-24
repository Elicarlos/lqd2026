from . import views
from django.urls import re_path

app_name = "cupom"

urlpatterns = [
    # cupom urlpatterns = [
    # path('', views.addcupom, name='detail'),
    re_path(r"^(?P<numerodocumento>[-\w]+)/$", views.addcupom, name="addcupom"),
    re_path(r"^cupons/(?P<username>[-\w]+)/$", views.cupomlist, name="list"),
]
