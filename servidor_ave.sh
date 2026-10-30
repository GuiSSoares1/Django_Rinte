#!/bin/bash
# Arranca a plataforma no servidor ave.dee.isep.ipp.pt (Fedora 41, Python 3.13).
# O Waitress só escuta localmente; o Apache publica-o em
# http://ave.dee.isep.ipp.pt/~1220847/rinte/ (ver public_html/rinte/.htaccess).
#
# Uso: ./servidor_ave.sh          arranca em segundo plano (continua após sair do SSH)
#      ./servidor_ave.sh parar    para o servidor
#      ./servidor_ave.sh frente   arranca neste terminal (Ctrl+C para parar)
set -e
cd "$(dirname "$0")"
PORTA=8847
DADOS=~/rinte-dados
PID="$DADOS/servidor.pid"

if [ "$1" = "parar" ]; then
    [ -f "$PID" ] && kill "$(cat "$PID")" && rm -f "$PID" && echo "Servidor parado."
    exit 0
fi

# Base de dados e chave secreta fora da pasta do código, só legíveis pelo dono
mkdir -p "$DADOS"
chmod 700 "$DADOS"
if [ ! -f "$DADOS/secret_key" ]; then
    python3 -c "import secrets; print(secrets.token_urlsafe(50))" > "$DADOS/secret_key"
fi
export DJANGO_SECRET_KEY=$(cat "$DADOS/secret_key")
export DJANGO_DEBUG=0
export DJANGO_SCRIPT_NAME=/~1220847/rinte
export DJANGO_CSRF_TRUSTED_ORIGINS=https://ave.dee.isep.ipp.pt,http://ave.dee.isep.ipp.pt

source ~/venvs/rinte-app/bin/activate
COMANDO="waitress-serve --threads=8 --listen=127.0.0.1:$PORTA config.wsgi:application"
# O HTTPS do ave tem o certificado de outro domínio (neeti): usar HTTP
URL="http://ave.dee.isep.ipp.pt$DJANGO_SCRIPT_NAME/"

if [ "$1" = "frente" ]; then
    echo "Plataforma em $URL  (Ctrl+C para parar)"
    exec $COMANDO
fi
if [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; then
    echo "Já está a correr. Para parar: ./servidor_ave.sh parar"
    exit 0
fi
nohup $COMANDO >> "$DADOS/servidor.log" 2>&1 &
echo $! > "$PID"
echo "Plataforma em $URL  (registo em $DADOS/servidor.log)"
