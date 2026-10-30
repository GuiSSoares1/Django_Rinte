from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import Leitura, Sensor

# Tolerância para pequenas diferenças entre o relógio do dispositivo e o servidor
TOLERANCIA_RELOGIO = timedelta(minutes=1)


class LeituraSerializer(serializers.ModelSerializer):
    sensor = serializers.PrimaryKeyRelatedField(
        queryset=Sensor.objects.filter(ativo=True))

    class Meta:
        model = Leitura
        fields = ['sensor', 'valor', 'instante']

    def validate_instante(self, instante):
        if instante > timezone.now() + TOLERANCIA_RELOGIO:
            raise serializers.ValidationError('A hora de medição está no futuro.')
        return instante
