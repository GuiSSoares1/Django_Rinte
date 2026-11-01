#!/usr/bin/env python
"""
Utilitário de linha de comandos do Django.

Todos os comandos do projeto passam por aqui, por exemplo:
    python manage.py runserver        servidor de desenvolvimento
    python manage.py migrate          cria/atualiza as tabelas da base de dados
    python manage.py test sensores    corre os testes automáticos
    python manage.py preparar_demo    comando nosso (sensores/management/commands/)
"""
import os
import sys


def main():
    # Indica ao Django qual é o ficheiro de configuração
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
