"""
Views da aplicação (o V do padrão MTV).

Uma view recebe o pedido HTTP (request), obtém os dados através dos modelos
(ORM) e devolve uma resposta:
  - páginas web (painel, historico): render() preenche um template com um
    dicionário de dados (o "contexto") e devolve HTML;
  - exportar_csv: devolve um ficheiro CSV;
  - API (SubmeterLeiturasAPIView): devolve JSON, com o Django REST Framework.

Os decorators por cima de cada função (@login_required, @staff_member_required)
são verificados antes de a view correr: se o utilizador não tiver sessão (ou
não for administrador), é enviado para a página de login.
"""
import csv
import io
from datetime import datetime, timedelta
from itertools import groupby

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, Max, Min, OuterRef, Subquery
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from drf_spectacular.utils import (OpenApiExample, OpenApiResponse, extend_schema,
                                   inline_serializer)
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Leitura, Sensor
from .serializers import LeituraSerializer

MAX_PONTOS_GRAFICO = 2000       # pontos enviados ao gráfico do histórico
MAX_LINHAS_TABELA = 50          # linhas da tabela "leituras mais recentes"
MAX_LEITURAS_POR_PEDIDO = 100   # limite de leituras num pedido à API


def _estado(sensor):
    """Estado apresentado no painel, a partir da última leitura do sensor."""
    if sensor.ultimo_valor is None:
        return 'sem_leituras'
    if sensor.fora_dos_limites(sensor.ultimo_valor):
        return 'alerta'
    return 'normal'


# ---------------------------------------------------------------- UC2 Painel

@login_required
def painel(request):
    """UC2: última leitura e estado de cada sensor, agrupados por instalação."""
    # Subconsulta: as leituras do sensor da linha atual (OuterRef('pk')),
    # da mais recente para a mais antiga
    ultima = Leitura.objects.filter(sensor=OuterRef('pk')).order_by('-instante')
    # Uma única consulta SQL: sensores + instalação + última leitura (evita N+1).
    # select_related junta a instalação (JOIN); annotate acrescenta a cada
    # sensor dois atributos calculados pela base de dados.
    sensores = (Sensor.objects.filter(ativo=True)
                .select_related('instalacao')
                .annotate(ultimo_valor=Subquery(ultima.values('valor')[:1]),
                          ultimo_instante=Subquery(ultima.values('instante')[:1]))
                .order_by('instalacao__nome', 'nome'))

    # A consulta só é executada aqui, quando se percorrem os sensores
    for sensor in sensores:
        sensor.estado = _estado(sensor)
    # Agrupa os sensores (já ordenados por instalação) em [(instalação, [sensores])]
    instalacoes = [(instalacao, list(grupo))
                   for instalacao, grupo in groupby(sensores, key=lambda s: s.instalacao)]
    estados = [s.estado for s in sensores]

    # O dicionário é o contexto: cada chave fica disponível no template
    return render(request, 'sensores/painel.html', {
        'instalacoes': instalacoes,
        'total_sensores': len(estados),
        'normais': estados.count('normal'),
        'em_alerta': estados.count('alerta'),
        'sem_leituras': estados.count('sem_leituras'),
    })


# ---------------------------------------------------------------- UC3 Histórico

def _intervalo(request):
    """Lê ?inicio=&fim= (datetime-local); por omissão, as últimas 24 horas."""
    fim = timezone.now()
    inicio = fim - timedelta(hours=24)
    try:
        # request.GET: parâmetros do endereço (?inicio=...&fim=...)
        if request.GET.get('inicio'):
            inicio = timezone.make_aware(datetime.fromisoformat(request.GET['inicio']))
        if request.GET.get('fim'):
            fim = timezone.make_aware(datetime.fromisoformat(request.GET['fim']))
    except ValueError:
        # messages: aviso mostrado no topo da página seguinte (ver base.html)
        messages.error(request, 'Data inválida. A mostrar as últimas 24 horas.')
        fim = timezone.now()
        return fim - timedelta(hours=24), fim
    if inicio >= fim:
        messages.error(request, 'O início tem de ser anterior ao fim. '
                                'A mostrar as últimas 24 horas.')
        fim = timezone.now()
        return fim - timedelta(hours=24), fim
    return inicio, fim


@login_required
def historico(request, pk):
    """UC3: leituras de um sensor num intervalo, com mínimo, máximo e média."""
    # Sensor com o id do endereço, ou página 404 se não existir
    sensor = get_object_or_404(Sensor.objects.select_related('instalacao'), pk=pk)
    inicio, fim = _intervalo(request)
    # __gte / __lte: maior ou igual / menor ou igual (WHERE instante BETWEEN ...)
    leituras = sensor.leituras.filter(instante__gte=inicio, instante__lte=fim)

    # Agregação feita pela base de dados, sem carregar as leituras em memória
    resumo = leituras.aggregate(minimo=Min('valor'), maximo=Max('valor'),
                                media=Avg('valor'), total=Count('id'))

    # As 2000 leituras mais recentes (usa o índice), depois invertidas para o
    # gráfico ficar da mais antiga para a mais recente
    pontos = list(leituras.order_by('-instante')
                  .values_list('instante', 'valor')[:MAX_PONTOS_GRAFICO])[::-1]
    # Dados do gráfico: o template coloca-os na página em JSON (json_script)
    # e o Chart.js desenha-os no browser
    grafico = {
        'etiquetas': [timezone.localtime(t).strftime('%d/%m %H:%M') for t, _ in pontos],
        'valores': [v for _, v in pontos],
        'limite_min': sensor.limite_min,
        'limite_max': sensor.limite_max,
    }

    return render(request, 'sensores/historico.html', {
        'sensor': sensor,
        'inicio': timezone.localtime(inicio),
        'fim': timezone.localtime(fim),
        'resumo': resumo,
        'grafico': grafico,
        'leituras': leituras.order_by('-instante')[:MAX_LINHAS_TABELA],
        'max_linhas': MAX_LINHAS_TABELA,
        # Parâmetros atuais, para o botão CSV exportar o mesmo intervalo
        'query': request.GET.urlencode(),
    })


# ---------------------------------------------------------------- UC4 Exportar CSV

@login_required
def exportar_csv(request, pk):
    """UC4: leituras do mesmo intervalo do histórico, em formato CSV."""
    sensor = get_object_or_404(Sensor, pk=pk)
    inicio, fim = _intervalo(request)
    # values_list: só as duas colunas, como tuplos (mais leve do que objetos)
    leituras = (sensor.leituras.filter(instante__gte=inicio, instante__lte=fim)
                .order_by('instante').values_list('instante', 'valor'))

    # Otimização: o ficheiro é montado em memória e escrito de uma só vez, e as
    # horas vão em UTC (ISO 8601), sem conversão de fuso horário linha a linha.
    conteudo = io.StringIO()
    escritor = csv.writer(conteudo, delimiter=';')   # ';' abre bem no Excel em PT
    escritor.writerow(['instante (UTC)', f'valor ({sensor.unidade})'])
    escritor.writerows((instante.isoformat(), valor) for instante, valor in leituras)

    resposta = HttpResponse(conteudo.getvalue(), content_type='text/csv; charset=utf-8')
    # attachment: o browser descarrega o ficheiro em vez de o mostrar
    resposta['Content-Disposition'] = f'attachment; filename="sensor_{sensor.pk}.csv"'
    return resposta


# ---------------------------------------------------------------- UC6 API

class SubmeterLeiturasAPIView(APIView):
    """UC6: recebe uma ou várias leituras em JSON (autenticação por token).

    A autenticação (TokenAuthentication) e a permissão (IsAuthenticated) vêm
    de REST_FRAMEWORK em settings.py: sem token válido, o DRF responde 401
    antes de chegar ao método post().
    """
    parser_classes = [JSONParser]   # só aceita corpo em JSON

    # @extend_schema não altera o funcionamento: só descreve a API no
    # documento OpenAPI (resumo, formato, respostas e exemplos do Scalar)
    @extend_schema(
        summary='Submeter leituras',
        description=('Recebe entre 1 e 100 leituras, guardadas numa só transação: se uma for '
                     'inválida, nenhuma é guardada. Se faltar o instante, usa-se a hora de '
                     'receção. Autenticação: cabeçalho `Authorization: Token <chave>`.'),
        request=LeituraSerializer(many=True),
        responses={
            201: inline_serializer('LeiturasAceites', {'aceites': serializers.IntegerField()}),
            400: OpenApiResponse(description='Leitura inválida (sensor inexistente, valor não '
                                             'numérico ou hora no futuro); nada é guardado.'),
            401: OpenApiResponse(description='Token em falta ou inválido.'),
        },
        # Cada exemplo é uma leitura; o drf-spectacular coloca-a dentro da lista
        examples=[
            OpenApiExample('Leitura normal', value={'sensor': 21, 'valor': 22.5},
                           request_only=True),
            OpenApiExample('Leitura fora dos limites', value={'sensor': 21, 'valor': 30},
                           request_only=True),
            OpenApiExample('Com hora de medição', request_only=True,
                           value={'sensor': 1, 'valor': 22.4,
                                  'instante': '2026-10-31T12:00:00Z'}),
            OpenApiExample('Sensor inexistente', value={'sensor': 99999, 'valor': 22},
                           request_only=True),
        ],
    )
    def post(self, request):
        # request.data: o corpo JSON já convertido para Python (lista ou dicionário)
        dados = request.data
        if not isinstance(dados, list):
            dados = [dados]   # aceita também uma única leitura, sem lista
        if not dados or len(dados) > MAX_LEITURAS_POR_PEDIDO:
            return Response(
                {'erro': f'Envie entre 1 e {MAX_LEITURAS_POR_PEDIDO} leituras.'},
                status=status.HTTP_400_BAD_REQUEST)

        # many=True: valida cada elemento da lista com o LeituraSerializer
        serializer = LeituraSerializer(data=dados, many=True)
        if not serializer.is_valid():
            # Erros por posição na lista, ex.: {"1": {"sensor": ["Pk inválido..."]}}
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Tudo ou nada: o lote é guardado numa só transação e num só INSERT
        with transaction.atomic():
            Leitura.objects.bulk_create(
                Leitura(**dados_validos) for dados_validos in serializer.validated_data)
        return Response({'aceites': len(serializer.validated_data)},
                        status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------- Documentação da API

@staff_member_required
def api_docs(request):
    """Documentação interativa da API (Scalar), para testar pedidos no browser."""
    # Token do dispositivo de demonstração, pré-preenchido para os pedidos de teste
    token = Token.objects.filter(user__username='dispositivo').values_list('key', flat=True).first()
    return render(request, 'sensores/api_docs.html', {'token': token})
