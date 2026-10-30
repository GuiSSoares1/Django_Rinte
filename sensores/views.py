import csv
import io
from datetime import datetime, timedelta
from itertools import groupby

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, Max, Min, OuterRef, Subquery
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Leitura, Sensor
from .serializers import LeituraSerializer

MAX_PONTOS_GRAFICO = 2000
MAX_LINHAS_TABELA = 50
MAX_LEITURAS_POR_PEDIDO = 100


def _estado(sensor):
    if sensor.ultimo_valor is None:
        return 'sem_leituras'
    if sensor.fora_dos_limites(sensor.ultimo_valor):
        return 'alerta'
    return 'normal'


@login_required
def painel(request):
    """UC2: última leitura e estado de cada sensor, agrupados por instalação."""
    ultima = Leitura.objects.filter(sensor=OuterRef('pk')).order_by('-instante')
    # Uma única consulta SQL: sensores + instalação + última leitura (evita N+1)
    sensores = (Sensor.objects.filter(ativo=True)
                .select_related('instalacao')
                .annotate(ultimo_valor=Subquery(ultima.values('valor')[:1]),
                          ultimo_instante=Subquery(ultima.values('instante')[:1]))
                .order_by('instalacao__nome', 'nome'))

    for sensor in sensores:
        sensor.estado = _estado(sensor)
    instalacoes = [(instalacao, list(grupo))
                   for instalacao, grupo in groupby(sensores, key=lambda s: s.instalacao)]
    estados = [s.estado for s in sensores]

    return render(request, 'sensores/painel.html', {
        'instalacoes': instalacoes,
        'total_sensores': len(estados),
        'normais': estados.count('normal'),
        'em_alerta': estados.count('alerta'),
        'sem_leituras': estados.count('sem_leituras'),
    })


def _intervalo(request):
    """Lê ?inicio=&fim= (datetime-local); por omissão, as últimas 24 horas."""
    fim = timezone.now()
    inicio = fim - timedelta(hours=24)
    try:
        if request.GET.get('inicio'):
            inicio = timezone.make_aware(datetime.fromisoformat(request.GET['inicio']))
        if request.GET.get('fim'):
            fim = timezone.make_aware(datetime.fromisoformat(request.GET['fim']))
    except ValueError:
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
    sensor = get_object_or_404(Sensor.objects.select_related('instalacao'), pk=pk)
    inicio, fim = _intervalo(request)
    leituras = sensor.leituras.filter(instante__gte=inicio, instante__lte=fim)

    # Agregação feita pela base de dados, sem carregar as leituras em memória
    resumo = leituras.aggregate(minimo=Min('valor'), maximo=Max('valor'),
                                media=Avg('valor'), total=Count('id'))

    pontos = list(leituras.order_by('-instante')
                  .values_list('instante', 'valor')[:MAX_PONTOS_GRAFICO])[::-1]
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
        'query': request.GET.urlencode(),
    })


@login_required
def exportar_csv(request, pk):
    """UC4: leituras do mesmo intervalo do histórico, em formato CSV."""
    sensor = get_object_or_404(Sensor, pk=pk)
    inicio, fim = _intervalo(request)
    leituras = (sensor.leituras.filter(instante__gte=inicio, instante__lte=fim)
                .order_by('instante').values_list('instante', 'valor'))

    # Otimização: o ficheiro é montado em memória e escrito de uma só vez, e as
    # horas vão em UTC (ISO 8601), sem conversão de fuso horário linha a linha.
    conteudo = io.StringIO()
    escritor = csv.writer(conteudo, delimiter=';')
    escritor.writerow(['instante (UTC)', f'valor ({sensor.unidade})'])
    escritor.writerows((instante.isoformat(), valor) for instante, valor in leituras)

    resposta = HttpResponse(conteudo.getvalue(), content_type='text/csv; charset=utf-8')
    resposta['Content-Disposition'] = f'attachment; filename="sensor_{sensor.pk}.csv"'
    return resposta


class SubmeterLeiturasAPIView(APIView):
    """UC6: recebe uma ou várias leituras em JSON (autenticação por token)."""

    def post(self, request):
        dados = request.data
        if not isinstance(dados, list):
            dados = [dados]
        if not dados or len(dados) > MAX_LEITURAS_POR_PEDIDO:
            return Response(
                {'erro': f'Envie entre 1 e {MAX_LEITURAS_POR_PEDIDO} leituras.'},
                status=status.HTTP_400_BAD_REQUEST)

        serializer = LeituraSerializer(data=dados, many=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Tudo ou nada: o lote é guardado numa só transação e num só INSERT
        with transaction.atomic():
            Leitura.objects.bulk_create(
                Leitura(**dados_validos) for dados_validos in serializer.validated_data)
        return Response({'aceites': len(serializer.validated_data)},
                        status=status.HTTP_201_CREATED)
