from django.urls import path

from . import views

urlpatterns = [
    path('', views.painel, name='painel'),
    path('sensores/<int:pk>/', views.historico, name='historico'),
    path('sensores/<int:pk>/csv/', views.exportar_csv, name='exportar_csv'),
    path('api/leituras/', views.SubmeterLeiturasAPIView.as_view(), name='api_leituras'),
]
