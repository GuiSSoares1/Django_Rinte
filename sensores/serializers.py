"""
Serializers do Django REST Framework (usados pela API, UC6).

Um serializer faz duas coisas:
  - valida os dados recebidos em JSON (campos obrigatórios, tipos, regras);
  - converte-os em dados Python prontos a gravar (serializer.validated_data).
Se algo falhar, serializer.errors diz o campo e o motivo, que a view devolve
ao dispositivo com o código 400.
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import Leitura, Sensor

# Tolerância para pequenas diferenças entre o relógio do dispositivo e o servidor
TOLERANCIA_RELOGIO = timedelta(minutes=1)


class LeituraSerializer(serializers.ModelSerializer):
    """Uma leitura: {"sensor": <id>, "valor": <número>, "instante": <opcional>}."""

    # ModelSerializer cria os campos a partir do modelo Leitura (ver Meta).
    # Os dois campos abaixo substituem os gerados, para acrescentar regras:

    # O id tem de corresponder a um sensor existente E ativo; caso contrário,
    # erro "Pk inválido ... objeto não existe"
    sensor = serializers.PrimaryKeyRelatedField(
        queryset=Sensor.objects.filter(ativo=True))
    # Se o dispositivo não indicar a hora de medição, usa-se a hora de receção
    instante = serializers.DateTimeField(default=timezone.now)

    class Meta:
        model = Leitura
        fields = ['sensor', 'valor', 'instante']   # valor: FloatField -> tem de ser número

    def validate_instante(self, instante):
        # Método validate_<campo>: o DRF chama-o automaticamente para esse campo
        if instante > timezone.now() + TOLERANCIA_RELOGIO:
            raise serializers.ValidationError('A hora de medição está no futuro.')
        return instante
