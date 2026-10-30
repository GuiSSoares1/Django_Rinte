"""Instalações e sensores usados na demonstração, no simulador e nos ensaios."""

# tipo: (unidade, limite_min, limite_max, valor_base, amplitude_diaria)
PERFIS = {
    'temperatura': ('°C', 18, 26, 22, 2.5),
    'humidade': ('%', 30, 70, 50, 10),
    'co2': ('ppm', 400, 1000, 650, 200),
    'potencia': ('W', 0, 3000, 1500, 800),
}

INSTALACOES = [
    ('Laboratório de Redes', 'Edifício F, piso 2'),
    ('Sala B201', 'Edifício B, piso 2'),
    ('Sala Técnica', 'Edifício I, piso -1'),
    ('Biblioteca', 'Edifício A, piso 0'),
]

SENSORES = [
    ('Temperatura ambiente', 'temperatura'),
    ('Temperatura junto à janela', 'temperatura'),
    ('Humidade relativa', 'humidade'),
    ('Concentração de CO₂', 'co2'),
    ('Potência consumida', 'potencia'),
]
