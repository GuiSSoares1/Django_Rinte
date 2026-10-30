"""Testes funcionais T01–T10 (rastreabilidade: casos de uso UC1–UC6 e RT5).

Executar com: python manage.py test sensores
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import Instalacao, Leitura, Sensor


class BaseTeste(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operador = User.objects.create_user('operador', password='pw-operador')
        cls.admin = User.objects.create_superuser('admin', password='pw-admin')
        cls.dispositivo = User.objects.create_user('dispositivo', password='pw-disp')
        cls.token = Token.objects.create(user=cls.dispositivo)

        cls.instalacao = Instalacao.objects.create(nome='Lab', localizacao='Ed. F')
        cls.sensor = Sensor.objects.create(
            instalacao=cls.instalacao, nome='Temperatura', tipo='temperatura',
            unidade='°C', limite_min=18, limite_max=26)
        agora = timezone.now()
        for minutos, valor in [(30, 20.0), (20, 22.0), (10, 24.0)]:
            Leitura.objects.create(sensor=cls.sensor, valor=valor,
                                   instante=agora - timedelta(minutes=minutos))

    def setUp(self):
        self.api = APIClient()

    def autenticar_api(self):
        self.api.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def leitura(self, **alteracoes):
        dados = {'sensor': self.sensor.pk, 'valor': 21.5,
                 'instante': timezone.now().isoformat()}
        dados.update(alteracoes)
        return dados


class T01AcessoAnonimo(BaseTeste):
    """UC1, RT5: páginas protegidas redirecionam para o login."""

    def test_redireciona_para_login(self):
        for url in [reverse('painel'), reverse('historico', args=[self.sensor.pk]),
                    reverse('exportar_csv', args=[self.sensor.pk])]:
            resposta = self.client.get(url)
            self.assertEqual(resposta.status_code, 302, url)
            self.assertTrue(resposta['Location'].startswith(reverse('login')), url)


class T02Autenticacao(BaseTeste):
    """UC1: credenciais válidas iniciam sessão; inválidas são rejeitadas."""

    def test_credenciais_validas(self):
        resposta = self.client.post(reverse('login'),
                                    {'username': 'operador', 'password': 'pw-operador'})
        self.assertRedirects(resposta, reverse('painel'))

    def test_credenciais_invalidas(self):
        resposta = self.client.post(reverse('login'),
                                    {'username': 'operador', 'password': 'errada'})
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)


class T03Painel(BaseTeste):
    """UC2: estados Normal, Em alerta e Sem leituras."""

    def test_estados(self):
        Sensor.objects.create(instalacao=self.instalacao, nome='Sem dados',
                              tipo='humidade', unidade='%', limite_min=30, limite_max=70)
        self.client.force_login(self.operador)
        resposta = self.client.get(reverse('painel'))
        self.assertContains(resposta, 'Normal')
        self.assertContains(resposta, 'Sem leituras')

        Leitura.objects.create(sensor=self.sensor, valor=30.0, instante=timezone.now())
        resposta = self.client.get(reverse('painel'))
        self.assertContains(resposta, 'Em alerta')
        self.assertEqual(resposta.context['em_alerta'], 1)


class T04Historico(BaseTeste):
    """UC3: filtro por intervalo e cálculo de mínimo, máximo e média."""

    def test_resumo(self):
        self.client.force_login(self.operador)
        resposta = self.client.get(reverse('historico', args=[self.sensor.pk]))
        resumo = resposta.context['resumo']
        self.assertEqual((resumo['minimo'], resumo['maximo'], resumo['total']),
                         (20.0, 24.0, 3))
        self.assertAlmostEqual(resumo['media'], 22.0)

    def test_filtro_intervalo(self):
        self.client.force_login(self.operador)
        inicio = timezone.localtime(timezone.now() - timedelta(minutes=25))
        resposta = self.client.get(reverse('historico', args=[self.sensor.pk]),
                                   {'inicio': inicio.strftime('%Y-%m-%dT%H:%M')})
        self.assertEqual(resposta.context['resumo']['total'], 2)


class T05ExportarCsv(BaseTeste):
    """UC4: CSV com cabeçalho e uma linha por leitura."""

    def test_csv(self):
        self.client.force_login(self.operador)
        resposta = self.client.get(reverse('exportar_csv', args=[self.sensor.pk]))
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta['Content-Type'].startswith('text/csv'))
        linhas = resposta.content.decode('utf-8').strip().splitlines()
        self.assertEqual(linhas[0], 'instante (UTC);valor (°C)')
        self.assertEqual(len(linhas), 4)


class T06Administracao(BaseTeste):
    """UC5, RT5: só o administrador acede ao Django Admin e cria registos."""

    def test_operador_sem_acesso(self):
        self.client.force_login(self.operador)
        resposta = self.client.get('/admin/')
        self.assertEqual(resposta.status_code, 302)

    def test_admin_cria_instalacao(self):
        self.client.force_login(self.admin)
        resposta = self.client.post('/admin/sensores/instalacao/add/', {
            'nome': 'Nova', 'localizacao': 'Ed. B', 'descricao': '',
            'sensores-TOTAL_FORMS': 0, 'sensores-INITIAL_FORMS': 0,
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Instalacao.objects.filter(nome='Nova').exists())


class T07ApiValida(BaseTeste):
    """UC6: lote válido com token devolve 201 e fica guardado."""

    def test_lote_valido(self):
        self.autenticar_api()
        lote = [self.leitura(valor=20 + i) for i in range(10)]
        resposta = self.api.post('/api/leituras/', lote, format='json')
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.data['aceites'], 10)
        self.assertEqual(Leitura.objects.count(), 13)


class T08ApiSemToken(BaseTeste):
    """UC6, RT5: sem token ou com token inválido devolve 401 e nada é guardado."""

    def test_sem_token(self):
        resposta = self.api.post('/api/leituras/', [self.leitura()], format='json')
        self.assertEqual(resposta.status_code, 401)

    def test_token_invalido(self):
        self.api.credentials(HTTP_AUTHORIZATION='Token 0000')
        resposta = self.api.post('/api/leituras/', [self.leitura()], format='json')
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(Leitura.objects.count(), 3)


class T09ApiInvalida(BaseTeste):
    """UC6: dados inválidos devolvem 400 e nenhuma leitura do lote é guardada."""

    def test_lote_invalido(self):
        self.autenticar_api()
        futuro = (timezone.now() + timedelta(hours=1)).isoformat()
        casos = [self.leitura(sensor=9999), self.leitura(valor='abc'),
                 self.leitura(instante=futuro)]
        for invalida in casos:
            resposta = self.api.post('/api/leituras/', [self.leitura(), invalida],
                                     format='json')
            self.assertEqual(resposta.status_code, 400, invalida)
        self.assertEqual(Leitura.objects.count(), 3)


class T10Csrf(BaseTeste):
    """RT5: formulário enviado sem token CSRF é rejeitado com 403."""

    def test_sem_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        resposta = cliente.post(reverse('login'),
                                {'username': 'operador', 'password': 'pw-operador'})
        self.assertEqual(resposta.status_code, 403)
