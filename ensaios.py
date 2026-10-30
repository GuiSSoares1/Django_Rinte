"""Ensaios de desempenho (Secção 4.2 do relatório).

Ensaio 1 - volume de dados: latência de cada caso de uso com 10^4, 10^5 e 10^6
leituras (RT1, RT2, RT3). Ensaio 2 - carga: o caso de uso de maior p95 com
1, 5, 10, 20 e 40 utilizadores simultâneos (RT4). Inclui ainda a comparação
da latência com e sem o índice (sensor, -instante).

Uso (com o ambiente virtual ativo, na pasta do projeto):
    python manage.py preparar_demo
    python ensaios.py
Os resultados ficam em resultados/ensaios_<data>.json.
"""
import argparse
import json
import math
import os
import platform
import sqlite3
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import django
import requests

RAIZ = Path(__file__).resolve().parent
PORTA = 8001
URL = f'http://127.0.0.1:{PORTA}'
UTILIZADOR, PALAVRA_PASSE = 'operador', 'rinte-operador-2026'
THREADS_SERVIDOR = 8
INDICE = 'leitura_sensor_instante'


def manage(*args):
    subprocess.run([sys.executable, 'manage.py', *args], cwd=RAIZ, check=True)


class Servidor:
    """Arranca o Waitress (WSGI) com DEBUG desligado e espera que responda."""

    def __enter__(self):
        ambiente = dict(os.environ, DJANGO_DEBUG='0')
        self.processo = subprocess.Popen(
            [sys.executable, '-m', 'waitress', f'--threads={THREADS_SERVIDOR}',
             f'--listen=127.0.0.1:{PORTA}', 'config.wsgi:application'],
            cwd=RAIZ, env=ambiente,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                requests.get(f'{URL}/login/', timeout=1)
                return self
            except requests.ConnectionError:
                time.sleep(0.5)
        raise RuntimeError('O servidor não arrancou.')

    def __exit__(self, *exc):
        self.processo.terminate()
        self.processo.wait()


def sessao_web():
    sessao = requests.Session()
    sessao.get(f'{URL}/login/')
    resposta = sessao.post(f'{URL}/login/', data={
        'username': UTILIZADOR, 'password': PALAVRA_PASSE,
        'csrfmiddlewaretoken': sessao.cookies['csrftoken']})
    if 'sessionid' not in sessao.cookies:
        raise RuntimeError(f'Login falhou (HTTP {resposta.status_code}).')
    return sessao


def sessao_api(token):
    sessao = requests.Session()
    sessao.headers['Authorization'] = f'Token {token}'
    return sessao


def lote_leituras(config, tamanho=10):
    sensores = config['dispositivos'][0]['sensores']
    agora = datetime.now(timezone.utc).isoformat()
    return [{'sensor': sensores[i % len(sensores)]['id'], 'valor': 21.0 + i,
             'instante': agora} for i in range(tamanho)]


def casos_de_uso(config):
    sensor = config['dispositivos'][0]['sensores'][0]['id']
    return {
        'UC2': ('web', 'GET', '/'),
        'UC3': ('web', 'GET', f'/sensores/{sensor}/'),
        'UC4': ('web', 'GET', f'/sensores/{sensor}/csv/'),
        'UC6': ('api', 'POST', '/api/leituras/'),
    }


def pedido(sessao, metodo, caminho, config):
    inicio = time.perf_counter()
    if metodo == 'GET':
        resposta = sessao.get(URL + caminho, timeout=60)
    else:
        resposta = sessao.post(URL + caminho, json=lote_leituras(config), timeout=60)
    duracao_ms = (time.perf_counter() - inicio) * 1000
    return duracao_ms, resposta.status_code in (200, 201)


def percentil(valores, p):
    ordenados = sorted(valores)
    return ordenados[max(0, math.ceil(p / 100 * len(ordenados)) - 1)]


def resumo(tempos, erros, duracao_total):
    total = len(tempos)
    return {
        'pedidos': total,
        'media_ms': round(statistics.mean(tempos), 2),
        'mediana_ms': round(statistics.median(tempos), 2),
        'p95_ms': round(percentil(tempos, 95), 2),
        'p99_ms': round(percentil(tempos, 99), 2),
        'debito_pedidos_s': round(total / duracao_total, 1),
        'erros_pct': round(100 * erros / total, 2),
    }


def nova_sessao(tipo, config):
    return sessao_web() if tipo == 'web' else sessao_api(config['token'])


def medir_sequencial(caso, config, n, aquecimento=20):
    tipo, metodo, caminho = caso
    sessao = nova_sessao(tipo, config)
    for _ in range(aquecimento):
        pedido(sessao, metodo, caminho, config)
    tempos, erros = [], 0
    inicio = time.perf_counter()
    for _ in range(n):
        duracao, ok = pedido(sessao, metodo, caminho, config)
        tempos.append(duracao)
        erros += not ok
    return resumo(tempos, erros, time.perf_counter() - inicio)


def medir_concorrente(caso, config, utilizadores, pedidos_por_utilizador):
    tipo, metodo, caminho = caso
    sessoes = [nova_sessao(tipo, config) for _ in range(utilizadores)]
    for sessao in sessoes:
        pedido(sessao, metodo, caminho, config)  # aquecimento

    def trabalho(sessao):
        return [pedido(sessao, metodo, caminho, config)
                for _ in range(pedidos_por_utilizador)]

    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=utilizadores) as executor:
        resultados = [r for lista in executor.map(trabalho, sessoes) for r in lista]
    duracao_total = time.perf_counter() - inicio
    tempos = [t for t, _ in resultados]
    erros = sum(1 for _, ok in resultados if not ok)
    return resumo(tempos, erros, duracao_total)


def alterar_indice(remover):
    from django.conf import settings
    with sqlite3.connect(settings.DATABASES['default']['NAME']) as ligacao:
        if remover:
            ligacao.execute(f'DROP INDEX IF EXISTS {INDICE}')
        else:
            ligacao.execute(f'CREATE INDEX IF NOT EXISTS {INDICE} '
                            'ON sensores_leitura (sensor_id, instante DESC)')


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--volumes', type=int, nargs='+',
                        default=[10_000, 100_000, 1_000_000])
    parser.add_argument('--n', type=int, default=200, help='pedidos por medição')
    parser.add_argument('--utilizadores', type=int, nargs='+', default=[1, 5, 10, 20, 40])
    parser.add_argument('--pedidos-por-utilizador', type=int, default=25)
    args = parser.parse_args()

    config = json.loads((RAIZ / 'simulador_config.json').read_text('utf-8'))
    casos = casos_de_uso(config)
    resultados = {
        'data': datetime.now().isoformat(timespec='seconds'),
        'ambiente': {'so': platform.platform(), 'cpu': platform.processor(),
                     'nucleos_logicos': os.cpu_count(),
                     'python': platform.python_version(),
                     'django': django.get_version(),
                     'servidor': f'Waitress, {THREADS_SERVIDOR} threads, DEBUG=False',
                     'pedidos_por_medicao': args.n},
        'volume': {}, 'indice': {}, 'carga': {},
    }

    # Ensaio 1: volume de dados
    for volume in args.volumes:
        print(f'\n== {volume} leituras ==')
        manage('gerar_leituras', str(volume))
        with Servidor():
            resultados['volume'][volume] = {}
            for nome, caso in casos.items():
                r = medir_sequencial(caso, config, args.n)
                resultados['volume'][volume][nome] = r
                print(f"{nome}: média {r['media_ms']} ms, p95 {r['p95_ms']} ms, "
                      f"erros {r['erros_pct']} %")

    maior = max(args.volumes)
    manage('gerar_leituras', str(maior))  # repõe o volume após os POST de UC6

    # Comparação com e sem o índice composto (maior volume)
    print('\n== índice (sensor, -instante) ==')
    for estado in ['sem_indice', 'com_indice']:
        alterar_indice(remover=(estado == 'sem_indice'))
        with Servidor():
            resultados['indice'][estado] = {
                nome: medir_sequencial(casos[nome], config, args.n)
                for nome in ['UC2', 'UC3']}
        print(estado, {k: v['p95_ms'] for k, v in resultados['indice'][estado].items()})

    # Ensaio 2: carga no caso de uso de maior p95 (RT4) e, como referência do
    # cenário IoT, na API de submissão de leituras (UC6)
    mais_lento = max(resultados['volume'][maior],
                     key=lambda nome: resultados['volume'][maior][nome]['p95_ms'])
    resultados['carga']['caso_mais_lento'] = mais_lento
    for nome in dict.fromkeys([mais_lento, 'UC6']):
        print(f'\n== carga em {nome} ==')
        resultados['carga'][nome] = {}
        with Servidor():
            for utilizadores in args.utilizadores:
                r = medir_concorrente(casos[nome], config, utilizadores,
                                      args.pedidos_por_utilizador)
                resultados['carga'][nome][utilizadores] = r
                print(f"{utilizadores} utilizadores: p95 {r['p95_ms']} ms, "
                      f"débito {r['debito_pedidos_s']} pedidos/s, erros {r['erros_pct']} %")

    pasta = RAIZ / 'resultados'
    pasta.mkdir(exist_ok=True)
    ficheiro = pasta / f"ensaios_{datetime.now():%Y%m%d_%H%M}.json"
    ficheiro.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), 'utf-8')
    print(f'\nResultados em {ficheiro}')


if __name__ == '__main__':
    main()
