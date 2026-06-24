"""liquida2018 URL Configuration"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from bcp import urls as burls
from cupom import urls as curls
from lojista import urls as lurls
from participante import urls as purls
from suporte import urls as surls
from organizacao import urls as ourls
from sorteio import urls as surlsorteio
from participante.views import api_root

# handler404 = 'participante.views.not_found_page_view'
# handler500 = 'participante.views.server_error_view'

urlpatterns = [
    path("suporte/", include(surls, namespace="suporte")),
    path("organizacao/", include(ourls, namespace="organizacao")),
    path("sorteio/", include(surlsorteio, namespace="sorteio")),
    path("", include(purls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("op-admin-nimda-solu/", admin.site.urls),
    re_path(r"^cupom/", include(curls, namespace="cupom")),
    path("lojista/", include(lurls, namespace="lojista")),
    path("barcode/", include(burls, namespace="bcp")),
    path("api/", api_root, name="api_root"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/participante/v1/", include("participante.api.v1.urls")),
    path("api/lojista/v1/", include("lojista.api.v1.urls")),
    
    # python-social-auth
    # url('social-auth/', include('social.apps.django_app.urls', namespace='social')),
]

# Servir arquivos de mídia e estáticos em desenvolvimento
if settings.DEBUG:
    urlpatterns += [
        path("silk/", include("silk.urls", namespace="silk")),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Em desenvolvimento, servir de STATICFILES_DIRS, não STATIC_ROOT
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
# Em produção, os arquivos de mídia são servidos pelo S3
# Mas se não estiver usando S3, servir localmente
elif not getattr(settings, 'USE_S3', False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)    

admin.site.site_header = "Administração Natal de Luz e Prêmios"
admin.site.site_title = "Natal de Luz e Prêmios"
admin.site.index_title = "Bem vindo a administração do Natal de Luz e Prêmios"
admin.site.site_url = "/lojista/"
admin.site.site_url = "/lojista/"
