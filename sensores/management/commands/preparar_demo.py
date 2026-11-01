"""Cria instalações, sensores e utilizadores de demonstração.

Uso: python manage.py preparar_demo
Escreve simulador_config.json (token do dispositivo e lista de sensores),
lido pelo simulador e pelo script de ensaios.

Comandos de gestão: qualquer ficheiro em <app>/management/commands/ com uma
classe Command passa a ser um comando do manage.py com o nome do ficheiro.
O Django chama o método handle().

Pode ser corrido várias vezes: get_or_create só cria o que ainda não existe
(não duplica) e repõe as palavras-passe de demonstração. Não apaga leituras.
"""
import json

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token

from sensores.dados_demo import INSTALACOES, PERFIS, SENSORES
from sensores.models import Instalacao, Sensor

# Credenciais só para a demonstração local (documentadas no README.md)
UTILIZADORES = [
    # (nome, palavra-passe, is_staff/is_superuser)
    ('admin', 'rinte-admin-2026', True),
    ('operador', 'rinte-operador-2026', False),
    # Conta técnica dos dispositivos: só se autentica com o token da API,
    # sem palavra-passe, pelo que não consegue entrar na interface web
    ('dispositivo', None, False),
]


class Command(BaseCommand):
    help = 'Cria os dados base da demonstração (instalações, sensores, utilizadores).'

    def handle(self, *args, **opcoes):
        # 1) Utilizadores
        for nome, palavra_passe, admin in UTILIZADORES:
            # get_or_create devolve (objeto, criado?): o _ ignora o segundo valor
            utilizador, _ = User.objects.get_or_create(username=nome)
            if palavra_passe:
                # set_password guarda só o hash (PBKDF2), nunca a palavra-passe em claro
                utilizador.set_password(palavra_passe)
            else:
                utilizador.set_unusable_password()
            # is_staff: entra no Admin; is_superuser: tem todas as permissões
            utilizador.is_staff = utilizador.is_superuser = admin
            utilizador.save()

        # 2) Token da API para a conta "dispositivo" (tabela do rest_framework.authtoken)
        token, _ = Token.objects.get_or_create(user=User.objects.get(username='dispositivo'))

        # 3) Instalações e sensores (dados_demo.py), guardando os ids para o simulador
        config = {'url': 'http://127.0.0.1:8000', 'token': token.key, 'dispositivos': []}
        for nome_inst, localizacao in INSTALACOES:
            instalacao, _ = Instalacao.objects.get_or_create(
                nome=nome_inst, defaults={'localizacao': localizacao})
            sensores = []
            for nome_sensor, tipo in SENSORES:
                unidade, minimo, maximo, base, amplitude = PERFIS[tipo]
                sensor, _ = Sensor.objects.get_or_create(
                    instalacao=instalacao, nome=nome_sensor,
                    defaults={'tipo': tipo, 'unidade': unidade,
                              'limite_min': minimo, 'limite_max': maximo})
                sensores.append({'id': sensor.pk, 'tipo': tipo})
            config['dispositivos'].append({'instalacao': nome_inst, 'sensores': sensores})

        # 4) Ficheiro de configuração dos scripts externos (não vai para o GitHub:
        #    contém o token, por isso está no .gitignore)
        caminho = settings.BASE_DIR / 'simulador_config.json'
        caminho.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(
            f'{Instalacao.objects.count()} instalações, {Sensor.objects.count()} sensores, '
            f'{len(UTILIZADORES)} utilizadores. Configuração em {caminho.name}.'))
