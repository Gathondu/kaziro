#!/bin/sh
set -eu

APP_DIR="${APP_DIR:-/opt/kaziro}"
SERVER_IP="${SERVER_IP:-167.233.100.112}"

cd "$APP_DIR"

SERVER_IP="$SERVER_IP" docker compose --env-file .env.production run --rm certbot renew --deploy-hook "true"
SERVER_IP="$SERVER_IP" docker compose --env-file .env.production exec -T caddy caddy reload --config /etc/caddy/Caddyfile
