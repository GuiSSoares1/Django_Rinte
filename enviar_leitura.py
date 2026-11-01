"""Envia uma única leitura para a API, como faria um dispositivo (útil na demonstração).

Uso: python enviar_leitura.py <id do sensor> <valor> [--sem-token] [--url http://127.0.0.1:8000]
O token é lido de simulador_config.json (criado por: python manage.py preparar_demo).

Exemplos (ver DEMO.md):
    python enviar_leitura.py 21 22.5          -> 201 Created
    python enviar_leitura.py 21 30            -> 201, e o sensor fica "Em alerta"
    python enviar_leitura.py 99999 22         -> 400 Bad Request (sensor inexistente)
    python enviar_leitura.py 21 22 --sem-token -> 401 Unauthorized
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sensor', type=int, help='id do sensor (coluna ID no Django Admin)')
    parser.add_argument('valor', type=float)
    parser.add_argument('--sem-token', action='store_true', help='envia sem autenticação (espera 401)')
    parser.add_argument('--url', help='endereço do servidor (por omissão, o da configuração)')
    args = parser.parse_args()

    config = json.loads(Path(__file__).with_name('simulador_config.json').read_text('utf-8'))
    url = f"{args.url or config['url']}/api/leituras/"
    # Corpo do pedido: lista com uma leitura, hora atual em UTC (ISO 8601)
    leitura = [{'sensor': args.sensor, 'valor': args.valor,
                'instante': datetime.now(timezone.utc).isoformat()}]
    # Cabeçalho de autenticação da API; com --sem-token não é enviado
    cabecalhos = {} if args.sem_token else {'Authorization': f"Token {config['token']}"}

    # Mostra o pedido e a resposta, para se ver o que circula na rede
    print(f'POST {url}')
    print(json.dumps(leitura, indent=2, ensure_ascii=False))
    resposta = requests.post(url, json=leitura, headers=cabecalhos, timeout=10)
    print(f'-> HTTP {resposta.status_code} {resposta.reason}')
    print(json.dumps(resposta.json(), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
