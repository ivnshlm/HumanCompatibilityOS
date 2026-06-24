# Миграции БД (Alembic)

Схема Postgres управляется [Alembic](https://alembic.sqlalchemy.org). Источник
истины — ORM-модели в `app/models.py`; миграции в `alembic/versions/` фиксируют
каждое изменение схемы явно.

## Как это работает на старте

`app.db.run_migrations()` вызывается из `init_db()` при запуске приложения и сам
выбирает действие:

| Состояние БД | Действие |
|---|---|
| Пустая БД | `upgrade head` — создаёт всю схему |
| Таблицы есть, но нет `alembic_version` (старый `create_all`-деплой) | `stamp head` — «усыновляет» базовую ревизию, ничего не пересоздавая |
| `alembic_version` уже есть | `upgrade head` — накатывает новые ревизии |

Поэтому при деплое (CI/CD) ничего вручную делать не нужно — миграции применяются
сами. URL БД берётся из `DATABASE_URL` (тот же DSN, что у приложения).

## Создать новую миграцию

После изменения моделей в `app/models.py`:

```bash
cd backend
# автогенерация diff между моделями и текущей БД
DATABASE_URL=postgresql+psycopg://hcos:hcos@localhost:5432/hcos \
  python -m alembic revision --autogenerate -m "краткое описание"
```

Затем **обязательно просмотрите** сгенерированный файл в `alembic/versions/`:
автогенерация не видит переименований (покажет drop+add) и не всегда верно
угадывает `server_default`/типы. Поправьте при необходимости.

Применить локально:

```bash
DATABASE_URL=... python -m alembic upgrade head
```

## Полезные команды

```bash
python -m alembic current            # текущая ревизия БД
python -m alembic history            # история ревизий
python -m alembic upgrade head       # накатить всё
python -m alembic downgrade -1       # откатить одну ревизию
python -m alembic upgrade head --sql # показать DDL без выполнения (offline)
```

## Замечания

- Базовая ревизия (`*_initial_schema`) описывает все 10 доменных таблиц и
  повторяет то, что раньше создавал `create_all`. На существующем проде она не
  выполняется (там срабатывает `stamp head`).
- `server_default` времени хранится как `now()` — так же, как создавал
  `create_all` на Postgres, чтобы автогенерация не показывала ложный дрейф.
- Тесты используют SQLite и создают схему напрямую через
  `Base.metadata.create_all` (см. `tests/conftest.py`), миграции в тестах не
  выполняются — это быстро и не зависит от Postgres-специфичного DDL.
