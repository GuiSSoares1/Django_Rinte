"""
Ponto de entrada ASGI (Asynchronous Server Gateway Interface).

É a alternativa assíncrona ao WSGI, necessária para WebSockets (por exemplo,
com o Django Channels). Este projeto não a usa: corre com o Waitress, que é
WSGI. O ficheiro é criado pelo startproject e fica para uma evolução futura
(painel atualizado em tempo real).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
