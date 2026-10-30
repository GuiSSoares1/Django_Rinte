from django.contrib import admin

from .models import Instalacao, Leitura, Sensor


class SensorInline(admin.TabularInline):
    model = Sensor
    extra = 0


@admin.register(Instalacao)
class InstalacaoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'localizacao']
    search_fields = ['nome', 'localizacao']
    inlines = [SensorInline]


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'instalacao', 'tipo', 'unidade',
                    'limite_min', 'limite_max', 'ativo']
    list_filter = ['instalacao', 'tipo', 'ativo']
    search_fields = ['nome']
    list_editable = ['limite_min', 'limite_max', 'ativo']


@admin.register(Leitura)
class LeituraAdmin(admin.ModelAdmin):
    list_display = ['sensor', 'valor', 'instante']
    list_filter = ['sensor__instalacao', 'sensor']
    date_hierarchy = 'instante'
    list_select_related = ['sensor__instalacao']
    show_full_result_count = False  # evita COUNT(*) sobre 10^6 linhas
