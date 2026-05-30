# Human Compatibility OS — Дорожная карта разработки

Источник: канонический пакет документов v10 (Fabrika Sredy / Human Compatibility OS).
Разработка ведётся пофазно, full-stack. UI — на русском.

## Принципы продукта (жёсткие ограничения)

- **Explainability-first** — каждый вывод объясним и проверяем.
- **Никаких автоматических решений** — светофор-индикаторы не являются единственным
  основанием для отказа, увольнения или иного кадрового действия.
- **Обязательная проверка человеком** для всех выводов.
- **Явное согласие** на сбор операционных данных + прозрачность.
- **Аудит и анти-слежка** — система не превращается в скрытый профайлинг.
- Оценивается **операционная совместимость и устойчивость среды**, а не ценность человека.

## Стек

FastAPI · SQLAlchemy 2.0 · psycopg3 · PostgreSQL · Next.js · Tailwind · Docker Compose · Nginx · GitHub Actions.

## Доменное ядро (из спецификации)

- **Роли (RBAC):** Employee, HR, Team Lead, Founder/Admin, Ethics Reviewer · JWT + refresh.
- **Опросник:** 15 вопросов, шкала 1–5.
- **Формула Burnout Pressure:**
  `Emergency*0.30 + RecoveryDeficit*0.25 + CommOverload*0.20 + Interruption*0.15 + LeadershipInstability*0.10`
- **Пороги риска:** 0.0–1.9 Low · 2.0–3.4 Medium · 3.5–5.0 High.
- **Блоки дашборда:** Burnout Pressure · Recovery Sustainability · Communication Entropy · Leadership Stability.
- **Цикл рекалибровки:** Baseline → 30 дней → 90 дней → ретроспектива.
- **Таблицы БД:** users, questionnaires, questionnaire_answers, calibration_reviews,
  recalibration_events, environment_metrics (UUID PK, timestamps, индексы, FK).

## API-эндпоинты (целевые)

| Метод | Путь                          | Фаза |
|-------|-------------------------------|------|
| GET   | /health                       | 0    |
| POST  | /auth/login                   | 1    |
| POST  | /questionnaire/submit         | 2    |
| GET   | /employee/{id}/history        | 2    |
| GET   | /dashboard/team/{id}          | 3    |
| GET   | /environment/metrics          | 3    |
| POST  | /recalibration/create         | 4    |

## Фазы

### Фаза 0 — Каркас ✅
Репозиторий, docker-compose (Postgres), backend skeleton (config/db/main/health),
frontend skeleton (Next.js + Tailwind, заглушка дашборда), CI, README, ROADMAP.

### Фаза 1 — Данные + Auth/RBAC ✅
Модели SQLAlchemy всех таблиц (+ audit_logs), Pydantic-схемы, JWT + refresh,
5 ролей, RBAC-зависимость `require_roles`, аудит-лог, сбор согласия.
Эндпоинты: `POST /auth/register`, `/auth/login`, `/auth/refresh`,
`GET /auth/me`, `POST /auth/consent`.

### Фаза 2 — Опросник + Scoring Engine (ядро MVP) ✅
15-вопросный опросник (RU), `GET /questionnaire/questions`,
`POST /questionnaire/submit`, движок подсчёта (`scoring.py`: формула +
5 саб-компонентов с RU-метками, ориентация reverse-вопросов), пороги риска,
объяснимый результат по компонентам. Юнит-тесты формулы + тесты эндпоинтов
(consent 403, scoring, RBAC). `GET /employee/{id}/history`.
UI: страница логина, форма опросника (шкала 1–5) с явным согласием,
экран результата с разбором по компонентам.

### Фаза 3 — Дашборд (телеметрия) ✅
`GET /dashboard/team/{id}` — агрегаты 4 блоков (Burnout Pressure, Recovery
Sustainability, Communication Entropy, Leadership Stability) из последнего опросника
каждого участника команды, с распределением по уровням риска. `POST/GET
/environment/metrics` — запись и агрегаты (count/mean/min/max) по типам метрик.
Anonymized analytics mode: агрегаты подавляются при выборке < MIN_COHORT (3) —
команда не может стать профилем одного человека. RBAC: дашборд видят hr/team_lead/
admin/ethics_reviewer; team_lead — только свою команду; просмотры аудируются.
Доменное ядро в `app/dashboard.py` (`aggregate_team`, `aggregate_metrics`).
UI: страница `/dashboard` с реальными данными, светофоры с дисклеймерами.

### Фаза 4 — Движок рекалибровки ✅
`POST /recalibration/create` (привязка к опроснику: явный `questionnaire_id` или
последний заполненный), `GET /recalibration/{user_id}` — таймлайн событий циклов
baseline → 30 → 90 дней → ретроспектива. Доменное ядро `app/recalibration.py`:
`trend_for` (improving/worsening/stable/insufficient относительно baseline, порог
0.3), `recommendations_for` (development-рекомендации по доминирующему
компоненту-драйверу ≥ 3.5, RU, advisory — не кадровые решения). RBAC: свои или
роли-ревьюеры; создание аудируется. UI: страница `/recalibration` — baseline,
тренд, рекомендации, история событий с Δ, форма создания события.

### Фаза 5 — Полировка фронтенда + Calibration Review ✅
Backend: `GET /users` (директория, scoped: team_lead — своя команда, hr/admin/
ethics — все), `POST /calibration/review` и `GET /calibration/review/{subject_id}`
(`routers/calibration.py`, модель `CalibrationReview`). RBAC: ревьюеры создают;
субъект всегда читает review о себе (прозрачность); team_lead — только своя команда;
создание и чтение аудируются. UI: страница `/review` (выбор сотрудника, история
опросников, прошлые review, форма нового review с источником данных). Общий
модуль светофоров `lib/risk.ts`, дисклеймеры на всех экранах.

### Фаза 6 — Этика/комплаенс + пилот ✅
`GET /compliance/policy` (машиночитаемая доктрина: no_automated_decisions,
requires_consent, requires_human_review + определение пилот-метрики),
`GET /compliance/pilot-metric/team/{id}` (KPI: emergency pressure baseline → day_90,
%change vs −20%, cohort-suppressed, `app/pilot.py`), `GET /audit` (журнал для
oversight-ролей admin/ethics_reviewer), `GET /export/employee/{id}` (полный
объяснимый пакет для human review: профиль + опросники + рекалибровка + reviews;
self или ревьюер; аудируется). UI: `/audit`, пилотная KPI-карточка на дашборде,
кнопка экспорта на `/review`. Документ пилота — [docs/PILOT.md](PILOT.md) (метрика
успеха, жёсткие ограничения, цикл, 3–5 кейсов).

### Фаза 7 — Полный набор пилот-метрик ✅
`GET /compliance/pilot-metric/...` отдаёт headline (emergency −20%) + изменение
всех 4 блоков среды baseline→day_90 (`app/pilot.py: compute_pilot_report`).

### Фаза 8 — Onboarding stability ✅
`GET /onboarding/team/{id}` — трение интеграции новичков vs устоявшаяся команда
(`app/onboarding.py`), окно по `created_at`, без миграций. UI-карточка на дашборде.

### Фаза 9 — Compatibility Hiring ✅ (HR Workbook v6)
Модели `candidates`, `compatibility_assessments`, `development_plans`. Справочник
`app/hiring.py` (10 сигналов: индикатор/вопрос/фокус/легенда риска, 5 измерений,
decision guidance, advisory `suggest_overall_risk`). Эндпоинты `/hiring/*`:
reference, candidates (CRUD-lite), assessments (Quick Screen 4 сигнала /
Full Calibration 10), development-plan. RBAC: hr/team_lead/admin создают,
ethics_reviewer смотрит; аудит; **никакого авто-отказа**. UI `/hiring`.
