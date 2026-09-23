# AGENTS.md — правила для AI-агентов (Codex, Cursor и других)

Контекст: 5-часовой хакатон HackAlem AI, кейс AI Sana. Цель — **рабочий сквозной сценарий**, а не идеальная архитектура. Выбирай самое простое решение, которое работает и проходит тесты.

## 0. Перед любой задачей

1. Прочитай этот файл и документы своей зоны:
   - ядро backend: `docs/architecture.md`, `docs/api-contract.md`, `docs/rating-and-gamification.md`;
   - AI и ML: `docs/ai-ml.md`, `docs/nvidia-brev.md`;
   - frontend: `docs/team/B-frontend-product.md`, `docs/api-contract.md`.
2. Определи свою зону (раздел 3). Чужие файлы не трогай.
3. **Не делай `git commit` и `git push`, пока человек явно не попросит.**

## 1. Что строим

**AI Sana Challenge Hub** — веб-платформа, где бизнес превращает короткое описание задачи в полноценную карточку, получает рейтинг готовности 0–100 и публикует задачу в открытом каталоге. Студенческие команды сами откликаются, бизнес сам выбирает.

Сценарий: черновик → AI-уточнение (не меньше 3 вопросов) → редактируемая карточка (AI предлагает, человек подтверждает) → рейтинг с расшифровкой и подсказками → публикация в каталог (позиция по рейтингу) → отклик команды (каталог и рекомендации) → ручное решение бизнеса → баллы команде за подтверждённый этап.

## 2. Инварианты предметной области (нарушать нельзя)

1. **Автоназначения команд нет.** Нет эндпоинтов, фоновых задач и AI-логики, которые выбирают, назначают или ранжируют команды за бизнес. Решение — только `POST /api/proposals/{id}/decision` по явному действию бизнеса.
2. **AI не добавляет фактов.** У каждого поля от AI есть дословная цитата из черновика или ответа. Grounding-проверка (цитата, числа, email, URL, @handle) обязательна. Поле, не прошедшее её, отбрасывается и пишется в `ai_trace`.
3. **AI только предлагает.** Поля от AI имеют статус `suggested` и дают 0 баллов. **AI никогда не перезаписывает `confirmed`-поля.**
4. **Баллы считают правила, а не AI.** Рейтинг — чистая детерминированная функция в `backend/app/domain/rating.py`. Веса 20/20/15/15/10/10/10, 18 проверок, уровни 0–39, 40–69, 70–89, 90–100. Любое изменение формулы — вместе с `docs/rating-and-gamification.md` и тестами.
5. **Пересчёт после каждого подтверждённого изменения**, запись в `score_event` с `delta` и причиной.
6. **Каталог ничего не скрывает.** Все опубликованные задачи видны при любом рейтинге. Сортировка по умолчанию: `score` по убыванию, затем `published_at` по возрастанию, затем `id`. Отклики разрешены на любом уровне и не ограничены по числу.
7. **Рекомендации** — только опубликованные задачи со `score ≥ 40`, только по интересам, навыкам и технологиям команды, с объяснением. Каталог они не фильтруют.
8. **Персональные и чувствительные признаки не используются.** Перед внешним LLM email, телефоны и @handle маскируются.
9. **Всегда не меньше 3 уточняющих вопросов** на первом шаге (добор из банка вопросов).
10. **Конвейер любого LLM-вызова:** маскирование PII → провайдер со structured output → валидация Pydantic → один repair → следующий провайдер → офлайн-заглушка → grounding → `ai_trace`. **Сценарий обязан работать без сети** (`AI_PROVIDER=stub`).

## 3. Зоны ответственности

| Зона | Человек | Агент | Пути |
| --- | --- | --- | --- |
| A1 — ядро backend | A | Cursor | `backend/app/{main,config,db,models,schemas,seed,errors}.py`, `backend/app/api/` (кроме `ai.py` и `recommendations.py`), `backend/app/services/`, `backend/app/domain/`, `backend/tests/` (кроме `test_ai_*.py`), `data/seed/`, `docker-compose.yml`, `backend/pyproject.toml` |
| A2 — AI и ML | A | Codex | `backend/app/ai/`, `backend/app/ml/`, `backend/app/api/ai.py`, `backend/app/api/recommendations.py`, `backend/eval/`, `infra/brev/`, `backend/tests/test_ai_*.py` |
| B — frontend | B | его агент | `frontend/` |
| Общее | A + B | — | `docs/`, `README.md`, `AGENTS.md`, `.env.example`, `.gitignore` — меняет человек или агент по прямой просьбе |

- Граница A1 и A2 — интерфейс `AIService` в `backend/app/ai/contracts.py`. Его сигнатуры меняются только по договорённости.
- Исключение на старте: A1 в каркасе создаёт `ai/contracts.py`, `ai/stub.py` и `ai/question_bank.py` по `docs/ai-ml.md` (разделы 4 и 7), а также пустые `api/ai.py` и `api/recommendations.py`. После слияния каркаса эти файлы принадлежат A2.
- Контракт API — `docs/api-contract.md`. Изменил ответ эндпоинта — обнови контракт в том же изменении и напиши об этом в итоговом отчёте.
- Новую зависимость в `pyproject.toml` добавляет A1. A2 пишет, что ему нужно.

## 4. Стек и команды

**Backend** (Python 3.11, в `backend/`). Зависимости: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `sqlmodel`, `httpx`, `openai`, `numpy`, `scikit-learn`, `rapidfuzz`; dev — `pytest`, `ruff`.

```powershell
cd backend
uv sync                                           # установка
uv run uvicorn app.main:app --reload --port 8000  # запуск, документация на http://localhost:8000/docs
uv run pytest                                     # тесты
uv run ruff check . --fix; uv run ruff format .   # линт и формат
uv run python -m eval.run_eval --providers stub,openai,nvidia   # eval (зона A2)
```

Без uv: `python -m venv .venv; .venv\Scripts\activate; pip install -e ".[dev]"`.

**Frontend** (Node 20+, в `frontend/`):

```powershell
npm install
npm run dev        # http://localhost:5173, proxy /api → :8000
npm run build
npm run gen:api    # типы из http://localhost:8000/openapi.json
npx tsc --noEmit
```

**Всё вместе:** `docker compose up --build`.

**Офлайн-проверка:** в `.env` поставить `AI_PROVIDER=stub` и `EMBED_PROVIDER_CHAIN=tfidf`, отключить сеть, пройти сценарий из `docs/demo-script.md`.

## 5. Конвенции

- Код, идентификаторы и имена файлов — на английском. Тексты UI, сообщения ошибок для пользователя и документация — на русском.
- Python: type hints везде; Pydantic v2 для всего ввода и вывода; роутер на ресурс в `app/api/`; бизнес-логика в `app/domain/` без I/O; `logging` вместо `print`; доменные ошибки — `HTTPException(status, {"code": ..., "message": ...})` с кодами из контракта.
- TypeScript: `strict`, без `any`; функциональные компоненты; серверное состояние через TanStack Query; компоненты shadcn/ui; подписи из `/api/meta`.
- Промпты — только в `backend/app/ai/prompts/*.vN.md`. Изменил промпт — повысь версию.
- Не добавляй: LangChain и прочие фреймворки агентов, векторные БД, Redis и очереди, auth-библиотеки, инструменты миграций, CSS-фреймворки кроме Tailwind.
- Коммиты (когда попросят): `feat(backend): ...`, `feat(ai): ...`, `feat(frontend): ...`, `fix: ...`, `test: ...`, `docs: ...`.

## 6. Безопасность (требования организаторов)

- **Ключи только в `.env`** в корне; `.env` внесён в `.gitignore`. В `.env.example` — пустые значения. Не логируй ключи, не выводи их в ответах API, не клади во frontend (всё с `VITE_` публично).
- Только синтетические данные: email на `example.com`, вымышленные компании и люди. Реальные персональные или служебные данные не используем.
- Не отправляй во внешние AI-сервисы конфиденциальное. Маскирование PII включено по умолчанию.
- Не сканируй сеть, не делай нагрузочных тестов, не выставляй сервисы в интернет без `--api-key`.
- Проверка перед push (всё должно вернуть пусто):

```powershell
git grep -nE "(sk-[A-Za-z0-9_-]{20,}|nvapi-[A-Za-z0-9_-]{20,})"
git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$"
git status --short | Select-String -Pattern "\.env$|\.db$"
```

## 7. Definition of Done

- [ ] Работает с `AI_PROVIDER=stub` без сети.
- [ ] `uv run pytest` и `uv run ruff check .` чистые (backend); `npm run build` и `npx tsc --noEmit` проходят (frontend).
- [ ] Эндпоинты и формы данных совпадают с `docs/api-contract.md`.
- [ ] Инварианты из раздела 2 не нарушены. Для рейтинга, grounding и fallback есть тесты.
- [ ] В UI есть состояния загрузки, ошибки и пустых списков.
- [ ] В diff нет секретов, `.env` и `*.db`.

## 8. Приоритеты

P0 — сквозной сценарий, рейтинг, каталог, отклики, ручное решение, заглушка. P1 — AI Inspector, рекомендации, маскирование PII, переключение провайдера, история рейтинга. P2 — eval, Brev, дубликаты, модерация, RU/KZ. Если время поджимает, режем по cut-list в `docs/plan-5h.md`, раздел 3. P0 не режем никогда.

## 9. Итоговый отчёт агента

В конце задачи — 3–6 строк: что сделано (файлы), как проверить (команда или URL), что изменилось в контракте (если изменилось), что осталось или не получилось.
