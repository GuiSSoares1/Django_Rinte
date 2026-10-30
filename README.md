# Plataforma de monitorização de sensores IoT (Django)

Caso de estudo do trabalho de RINTE (MEEC/ISEP) sobre o Django.

## Funcionalidades (casos de uso)

| Caso de uso | Onde |
|---|---|
| UC1 Autenticar-se | `/login/` |
| UC2 Consultar painel | `/` |
| UC3 Histórico de um sensor | `/sensores/<id>/` |
| UC4 Exportar CSV | `/sensores/<id>/csv/` |
| UC5 Gerir instalações e sensores | `/admin/` |
| UC6 Submeter leituras (API) | `POST /api/leituras/` (cabeçalho `Authorization: Token <chave>`) |

## Instalação (Windows)

```
python -m venv C:\Users\<utilizador>\venvs\rinte-app
C:\Users\<utilizador>\venvs\rinte-app\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py preparar_demo        # instalações, sensores, utilizadores
python manage.py gerar_leituras 10000 # leituras de exemplo
python manage.py runserver
```

Abrir http://127.0.0.1:8000/.

## Utilizadores de demonstração (só para uso local)

| Utilizador | Palavra-passe | Perfil |
|---|---|---|
| `admin` | `rinte-admin-2026` | Administrador (acede a `/admin/`) |
| `operador` | `rinte-operador-2026` | Operador |
| `dispositivo` | (nenhuma, não entra no site) | Dono do *token* da API (em `simulador_config.json`) |

## Servidor Linux com Apache

```
python3 -m venv ~/venvs/rinte-app && source ~/venvs/rinte-app/bin/activate
cd ~/app-monitorizacao && pip install -r requirements.txt
mkdir -p ~/rinte-dados && chmod 700 ~/rinte-dados
python manage.py migrate && python manage.py collectstatic --noinput
python manage.py preparar_demo && python manage.py gerar_leituras 10000
python manage.py changepassword admin   # e operador
mkdir -p ~/public_html/rinte && cp ave_htaccess ~/public_html/rinte/.htaccess
./servidor_ave.sh                       # ./servidor_ave.sh parar para desligar
```

O Apache publica a plataforma na pasta `public_html/rinte/` do utilizador e
passa os pedidos ao Waitress, que só escuta em 127.0.0.1:8847.

Num servidor acessível a terceiros convém trocar as palavras-passe de
demonstração acima. Correr de novo `preparar_demo` repõe-nas.

## Simulador de dispositivos

Com o servidor ligado, noutro terminal:

```
python simulador.py --intervalo 5 --prob-alerta 0.05
```

Cada instalação envia a cada 5 s as leituras dos seus 5 sensores; ~5 % dos
valores ficam fora dos limites, para os sensores aparecerem "Em alerta".

## Testes

```
python manage.py test sensores
```

Testes T01–T10 (UC1–UC6 e segurança RT5).

## Ensaios de desempenho

```
python manage.py gerar_leituras 1000000
waitress-serve --threads=8 --listen=127.0.0.1:8000 config.wsgi:application
python ensaios.py
```
