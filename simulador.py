"""Simula os dispositivos IoT: cada instalação envia, periodicamente, as leituras
dos seus sensores para a API (POST /api/leituras/, autenticação por token).

Uso: python simulador.py [--intervalo 5] [--prob-alerta 0.05] [--ciclos 0]
Requer simulador_config.json (criado por: python manage.py preparar_demo).

Não faz parte do Django: é um cliente externo que fala com a plataforma só
por HTTP, tal como um dispositivo real. Corre até ser interrompido (Ctrl+C).
Destina-se à demonstração e não foi usado nos ensaios de desempenho.
"""
import argparse
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

LIMITES = {  # tipo: (limite mínimo, limite máximo)
    'temperatura': (18, 26),
    'humidade': (30, 70),
    'co2': (400, 1000),
    'potencia': (0, 3000),
}


def gerar_valor(tipo, prob_alerta):
    """Valor aleatório entre os limites; às vezes 10 % acima do máximo (alerta)."""
    minimo, maximo = LIMITES[tipo]
    if random.random() < prob_alerta:
        return round(maximo * 1.1, 2)
    return round(random.uniform(minimo, maximo), 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--intervalo', type=float, default=5, help='segundos entre envios')
    parser.add_argument('--prob-alerta', type=float, default=0.05)
    parser.add_argument('--ciclos', type=int, default=0, help='0 = sem fim')
    parser.add_argument('--url', help='endereço do servidor (por omissão, o da configuração)')
    args = parser.parse_args()

    # Token e ids dos sensores, escritos pelo preparar_demo
    config = json.loads(Path(__file__).with_name('simulador_config.json').read_text('utf-8'))
    # Uma sessão HTTP reutiliza a ligação e envia o token em todos os pedidos
    sessao = requests.Session()
    sessao.headers['Authorization'] = f"Token {config['token']}"
    url = f"{args.url or config['url']}/api/leituras/"

    ciclo = 0
    while args.ciclos == 0 or ciclo < args.ciclos:   # --ciclos 0: sem fim
        ciclo += 1
        agora = datetime.now(timezone.utc).isoformat()
        # Cada instalação é um "dispositivo": um pedido com as leituras dos seus 5 sensores
        for dispositivo in config['dispositivos']:
            leituras = [{'sensor': s['id'], 'valor': gerar_valor(s['tipo'], args.prob_alerta),
                         'instante': agora} for s in dispositivo['sensores']]
            try:
                # json=...: o requests converte a lista em JSON e põe o Content-Type
                resposta = sessao.post(url, json=leituras, timeout=10)
                print(f"[{ciclo}] {dispositivo['instalacao']}: HTTP {resposta.status_code}")
            except requests.ConnectionError:
                print(f"[{ciclo}] servidor indisponível em {url}; nova tentativa no próximo ciclo")
                break
        time.sleep(args.intervalo)


if __name__ == '__main__':
    main()
