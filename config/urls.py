"""
Tabela de URLs principal (ROOT_URLCONF em settings.py).

Quando chega um pedido, o Django percorre esta lista de cima para baixo e
usa a primeira entrada cujo caminho coincide. Cada entrada liga um caminho a
uma view (a função ou classe que responde) ou a outra lista de URLs.
O name=... permite referir o URL pelo nome (nos templates e em redirect),
sem escrever o endereço.
"""
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    # Django Admin (UC5): todas as páginas de administração geradas pelo Django
    path('admin/', admin.site.urls),
    # Início e fim de sessão (UC1): views prontas do Django. A LoginView usa o
    # template registration/login.html, que está em sensores/templates/.
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Tudo o resto é tratado pela tabela de URLs da aplicação sensores
    path('', include('sensores.urls')),
]

# Com DEBUG=False o Django não serve os ficheiros estáticos: no servidor ave não
# há Nginx/Apache à frente, por isso é o próprio Waitress que serve o CSS do Admin.
if not settings.DEBUG:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    ]
