"""
URLs da aplicação sensores (incluídas em config/urls.py com path('', ...)).

Cada path() liga um caminho a uma view. <int:pk> captura um número do
endereço e passa-o à view como argumento pk (o id do sensor). O name=...
é usado nos templates, por exemplo {% url 'historico' sensor.pk %}.
"""
from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from . import views

urlpatterns = [
    path('', views.painel, name='painel'),                                  # UC2
    path('sensores/<int:pk>/', views.historico, name='historico'),          # UC3
    path('sensores/<int:pk>/csv/', views.exportar_csv, name='exportar_csv'),  # UC4
    # UC6: as views do DRF são classes; .as_view() converte-a numa função
    path('api/leituras/', views.SubmeterLeiturasAPIView.as_view(), name='api_leituras'),
    # Documento OpenAPI (JSON/YAML) gerado pelo drf-spectacular a partir das views
    path('api/schema/', SpectacularAPIView.as_view(), name='api_schema'),
    # Página do Scalar, que lê o documento acima e permite testar a API
    path('api/docs/', views.api_docs, name='api_docs'),
]
