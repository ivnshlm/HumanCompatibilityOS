# Статус проекта — Human Compatibility OS

> Документ для передачи работы между машинами. Обновляется в конце каждой фазы.
> Последнее обновление: 2026-05-29 (после Фазы 2).

Репозиторий: `https://github.com/ivnshlm/HumanCompatibilityOS` (приватный).
Ветка по умолчанию: `main`. Рабочий процесс: ветка → PR → зелёный CI → squash-merge.

---

## Что сделано

### Фаза 0 — Каркас ✅ (PR смержён)
- Структура репозитория, `docker-compose.yml` (backend + Postgres), `.env.example`.
- Backend skeleton: `app/config.py`, `app/db.py`, `app/main.py`, `app/routers/health.py`.
- Frontend skeleton: Next.js + Tailwind, заглушка главной (`app/page.tsx`).
- CI (`.github/workflows/ci.yml`): backend (ruff + pytest), frontend (next build).
- `README.md`, `docs/ROADMAP.md`.

### Фаза 1 — Данные + Auth/RBAC ✅ (PR #1 смержён)
- `app/models.py`: все 6 таблиц спецификации + `audit_logs`. UUID PK, FK, enum'ы
  (`Role`, `RiskLevel`, `RecalibrationCycle`), `native_enum=False` для совместимости с SQLite.
- `app/security.py`: bcrypt (hash/verify), JWT access + refresh (PyJWT), валидация типа токена.
- `app/deps.py`: `get_current_user` (HTTPBearer), фабрика `require_roles(*roles)`.
- `app/audit.py`: `log_audit(...)`.
- `app/schemas.py`: Pydantic-схемы auth.
- `app/routers/auth.py`: `POST /auth/register`, `/auth/login`, `/auth/refresh`,
  `GET /auth/me`, `POST /auth/consent`. Все пишут аудит.
- Тесты: `tests/test_auth.py`, `tests/test_root.py` (SQLite in-memory через override `get_db`).

### Фаза 2 — Опросник + Scoring Engine ✅ (PR #2 смержён)
- `app/scoring.py` — ядро:
  - 15 вопросов (RU), маппинг на 5 компонентов: emergency_pressure (0.30),
    recovery_deficit (0.25), communication_overload (0.20), interruption_density (0.15),
    leadership_instability (0.10). RU-метки компонентов.
  - reverse-вопросы (Q4, Q8, Q9, Q14) считаются как `6 - value`.
  - Формула Burnout Pressure = взвешенная сумма средних по компонентам.
  - Пороги риска: 0.0–1.9 low, 2.0–3.4 medium, 3.5–5.0 high.
  - `compute_burnout_score()` валидирует полноту (15 шт.), диапазон (1–5), индексы;
    возвращает объяснимый разбор по компонентам.
- `app/routers/questionnaire.py`:
  - `GET /questionnaire/questions` — список вопросов.
  - `POST /questionnaire/submit` — **требует согласия** (иначе 403), считает, сохраняет, аудирует.
  - `GET /employee/{id}/history` — RBAC: свои или роли-ревьюеры (hr/team_lead/admin/ethics_reviewer).
- `app/schemas.py`: QuestionOut, AnswerIn, QuestionnaireSubmit, ComponentScoreOut,
  QuestionnaireResult, HistoryItem.
- Тесты: `tests/test_scoring.py` (юнит формулы/порогов), `tests/test_questionnaire.py`
  (consent 403, scoring, incomplete 400, out-of-range 422, history, RBAC).
- Frontend: `lib/api.ts` (клиент + токен в localStorage `hcos_access_token`),
  `app/login/page.tsx`, `app/questionnaire/page.tsx` (шкала 1–5, явное согласие,
  экран результата с разбором по компонентам), навигация на главной.

**Тесты:** 29 проходят. **Ruff:** чисто. **CI:** зелёный на обоих PR.

---

## Что осталось (роадмап)

### Фаза 3 — Дашборд (телеметрия) ← следующая
- `GET /dashboard/team/{id}`, `GET /environment/metrics`.
- Агрегаты 4 блоков (Burnout Pressure, Recovery Sustainability,
  Communication Entropy, Leadership Stability), anonymized analytics mode, RBAC-видимость.
- UI: дашборд с реальными данными вместо заглушек на главной.

### Фаза 4 — Движок рекалибровки
- `POST /recalibration/create`, циклы baseline → 30 → 90 дней → ретроспектива,
  сравнение с baseline, тренды, development-рекомендации. UI: история и review-экран.

### Фаза 5 — Полировка фронтенда
- UX, светофоры с дисклеймерами, экран calibration review для HR/Team Lead.

### Фаза 6 — Этика/комплаенс + пилот
- Проверки «нет авто-решений», экспорт для human review, аудит,
  инструкции пилота (3–5 кейсов), метрики (−20% emergency pressure за 90 дней).

### Позже — Compatibility Hiring
- Quick Screen, Full Calibration, Interview Guide, Development Plan (HR Workbook v6).

### Технический долг / отложено
- **Alembic-миграции** — сейчас `init_db()` делает `create_all` на старте (MVP).
- **Деплой (CD)** — пока нет; запуск только локально. Кандидаты: Railway/Render/Fly.io.
  Делать ближе к Фазе 6 (данные HR-чувствительные → аккуратно с приватностью).
- **Docker на dev-машине** — на момент написания не установлен; стек гонялся через CI.

---

## Как продолжить на другом компе

```bash
git clone https://github.com/ivnshlm/HumanCompatibilityOS.git
cd HumanCompatibilityOS
cp .env.example .env
```

### Вариант A — через Docker (нужен установленный + запущенный Docker Desktop)
```bash
docker compose up --build
# backend:  http://localhost:8000  (Swagger: /docs)
# frontend: http://localhost:3000
```

### Вариант B — backend без Docker (нужен Python 3.12)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
ruff check .            # линтер
pytest -q               # 29 тестов (SQLite in-memory, Postgres не нужен)
uvicorn app.main:app --reload   # запуск API на :8000
```

### Frontend локально (нужен Node)
```bash
cd frontend
npm install
npm run dev             # :3000  (для prod-сборки: npm run build)
```
Env-переменная фронта: `NEXT_PUBLIC_API_BASE_URL` (по умолчанию `http://localhost:8000`).

---

## Заметки по окружению (текущая dev-машина, Windows)
- Реальный Python 3.12: `C:\Users\isha7\AppData\Local\Programs\Python\Python312\python.exe`
  (bare `python`/`py` указывают на заглушку Microsoft Store — не использовать).
  В CI-форме тесты: `pytest` (console-script) из `backend/` — путь чинит `pyproject.toml` (`pythonpath=["."]`).
- Node/npm локально **нет** — фронт собирается только в CI (`next build`).
- Docker — **не установлен** (проверено 2026-05-29). После установки запустить Docker Desktop.
- `gh` CLI нет — PR'ы создаются через GitHub REST API.
