"""
Configuração do Django Admin (UC5: gerir instalações, sensores e leituras).

O Django Admin gera sozinho as páginas de listagem, pesquisa, criação,
edição e remoção de cada modelo registado. Aqui só se indica, para cada
modelo, o que se quer ver. Os utilizadores, grupos e tokens não aparecem
neste ficheiro porque o Django e o Django REST Framework já os registam.

Só os utilizadores com is_staff=True (Administradores) entram em /admin/.
"""
from django.contrib import admin

from .models import Instalacao, Leitura, Sensor


class SensorInline(admin.TabularInline):
    """Tabela de sensores dentro da página de cada instalação."""
    model = Sensor
    extra = 0   # não mostra linhas vazias (há o botão "Adicionar outro Sensor")


# @admin.register(Modelo) regista o modelo no Admin com a configuração da classe
@admin.register(Instalacao)
class InstalacaoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'localizacao']     # colunas da listagem
    search_fields = ['nome', 'localizacao']    # caixa de pesquisa
    inlines = [SensorInline]                   # sensores editáveis na mesma página


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ['id', 'nome', 'instalacao', 'tipo', 'unidade',
                    'limite_min', 'limite_max', 'ativo']
    list_filter = ['instalacao', 'tipo', 'ativo']        # filtros na barra lateral
    search_fields = ['nome']
    # Colunas editáveis diretamente na listagem (botão "Gravar" no fundo)
    list_editable = ['limite_min', 'limite_max', 'ativo']


@admin.register(Leitura)
class LeituraAdmin(admin.ModelAdmin):
    list_display = ['sensor', 'valor', 'instante']
    list_filter = ['sensor__instalacao', 'sensor']       # __ segue a chave estrangeira
    date_hierarchy = 'instante'                          # navegação por ano/mês/dia
    # Obtém o sensor e a instalação na mesma consulta (JOIN), em vez de uma
    # consulta extra por cada linha da listagem
    list_select_related = ['sensor__instalacao']
    show_full_result_count = False  # evita COUNT(*) sobre 10^6 linhas
