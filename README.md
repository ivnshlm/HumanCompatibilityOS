# Human Compatibility OS

Операционная HR-платформа в философии **Fabrika Sredy** — «Среда важнее героизма».
Система оценивает **операционную совместимость и устойчивость среды**, а не «ценность человека».

> Принципы, зашитые в продукт: explainability-first, никаких автоматических решений,
> обязательная проверка человеком, явное согласие и аудит.

## MVP-клин

**Burnout & Environment Health Monitoring** — мониторинг давления выгорания, дефицита
восстановления, коммуникационной энтропии и устойчивости лидерства.

## Стек

| Слой      | Технологии                                              |
|-----------|---------------------------------------------------------|
| Backend   | FastAPI · SQLAlchemy 2.0 · psycopg3 · Pydantic          |
| База      | PostgreSQL (docker-compose), Alembic (позже)            |
| Frontend  | Next.js · Tailwind CSS                                   |
| Infra     | Docker Compose · Nginx · GitHub Actions CI              |

## Структура репозитория

```
backend/        FastAPI-приложение (app/: config, db, models, schemas, routers)
frontend/       Next.js дашборд (UI на русском)
docs/           ROADMAP и проектные документы
infra/          Nginx и деплой-конфиги
.github/        CI workflow
```

## Запуск (требуется Docker)

```bash
cp .env.example .env
docker compose up --build
# backend:  http://localhost:8000  (Swagger: /docs)
# frontend: http://localhost:3000
```

## Дорожная карта и статус

- [docs/ROADMAP.md](docs/ROADMAP.md) — пофазный план разработки.
- [docs/STATUS.md](docs/STATUS.md) — что сделано / что осталось + как продолжить на другом компе.
