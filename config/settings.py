"""
Configuração global do projeto Django.

Este ficheiro é lido uma vez, quando o Django arranca (com o runserver, o
Waitress ou um comando do manage.py). Cada variável em MAIÚSCULAS é uma
definição que o Django ou as bibliotecas instaladas consultam.

Várias definições vêm de variáveis de ambiente (os.environ), para que o mesmo
código funcione no PC (valores por omissão) e no servidor ave (valores
definidos pelo servidor_ave.sh), sem alterar o ficheiro.

Referência: https://docs.djangoproject.com/en/6.1/ref/settings/
"""

import os
from pathlib import Path

# Pasta raiz do projeto (a que contém o manage.py): este ficheiro está em
# config/settings.py, por isso sobe-se dois níveis.
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- Segurança

# Chave usada para assinar sessões, cookies e tokens CSRF. Se alguém a
# conhecer, consegue forjar sessões. No servidor ave vem do ambiente
# (servidor_ave.sh gera-a e guarda-a fora do código); a de baixo é só local.
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-o7!-ws_yndrrw7-=d%@n#2!_z_@k1ue$ot8)mbf(-b(10$gnji')

# Modo de depuração: mostra páginas de erro detalhadas e serve os ficheiros
# estáticos. Nunca deve estar ligado num servidor público.
# Por omissão está ligado (PC); os ensaios e o servidor usam DJANGO_DEBUG=0.
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'

# Nomes de servidor aceites no cabeçalho Host dos pedidos (proteção contra
# ataques de Host forjado). Endereços extra separados por vírgulas.
ALLOWED_HOSTS = ['127.0.0.1', 'localhost'] + [
    h for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if h]

# Servidor ave: o Apache passa os pedidos de /~1220847/rinte/ ao Waitress
# (public_html/rinte/.htaccess). O prefixo entra nos URLs gerados e limita os
# cookies a esta app, porque o domínio é partilhado com outros alunos.
FORCE_SCRIPT_NAME = os.environ.get('DJANGO_SCRIPT_NAME') or None
if FORCE_SCRIPT_NAME:
    SESSION_COOKIE_PATH = CSRF_COOKIE_PATH = FORCE_SCRIPT_NAME + '/'

# Origens de onde se aceitam formulários POST (verificação CSRF). Só é preciso
# no servidor, porque o endereço público é diferente do endereço local.
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o]


# ---------------------------------------------------------------- Aplicações

# Aplicações ativas. As django.contrib.* vêm com o Django; as seguintes são
# bibliotecas instaladas pelo requirements.txt; a última é a nossa.
INSTALLED_APPS = [
    'django.contrib.admin',          # Django Admin (UC5)
    'django.contrib.auth',           # utilizadores, grupos, permissões, login (UC1)
    'django.contrib.contenttypes',   # registo dos modelos (usado pelo auth e admin)
    'django.contrib.sessions',       # sessões guardadas na base de dados
    'django.contrib.messages',       # mensagens de uma página para a seguinte
    'django.contrib.staticfiles',    # ficheiros estáticos (CSS/JS do Admin)
    'rest_framework',                # Django REST Framework: a API (UC6)
    'rest_framework.authtoken',      # tabela de tokens dos dispositivos
    'drf_spectacular',               # gera o documento OpenAPI da API
    'sensores',                      # a nossa aplicação: modelos, views, templates
]

# Middleware: camadas por onde passa cada pedido (de cima para baixo) e cada
# resposta (de baixo para cima), antes e depois da view. A ordem importa:
# por exemplo, a autenticação precisa da sessão, por isso vem depois dela.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',           # cabeçalhos de segurança
    'django.contrib.sessions.middleware.SessionMiddleware',    # lê/grava a sessão (cookie sessionid)
    'django.middleware.common.CommonMiddleware',               # normaliza URLs (barra final)
    'django.middleware.csrf.CsrfViewMiddleware',               # proteção CSRF nos POST
    'django.contrib.auth.middleware.AuthenticationMiddleware', # põe o utilizador em request.user
    'django.contrib.messages.middleware.MessageMiddleware',    # mensagens entre páginas
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # impede abrir as páginas em iframes
]

# Ficheiro com a tabela de URLs principal (o "índice" do site).
ROOT_URLCONF = 'config.urls'

# Motor de templates. Com APP_DIRS=True, o Django procura os templates na
# pasta templates/ de cada aplicação (aqui, sensores/templates/).
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            # Variáveis disponíveis em todos os templates sem a view as passar:
            # request, user (utilizador autenticado) e messages.
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Ponto de entrada para servidores WSGI como o Waitress (ver config/wsgi.py).
WSGI_APPLICATION = 'config.wsgi.application'


# ---------------------------------------------------------------- Base de dados

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # Fora da pasta do OneDrive: a sincronização interfere com as escritas
        'NAME': Path(os.environ.get('DJANGO_DB_PATH',
                                    Path.home() / 'rinte-dados' / 'db.sqlite3')),
        'OPTIONS': {
            # WAL: leituras em simultâneo com uma escrita;
            # IMMEDIATE + timeout: escritas concorrentes esperam em vez de falhar.
            'init_command': 'PRAGMA journal_mode=WAL;',
            'transaction_mode': 'IMMEDIATE',
            'timeout': 20,
        },
    }
}


# ---------------------------------------------------------------- Palavras-passe

# Regras aplicadas quando se define uma palavra-passe (por exemplo, no Admin
# ou com manage.py changepassword): não ser parecida com o nome, ter um
# comprimento mínimo, não ser comum nem só numérica.
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ---------------------------------------------------------------- Língua e hora

LANGUAGE_CODE = 'pt-pt'        # textos do Django (Admin, erros) em português
TIME_ZONE = 'Europe/Lisbon'    # hora apresentada nas páginas
USE_I18N = True                # ativa as traduções
USE_TZ = True                  # datas guardadas em UTC na base de dados


# ---------------------------------------------------------------- Ficheiros estáticos

# Ficheiros estáticos = CSS, JavaScript e imagens que não mudam (aqui, os do
# Admin; o Bootstrap e o Chart.js vêm de uma CDN).
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # destino do collectstatic (CSS do Admin)

# Tipo da chave primária (id) criada automaticamente em cada modelo.
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------- Autenticação

# Autenticação da interface web (UC1). Os valores são nomes de URLs
# (name=... nos ficheiros urls.py), não endereços.
LOGIN_URL = 'login'            # para onde o login_required envia quem não tem sessão
LOGIN_REDIRECT_URL = 'painel'  # para onde vai depois de entrar
LOGOUT_REDIRECT_URL = 'login'  # para onde vai depois de sair


# ---------------------------------------------------------------- API REST

# API REST (UC6): só pedidos com token válido.
# TokenAuthentication lê o cabeçalho "Authorization: Token <chave>" e
# IsAuthenticated recusa (401) quem não se autenticou.
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Documentação OpenAPI da API (drf-spectacular), vista com o Scalar em /api/docs/.
# O esquema só é servido a administradores com sessão iniciada.
SPECTACULAR_SETTINGS = {
    'TITLE': 'Monitorização IoT - API',
    'DESCRIPTION': 'Submissão de leituras pelos dispositivos (UC6).',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SERVE_AUTHENTICATION': ['rest_framework.authentication.SessionAuthentication'],
    'SERVE_PERMISSIONS': ['rest_framework.permissions.IsAdminUser'],
    # No servidor ave os URLs têm o prefixo /~1220847/rinte
    'SERVERS': [{'url': FORCE_SCRIPT_NAME}] if FORCE_SCRIPT_NAME else [],
}


# ---------------------------------------------------------------- Email

# Não se enviam emails: se o Django precisar (por exemplo, recuperar a
# palavra-passe), o texto é escrito na consola.
MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}
