"""Simula os dispositivos IoT: cada instalação envia, periodicamente, as leituras
dos seus sensores para a API (POST /api/leituras/, autenticação por token).

Uso: python simulador.py [--intervalo 5] [--prob-alerta 0.05] [--ciclos 0]
Requer simulador_config.json (criado por: python manage.py preparar_demo).
"""
import argparse
import json
import math
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

PERFIS = {  # tipo: (limite_min, limite_max, valor_base, amplitude)
    'temperatura': (18, 26, 22, 2.5),
    'humidade': (30, 70, 50, 10),
    'co2': (400, 1000, 650, 200),
    'potencia': (0, 3000, 1500, 800),
}


def gerar_valor(tipo, prob_alerta):
    minimo, maximo, base, amplitude = PERFIS[tipo]
    if random.random() < prob_alerta:
        return round(maximo * random.uniform(1.05, 1.2), 2)
    hora = datetime.now().hour + datetime.now().minute / 60
    valor = base + amplitude * math.sin((hora - 9) / 24 * 2 * math.pi)
    return round(valor + random.gauss(0, amplitude * 0.08), 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--intervalo', type=float, default=5, help='segundos entre envios')
    parser.add_argument('--prob-alerta', type=float, default=0.05)
    parser.add_argument('--ciclos', type=int, default=0, help='0 = sem fim')
    parser.add_argument('--url', help='endereço do servidor (por omissão, o da configuração)')
    args = parser.parse_args()

    config = json.loads(Path(__file__).with_name('simulador_config.json').read_text('utf-8'))
    sessao = requests.Session()
    sessao.headers['Authorization'] = f"Token {config['token']}"
    url = f"{args.url or config['url']}/api/leituras/"

    ciclo = 0
    while args.ciclos == 0 or ciclo < args.ciclos:
        ciclo += 1
        agora = datetime.now(timezone.utc).isoformat()
        for dispositivo in config['dispositivos']:
            leituras = [{'sensor': s['id'], 'valor': gerar_valor(s['tipo'], args.prob_alerta),
                         'instante': agora} for s in dispositivo['sensores']]
            try:
                resposta = sessao.post(url, json=leituras, timeout=10)
                print(f"[{ciclo}] {dispositivo['instalacao']}: HTTP {resposta.status_code}")
            except requests.ConnectionError:
                print(f"[{ciclo}] servidor indisponível em {url}; nova tentativa no próximo ciclo")
                break
        time.sleep(args.intervalo)


if __name__ == '__main__':
    main()
