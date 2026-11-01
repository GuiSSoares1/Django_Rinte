"""Gera leituras sintéticas (uma por minuto e por sensor, para trás no tempo).

Uso: python manage.py gerar_leituras 1000000
Apaga as leituras existentes e cria exatamente N, repartidas pelos sensores
ativos. Usado para os ensaios de volume de dados (10^4, 10^5 e 10^6).

Ao contrário do simulador, não passa pela API: grava diretamente na base de
dados, em lotes, o que permite criar um milhão de leituras em poucos minutos.
Com a mesma semente (--semente), gera sempre os mesmos valores.
"""
import math
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from sensores.dados_demo import PERFIS
from sensores.models import Leitura, Sensor

LOTE = 20_000   # leituras acumuladas em memória antes de cada gravação


def valor_sintetico(tipo, instante, rng):
    """Variação diária (sinusoide) + ruído; ~1 % dos valores fora dos limites."""
    _, minimo, maximo, base, amplitude = PERFIS[tipo]
    hora = instante.hour + instante.minute / 60
    # Sinusoide com período de 24 h: valor base ± amplitude ao longo do dia
    valor = base + amplitude * math.sin((hora - 9) / 24 * 2 * math.pi)
    valor += rng.gauss(0, amplitude * 0.08)   # ruído de medição
    if rng.random() < 0.01:
        # 1 % das leituras: acima do máximo ou abaixo do mínimo (alertas)
        valor = maximo * 1.1 if rng.random() < 0.5 else minimo * 0.9 - 1
    return round(valor, 2)


class Command(BaseCommand):
    help = 'Substitui as leituras por N leituras sintéticas.'

    def add_arguments(self, parser):
        # Argumentos da linha de comandos: manage.py gerar_leituras <total> [--semente N]
        parser.add_argument('total', type=int)
        parser.add_argument('--semente', type=int, default=42)

    def handle(self, *args, total, semente, **opcoes):
        rng = random.Random(semente)   # gerador próprio: resultados reprodutíveis
        sensores = list(Sensor.objects.filter(ativo=True))
        if not sensores:
            self.stderr.write('Não há sensores. Corra primeiro: manage.py preparar_demo')
            return

        Leitura.objects.all().delete()
        # Ex.: 10 000 leituras / 21 sensores = 477 minutos (as últimas ~8 horas)
        minutos = math.ceil(total / len(sensores))
        agora = timezone.now().replace(second=0, microsecond=0)
        lote, criadas = [], 0

        # Do minuto mais antigo até agora: uma leitura por sensor em cada minuto
        for i in range(minutos):
            instante = agora - timedelta(minutes=minutos - 1 - i)
            for sensor in sensores:
                if criadas + len(lote) >= total:   # para exatamente em N
                    break
                lote.append(Leitura(sensor=sensor, instante=instante,
                                    valor=valor_sintetico(sensor.tipo, instante, rng)))
            if len(lote) >= LOTE or criadas + len(lote) >= total:
                # Grava o lote numa transação, em INSERTs de 2000 linhas
                with transaction.atomic():
                    Leitura.objects.bulk_create(lote, batch_size=2000)
                criadas += len(lote)
                lote = []
                # \r volta ao início da linha: progresso na mesma linha do terminal
                self.stdout.write(f'\r{criadas}/{total}', ending='')

        self.stdout.write(self.style.SUCCESS(
            f'\n{criadas} leituras criadas ({minutos} minutos x {len(sensores)} sensores).'))
