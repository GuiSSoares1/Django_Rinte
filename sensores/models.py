from django.db import models


class Instalacao(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    localizacao = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)

    class Meta:
        verbose_name = 'instalação'
        verbose_name_plural = 'instalações'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Sensor(models.Model):
    class Tipo(models.TextChoices):
        TEMPERATURA = 'temperatura', 'Temperatura'
        HUMIDADE = 'humidade', 'Humidade'
        CO2 = 'co2', 'CO₂'
        POTENCIA = 'potencia', 'Potência'

    # PROTECT: não se pode apagar uma instalação que ainda tem sensores
    instalacao = models.ForeignKey(
        Instalacao, on_delete=models.PROTECT, related_name='sensores')
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    unidade = models.CharField(max_length=20)
    limite_min = models.FloatField()
    limite_max = models.FloatField()
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'sensor'
        verbose_name_plural = 'sensores'
        ordering = ['instalacao__nome', 'nome']

    def __str__(self):
        return f'{self.nome} ({self.instalacao})'

    def fora_dos_limites(self, valor):
        return valor < self.limite_min or valor > self.limite_max


class Leitura(models.Model):
    # CASCADE: ao remover um sensor, as suas leituras são removidas
    sensor = models.ForeignKey(
        Sensor, on_delete=models.CASCADE, related_name='leituras')
    valor = models.FloatField()
    instante = models.DateTimeField()

    class Meta:
        verbose_name = 'leitura'
        verbose_name_plural = 'leituras'
        ordering = ['-instante']
        # Consultas de UC2 e UC3: filtram por sensor e ordenam por instante
        indexes = [models.Index(fields=['sensor', '-instante'],
                                name='leitura_sensor_instante')]

    def __str__(self):
        return f'{self.sensor.nome}: {self.valor} @ {self.instante:%Y-%m-%d %H:%M}'
