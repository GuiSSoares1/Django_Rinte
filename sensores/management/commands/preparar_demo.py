"""Cria instalações, sensores e utilizadores de demonstração.

Uso: python manage.py preparar_demo
Escreve simulador_config.json (token do dispositivo e lista de sensores),
lido pelo simulador e pelo script de ensaios.
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
        for nome, palavra_passe, admin in UTILIZADORES:
            utilizador, _ = User.objects.get_or_create(username=nome)
            if palavra_passe:
                utilizador.set_password(palavra_passe)
            else:
                utilizador.set_unusable_password()
            utilizador.is_staff = utilizador.is_superuser = admin
            utilizador.save()

        token, _ = Token.objects.get_or_create(user=User.objects.get(username='dispositivo'))

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

        caminho = settings.BASE_DIR / 'simulador_config.json'
        caminho.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(
            f'{Instalacao.objects.count()} instalações, {Sensor.objects.count()} sensores, '
            f'{len(UTILIZADORES)} utilizadores. Configuração em {caminho.name}.'))
