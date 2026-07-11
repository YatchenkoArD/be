# RUNBOOK — сервер Timeweb (prod + staging)

Схема: один сервер, три compose-проекта — `rumi-prod` (app+arq+redis, БД = managed PostgreSQL Timeweb), `rumi-staging` (то же + свой контейнер Postgres) и `rumi-edge` (один Caddy на 80/443, проксирует оба стека через внешнюю docker-сеть `edge`; staging закрыт basic_auth).

## 1. Первый запуск (один раз)

```bash
# --- под root ---
bash server/bootstrap.sh 'ssh-ed25519 AAAA... artem-rumi-deploy'
# НЕ закрывая сессию, из второго терминала проверить: ssh deploy@<host>

# --- дальше под deploy ---
cd /opt/rumi && git clone https://github.com/YatchenkoArD/be.git && cd be
```

### Секреты (блок 03 — старые скомпрометированы публичной git-историей!)
```bash
cp .env.example .env && cp .env.staging.example .env.staging
chmod 600 .env .env.staging
# в .env:  новый SECRET_KEY (openssl rand -hex 32), креды managed-БД из панели
#          Timeweb, DOMAIN (до домена — IP сервера), STAGING_BASIC_AUTH_HASH
#          (docker run --rm caddy:2-alpine caddy hash-password --plaintext '...';
#           в хеше КАЖДЫЙ $ удвоить до $$ — compose интерполирует $ в .env)
# в .env.staging:  свой SECRET_KEY и пароль БД (НЕ прод-значения)
# пароль managed-БД сменить в панели Timeweb (ротация)

# RS256-ключи: прод и staging — РАЗНЫЕ пары
python3 -m venv /tmp/genkeys && /tmp/genkeys/bin/pip install cryptography
SECRET_KEY=x POSTGRES_PASSWORD=x /tmp/genkeys/bin/python -m app.scripts.gen_keys   # → ./keys (прод)
mkdir keys-staging && mv keys/jwt_*.pem keys-staging/ && \
SECRET_KEY=x POSTGRES_PASSWORD=x /tmp/genkeys/bin/python -m app.scripts.gen_keys   # → ./keys ещё раз
```

### Первые миграции (блок 04)
Живая БД создавалась через `Base.metadata.create_all` — Alembic в ней не инициализирован. Если разворачиваем **существующую** прод-БД: разово
```bash
docker compose -p rumi-prod -f docker-compose.prod.yml run --rm app alembic stamp head
```
Для **чистой** БД ничего не нужно — `deploy.sh` сам прогонит `alembic upgrade head`.

### Запуск
```bash
./deploy.sh staging     # свой Postgres поднимется сам; сиды по желанию:
# docker compose -p rumi-staging -f docker-compose.staging.yml --env-file .env.staging \
#     run --rm app python -m app.scripts.seed_data
./deploy.sh prod
```

### Бэкапы (блок 04)
```bash
crontab -e   # под deploy:
0 3 * * * cd /opt/rumi/be && ./backup_to_s3.sh >> /var/log/db_backup.log 2>&1
```
S3-переменные — в `.env` (панель Timeweb → S3 VK Cloud). **Проверить restore**: скачать дамп, развернуть в staging-Postgres, убедиться, что приложение живо, — бэкап без проверенного restore не считается.

### Автодеплой staging из GitHub
В настройках репозитория → Secrets → Actions добавить `DEPLOY_HOST`, `DEPLOY_USER=deploy`, `DEPLOY_SSH_KEY` (приватная часть ключа). После этого каждый пуш в main обновляет staging сам.

## 2. Обычная работа

| Действие | Команда |
| --- | --- |
| Деплой прод | `./deploy.sh prod` (только руками, после проверки на staging) |
| Деплой staging руками | `./deploy.sh staging` |
| Откат | `docker tag rumi-app:prod-prev rumi-app:prod && ./deploy.sh prod --no-pull --no-build` |
| Логи | `docker logs -f rumi-prod-app` (или `-staging-`, `rumi-edge-caddy`) |
| Статус | `docker compose -p rumi-prod -f docker-compose.prod.yml ps` |
| Здоровье воркера | `docker exec rumi-prod-arq arq --check app.core.worker.WorkerSettings` |

## 3. Когда появится домен

1. DNS: A-записи `домен` и `staging.домен` → IP сервера.
2. В `.env`: `DOMAIN=домен`, `STAGING_DOMAIN=staging.домен`, `STAGING_TLS=<email>` (включает Let's Encrypt для staging; без него остаётся самоподписанный).
3. `docker compose -p rumi-edge -f docker-compose.edge.yml up -d --force-recreate` — Caddy сам получит сертификаты Let's Encrypt.

## 4. Когда юристы подключат SMSC (OTP)

В `.env` и `.env.staging`: `OTP_ENABLED=true`, `SMS_MODE=live`, `SMSC_LOGIN/PASSWORD/SENDER_ID`, убрать `OTP_DISABLED_ACK`. Перезапустить стеки.
