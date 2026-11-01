"""
Modelos de dados (o M do padrão MTV).

Cada classe que herda de models.Model corresponde a uma tabela da base de
dados, e cada atributo do tipo models.XxxField a uma coluna. O Django
acrescenta sozinho a chave primária `id`. A partir desta descrição:
  - o comando makemigrations gera as migrações (sensores/migrations/), que o
    migrate aplica à base de dados, sem escrever SQL;
  - o ORM permite consultar e gravar com Python, por exemplo
    Sensor.objects.filter(ativo=True) ou leitura.save();
  - o Django Admin gera as listagens e os formulários de gestão (admin.py).

O primeiro argumento de cada campo (ex.: 'localização') é o nome apresentado
ao utilizador no Admin e nos formulários. Sem ele, o Django usaria o nome do
atributo, sem acentos ("Localizacao").
"""
from django.db import models


class Instalacao(models.Model):
    """Local onde estão os sensores (laboratório, sala, biblioteca...)."""

    # unique=True: não pode haver duas instalações com o mesmo nome
    nome = models.CharField('nome', max_length=100, unique=True)
    localizacao = models.CharField('localização', max_length=150)
    # blank=True: campo opcional nos formulários
    descricao = models.TextField('descrição', blank=True)

    class Meta:
        # Nomes apresentados no Admin e ordem por omissão das consultas
        verbose_name = 'instalação'
        verbose_name_plural = 'instalações'
        ordering = ['nome']

    def __str__(self):
        # Texto usado sempre que o objeto é mostrado (Admin, listas de escolha)
        return self.nome


class Sensor(models.Model):
    """Sensor de uma instalação, com os limites do funcionamento normal."""

    class Tipo(models.TextChoices):
        # valor guardado na base de dados, texto apresentado ao utilizador
        TEMPERATURA = 'temperatura', 'Temperatura'
        HUMIDADE = 'humidade', 'Humidade'
        CO2 = 'co2', 'CO₂'
        POTENCIA = 'potencia', 'Potência'

    # Chave estrangeira: cada sensor pertence a uma instalação (relação 1:N).
    # PROTECT: não se pode apagar uma instalação que ainda tem sensores.
    # related_name: a partir de uma instalação, instalacao.sensores.all()
    instalacao = models.ForeignKey(
        Instalacao, on_delete=models.PROTECT, related_name='sensores',
        verbose_name='instalação')
    nome = models.CharField('nome', max_length=100)
    # choices: só aceita os valores de Tipo e mostra uma lista de escolha
    tipo = models.CharField('tipo', max_length=20, choices=Tipo.choices)
    unidade = models.CharField('unidade', max_length=20)
    limite_min = models.FloatField('limite mínimo')
    limite_max = models.FloatField('limite máximo')
    # Um sensor inativo não aparece no painel e a API recusa as suas leituras
    ativo = models.BooleanField('ativo', default=True)

    class Meta:
        verbose_name = 'sensor'
        verbose_name_plural = 'sensores'
        ordering = ['instalacao__nome', 'nome']

    def __str__(self):
        return f'{self.nome} ({self.instalacao})'

    def fora_dos_limites(self, valor):
        """True se o valor estiver fora do intervalo normal (sensor em alerta)."""
        return valor < self.limite_min or valor > self.limite_max


class Leitura(models.Model):
    """Valor medido por um sensor num dado instante (enviado pela API)."""

    # CASCADE: ao remover um sensor, as suas leituras são removidas.
    # related_name: sensor.leituras.all() devolve as leituras do sensor
    sensor = models.ForeignKey(
        Sensor, on_delete=models.CASCADE, related_name='leituras',
        verbose_name='sensor')
    valor = models.FloatField('valor')
    # Guardado em UTC (USE_TZ=True) e apresentado na hora de Lisboa
    instante = models.DateTimeField('instante')

    class Meta:
        verbose_name = 'leitura'
        verbose_name_plural = 'leituras'
        ordering = ['-instante']   # mais recentes primeiro
        # Consultas de UC2 e UC3: filtram por sensor e ordenam por instante.
        # Sem este índice, cada consulta percorria toda a tabela
        # (1,9 s em vez de 7,5 ms com 10^6 leituras, Secção 4.2 do relatório).
        indexes = [models.Index(fields=['sensor', '-instante'],
                                name='leitura_sensor_instante')]

    def __str__(self):
        return f'{self.sensor.nome}: {self.valor} @ {self.instante:%Y-%m-%d %H:%M}'
