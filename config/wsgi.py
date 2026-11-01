"""
Ponto de entrada WSGI (Web Server Gateway Interface).

O WSGI é a norma (PEP 3333) que liga um servidor web em Python a uma
aplicação. O servidor (aqui, o Waitress) importa este módulo e, por cada
pedido HTTP, chama a variável `application`, que devolve a resposta.

Exemplo, usado no servidor_ave.sh e no ensaios.py:
    waitress-serve --listen=127.0.0.1:8847 config.wsgi:application
"""

import os

from django.core.wsgi import get_wsgi_application

# Indica ao Django qual é o ficheiro de configuração
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
