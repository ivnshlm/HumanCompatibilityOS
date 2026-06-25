# Деплой (тестовый стенд в интернете)

Однооригинная схема: один контейнер **Caddy** терминирует HTTPS и проксирует
`/api/*` → backend (FastAPI), всё остальное → frontend (Next.js). CORS не нужен,
сертификат Let's Encrypt выпускается автоматически.

```
Caddy (:80/:443, auto-HTTPS)
  ├── /api/*  → backend:8000   (префикс /api срезается)
  └── /*      → frontend:3000
```

## Что нужно

- VPS с публичным IP (Ubuntu 22.04+), Docker и docker compose.
- Открытые порты **80** и **443**.
- Домен **необязателен**: используем `sslip.io` — `<IP>.sslip.io` резолвится в IP
  без настройки DNS, и Caddy выпускает на него настоящий TLS-сертификат.

## Шаги

### 1. Установить Docker (если ещё нет)
```bash
curl -fsSL https://get.docker.com | sh
```

### 2. Получить код
```bash
git clone https://github.com/ivnshlm/HumanCompatibilityOS.git
cd HumanCompatibilityOS
```

### 3. Настроить окружение
```bash
cp .env.prod.example .env.prod
nano .env.prod
```
Заполнить (пусть `IP` — публичный адрес сервера):
- `HCOS_DOMAIN=<IP>.sslip.io`
- `PUBLIC_BASE_URL=https://<IP>.sslip.io`
- `POSTGRES_PASSWORD=<сильный пароль>`
- `JWT_SECRET=<openssl rand -hex 32>`

### 4. Запустить
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```
Первый запуск: сборка образов + выпуск сертификата (несколько минут).

### 5. Проверить
- Фронт: `https://<IP>.sslip.io`
- API health: `https://<IP>.sslip.io/api/health` → `{"status":"ok","database":true}`
- Swagger: `https://<IP>.sslip.io/api/docs`

### Завести администратора
Регистрация открыта (MVP), роль можно задать сразу:
```bash
curl -X POST https://<IP>.sslip.io/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"<пароль>","full_name":"Admin","role":"admin"}'
```

## Эксплуатация

```bash
# логи
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f
# обновление после git pull
git pull && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
# остановка
docker compose -f docker-compose.prod.yml --env-file .env.prod down
```

## Автодеплой (CI/CD)

Прод обновляется автоматически: после зелёного `CI` на ветке `main` запускается
workflow **`Deploy`** (`.github/workflows/deploy.yml`). Он собирает чистый снимок
коммита (`git archive`), заливает по SSH на сервер и пересобирает стек —
`.env.prod` на сервере не трогается.

Схема **push**: деплоит сама GitHub Actions, серверу не нужен доступ к репозиторию.
Нужны GitHub Secrets: `DEPLOY_SSH_KEY` (приватный ключ), `DEPLOY_HOST`,
`DEPLOY_USER`, `PUBLIC_BASE_URL`. Код на сервере живёт в `/opt/hcos`.

Ручной перезапуск деплоя — вкладка Actions → workflow «Deploy» → Run workflow
(или `gh workflow run Deploy`). Каждый деплой делает бэкап `.env.prod.bak.*` и
в конце проверяет `/api/health`.

## Миграции БД (Alembic)

Схема управляется Alembic. При старте контейнера `init_db` приводит БД к `head`:

- пустая БД → `upgrade head` создаёт всю схему;
- БД с уже существующими таблицами от старого `create_all` (до Alembic) → один раз
  «усыновляет» базовую ревизию через `stamp head`, не пересоздавая таблицы;
- дальше — обычный `upgrade head`, накатывает все новые ревизии.

Поэтому при деплое ничего вручную делать не нужно. Подробности и как создавать новые
миграции — в [`backend/MIGRATIONS.md`](../backend/MIGRATIONS.md).

## Бэкапы БД

Сервис `db-backup` в стеке делает `pg_dump` (тот же образ `postgres:16`, версии
совпадают): один дамп при старте/редеплое, далее каждые `BACKUP_INTERVAL_SECONDS`
(по умолчанию раз в сутки). Дампы — в `./backups` на хосте (`/opt/hcos/backups`),
старше `BACKUP_RETENTION_DAYS` (14) удаляются.

Шифрование at-rest: задайте `BACKUP_ENCRYPTION_PASSPHRASE` в `.env.prod`
(`openssl rand -hex 32`) — дампы пишутся как `*.sql.gz.enc` (AES-256). Без
парольной фразы — обычный gzip. **Храните фразу отдельно**: без неё зашифрованный
дамп не восстановить.

```bash
# посмотреть дампы
ls -lh /opt/hcos/backups
# восстановить (из /opt/hcos); для .enc сначала export BACKUP_ENCRYPTION_PASSPHRASE=...
./scripts/db-restore.sh backups/hcos_YYYYMMDD_HHMMSS.sql.gz
# забрать дамп с сервера к себе
scp -i <key> root@<host>:/opt/hcos/backups/hcos_*.sql.gz.enc .
```

> Дампы лежат на том же диске VPS — это защищает от порчи данных и плохих
> миграций, но не от потери диска. Для боевого стенда настройте регулярный вывоз
> дампов за пределы сервера (scp/rclone в другое хранилище).

## Замечания по безопасности (тестовый стенд)

- Схема БД управляется миграциями Alembic (накат при старте, см. выше).
- Бэкапы БД настроены (сервис `db-backup`, см. выше); для боевого — вывоз дампов off-box.
- **Шифрование диска at-rest** на этом VPS не настроено. Честно о вариантах:
  полнодисковый LUKS на работающем VPS требует переустановки/консоли и пароля при
  загрузке (ломает автоперезагрузку) либо keyfile на том же диске (слабая защита);
  пошифровать колонки приложения мешает агрегатам дашборда и логину по email. Самый
  практичный шаг уже сделан — шифрование дампов (самый «утекаемый» артефакт). Полный
  диск — только через шифрованный том на стороне провайдера при заказе сервера.
- Данные HR-чувствительные: для боевого стенда добавить ограничение регистрации
  и (при сплите фронт/бэк) выставить `CORS_ORIGINS`.
- Только Caddy слушает наружу; db/backend/frontend — во внутренней docker-сети.
