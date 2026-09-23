# Роль A — Backend и ML (ты)

Ты тимлид двух AI-агентов. Код пишут они, а ты режешь задачи, запускаешь, проверяешь, сливаешь и отвечаешь за результат. На защите ты объясняешь формулу рейтинга, защиту от выдуманных фактов и NVIDIA-часть (раздел 7).

| Агент | Зона | Папки | Ветка и папка |
| --- | --- | --- | --- |
| **A1 — Cursor** | Ядро backend: API, БД, рейтинг, каталог, отклики, seed, тесты, Docker | `backend/app/{main,config,db,models,schemas,seed}.py`, `backend/app/api/` (кроме `ai.py`, `recommendations.py`), `backend/app/domain/`, `backend/tests/`, `data/seed/`, `docker-compose.yml`, `backend/pyproject.toml` | `feat/backend-core`, `D:\projects\hakaton` |
| **A2 — Codex** | AI и ML: провайдеры, промпты, grounding, PII, заглушка, эмбеддинги, рекомендации, eval, Brev | `backend/app/ai/`, `backend/app/ml/`, `backend/app/api/ai.py`, `backend/app/api/recommendations.py`, `backend/eval/`, `infra/brev/` | `feat/ai-ml`, `..\hakaton-ai` (worktree) |

Если удобнее наоборот (Codex на ядре, Cursor на AI), поменяй местами: зоны остаются те же.

Граница между A1 и A2 — интерфейс `AIService` в `backend/app/ai/contracts.py` (`docs/ai-ml.md`, раздел 4). A1 создаёт его и заглушку в первые 30 минут, дальше `ai/` принадлежит A2. A1 вызывает AI только через этот интерфейс.

## 1. Настройка (первые 10 минут)

**Шаг 0.** Документация пока лежит только у тебя локально и не закоммичена. Worktree для Codex и клон у B её не увидят. Поэтому на старте:

```powershell
cd D:\projects\hakaton
git add README.md AGENTS.md docs
git commit -m "docs: план, архитектура, контракт и роли"
git push origin main            # чтобы B склонировал уже с документацией
```

Дальше:

```powershell
# uv, если ещё нет
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

git checkout -b feat/backend-core                # здесь работает Cursor (A1)
git worktree add ..\hakaton-ai -b feat/ai-ml main  # отдельная папка для Codex (A2)

# .env создаёт A1 из .env.example; ключи вписываешь ты руками
# OPENAI_API_KEY, NVIDIA_API_KEY, позже BREV_LLM_*
```

Когда A1 закончит каркас (около T+0:20), закоммить его в `feat/backend-core` и влей в ветку Codex:

```powershell
git add -A; git commit -m "feat(backend): каркас"      # в D:\projects\hakaton
cd ..\hakaton-ai; git merge feat/backend-core          # теперь у Codex есть contracts.py и stub.py
```

Brev-инстанс создаёшь руками по `docs/nvidia-brev.md`, раздел 3 (T+0:10, 5 минут), и забываешь до T+1:00.

## 2. Фазы и готовые промпты

Промпт вставляешь агенту как есть. После каждой фазы — проверка по разделу 3.

### Фаза 1 (0:00–0:30) — каркас

**A1 — Cursor:**

```text
Прочитай AGENTS.md, docs/architecture.md, docs/api-contract.md, docs/rating-and-gamification.md и docs/ai-ml.md (разделы 4 и 7).
Создай каркас backend по структуре из docs/architecture.md:
- backend/pyproject.toml (Python 3.11, зависимости из AGENTS.md, раздел 4), app/main.py (FastAPI, CORS из настроек, роутеры под /api), app/config.py (pydantic-settings, все переменные из .env.example, читать ../.env и .env), app/db.py (SQLModel + SQLite), app/models.py (все таблицы из раздела «Модель данных»), app/schemas.py (DTO из docs/api-contract.md), app/seed.py.
- Эндпоинты: GET /api/health, GET /api/meta, GET/POST /api/businesses, GET /api/teams, GET /api/teams/{id}, POST /api/admin/reset.
- app/ai/contracts.py строго по docs/ai-ml.md, раздел 4, и app/ai/stub.py и app/ai/question_bank.py по разделу 7 — чтобы backend работал без ключей и без сети.
- Пустые роутеры app/api/ai.py и app/api/recommendations.py, подключённые в main.py (их заполнит другой агент).
- Корневые .gitignore (.env, *.db, .venv, node_modules, dist, __pycache__, backend/eval/reports/*.json) и .env.example из docs/architecture.md, раздел 7.
- data/seed/*.json с синтетикой по docs/hackathon-brief.md, раздел 6: 6 бизнесов, 6 черновиков, 6 опубликованных карточек разных уровней, 6 команд, 8 откликов, 2 этапа (один подтверждён). Бизнес «Дала Логистик» и команда «Nomad AI» (Python, NLP, Telegram-боты, FastAPI) обязательны — они нужны для docs/demo-script.md. Только вымышленные данные, email на example.com.
Готово, когда: `uv run uvicorn app.main:app --reload --port 8000` стартует, /docs открывается, /api/meta отдаёт поля, критерии, уровни и темы, smoke-тест в tests/ проходит. Не коммить и не пушь без моей команды.
```

**A2 — Codex, часть 1** (в папке `..\hakaton-ai`, пока A1 делает каркас; только новые независимые файлы):

```text
Прочитай AGENTS.md, docs/ai-ml.md и docs/nvidia-brev.md. Пока другой агент делает каркас backend, создай только независимые файлы, ничего больше в backend/ не трогай:
1) backend/eval/dataset.jsonl — 12–15 синтетических черновиков бизнес-задач на русском по docs/ai-ml.md, раздел 10: разная полнота, разметка gold.present, 4 обязательные ловушки (prompt injection про бюджет, черновик без чисел, черновик из 1–3 слов, контакт в тексте). Компании вымышленные, email на example.com.
2) infra/brev/serve_vllm.sh и infra/brev/serve_nim.sh по docs/nvidia-brev.md, раздел 3.4 (ключ из переменной окружения, не хардкодить).
Не коммить без моей команды.
```

**A2 — Codex, часть 2** (после `git merge feat/backend-core` в `..\hakaton-ai`):

```text
Работай только в backend/app/ai/, backend/app/ml/, backend/app/api/ai.py, backend/app/api/recommendations.py, backend/eval/, infra/brev/ и backend/tests/test_ai_*.py.
Сделай backend/app/ai/router.py и providers/ (openai, nvidia, brev, stub) по docs/ai-ml.md, разделы 2–3: цепочка AI_PROVIDER_CHAIN, таймаут, один repair, circuit breaker на 60 с, финальная заглушка. Провайдер без ключа или URL недоступен. Сигнатуры AIService из contracts.py не меняй.
Готово, когда: с AI_PROVIDER=stub без сети analyze_draft отдаёт не меньше 3 вопросов, а с OPENAI_API_KEY отдаёт валидный DraftAnalysis. Не коммить без моей команды.
```

### Фаза 2 (0:30–1:40) — конструктор и рейтинг

**A1 — Cursor:**

```text
Реализуй backend/app/domain/rating.py строго по docs/rating-and-gamification.md: 18 проверок с баллами и правилами (разделы 3–4), potential_score, level, next_level, missing с подсказками из раздела 6, achievements из раздела 10. Это чистые функции без I/O; константы и регулярные выражения — в начале файла.
Тесты tests/test_rating.py по разделу 13, включая 4 шага примера (27, 76, 96, 100).
Затем эндпоинты конструктора из docs/api-contract.md, раздел 3.3: POST /api/tasks, GET /api/tasks, GET /api/tasks/{id}, POST /api/tasks/{id}/answers, POST /api/tasks/{id}/clarify, PATCH /api/tasks/{id}/card, POST /api/tasks/{id}/confirm-all, GET /api/tasks/{id}/rating, GET /api/tasks/{id}/history.
Инварианты: AI вызывается только через AIService; AI не перезаписывает confirmed-поля; баллы только за confirmed; каждое изменение score пишет score_event с delta и причиной; ответы API совпадают с контрактом.
Тест tests/test_api_flow.py: черновик → ответы → подтверждение → рейтинг вырос (на заглушке).
```

**A2 — Codex:**

```text
Шаг 2 по docs/ai-ml.md: prompts/analyze_draft.v1.md и build_card.v1.md (раздел 5), clarify.py и card_builder.py, grounding.py (раздел 6: цитаты с rapidfuzz, числа, email, URL и @handle), постобработка вопросов (не меньше 3, добор из question_bank, points_gain через domain.rating), trace.py (запись каждой попытки в ai_trace). Провайдер nvidia: base_url из NVIDIA_BASE_URL, отключи рассуждение через chat_template_kwargs.enable_thinking=false.
Тесты: невалидный JSON → repair → следующий провайдер → заглушка; выдуманное число отклоняется; меньше 3 вопросов → добор; confirmed-поля не возвращаются.
```

**S1 (1:40):** слить `feat/ai-ml` и `feat/backend-core` в `main` → `pytest` зелёный → проверка на секреты → push (твоё решение) → написать B, что backend в `main`.

### Фаза 3 (1:40–2:40) — публикация, каталог, прозрачность

**A1 — Cursor:**

```text
По docs/api-contract.md, разделы 3.3–3.4, и docs/rating-and-gamification.md, раздел 7: POST /api/tasks/{id}/publish (confirm обязателен, нужен подтверждённый title, неподтверждённые поля не публикуются), GET /api/catalog (сортировка score desc → published_at asc → id, фильтры topic, level (несколько), q, sort=newest, position), GET /api/catalog/{id} (только confirmed-поля и полный rating), catalog_position и catalog_position_preview в TaskDetail. Логику порядка вынеси в domain/catalog.py и покрой тестом.
```

**A2 — Codex:**

```text
Шаг 3 по docs/ai-ml.md: pii.py (маскирование и восстановление, раздел 6), ml/embeddings.py (цепочка nvidia → openai → tfidf, input_type passage и query для NVIDIA, кэш в памяти), ml/recommend.py (формула match, только score ≥ 40, reasons, раздел 9), GET /api/teams/{id}/recommendations, GET /api/ai/traces, GET /api/ai/prompts, GET и PUT /api/ai/provider — всё по docs/api-contract.md, разделы 3.5 и 3.7.
```

**S2 (2:40):** слить и запушить. Черновик → публикация → каталог проходит через UI у B.

### Фаза 4 (2:40–3:40) — отклики и решение

**A1 — Cursor:**

```text
По docs/api-contract.md, раздел 3.6: отклики (POST и GET по задаче, GET по команде), POST /api/proposals/{id}/decision (только вручную, проверка владельца, можно менять решение), этапы (только для selected), POST /api/milestones/{id}/confirm (+points к team.progress_points, повторно нельзя), GET /api/leaderboard/teams. Все коды ошибок из раздела 2. Расширь test_api_flow.py до полного сценария из docs/demo-script.md.
```

**A2 — Codex:**

```text
Шаг 4 по docs/ai-ml.md, раздел 10: eval/run_eval.py на готовом backend/eval/dataset.jsonl с метриками из таблицы, отчёт eval/reports/latest.md и GET /api/ai/eval/latest. Прогони на stub, openai, nvidia. Если Brev поднят (docs/nvidia-brev.md), добавь провайдер brev и infra/brev/serve_vllm.sh и serve_nim.sh.
```

**S3 (3:40):** полный сценарий проходит в UI.

### Фаза 5 (3:40–5:00) — стабилизация и сдача

**A1 — Cursor:**

```text
Добавь docker-compose.yml (backend на :8000 с env_file .env и томом ./data, frontend на :5173 или :8080), проверь `docker compose up --build` с чистого клона. Прогони ruff и pytest. Убедись, что с AI_PROVIDER=stub и EMBED_PROVIDER_CHAIN=tfidf без сети проходит весь сценарий из docs/demo-script.md.
```

Затем README: вставить Codex промпт организаторов из `docs/hackathon-brief.md`, раздел 12, и дописать «сохрани формулу рейтинга, правила каталога, тестовые сценарии и таблицу eval». Прочитать результат глазами: только то, что реально работает.

## 3. Как проверять работу агента (5 минут на фазу)

- [ ] Запускается: `uv run uvicorn app.main:app --reload --port 8000`; `/docs` открывается.
- [ ] `uv run pytest` зелёный, `uv run ruff check .` чистый.
- [ ] Вручную в `/docs`: создать задачу → ответить → подтвердить → рейтинг вырос, `delta` верный.
- [ ] С `AI_PROVIDER=stub` и без интернета всё то же самое работает.
- [ ] В `git diff` нет ключей, `.env`, `*.db`; агент не лез в чужую зону.
- [ ] Форма ответов совпадает с `docs/api-contract.md`. Если агент её поменял — обновить контракт и сказать B.
- [ ] Нет автоназначения команд, AI не ставит баллы, confirmed-поля не перезаписываются.

Если агент застрял больше 10 минут на одном месте: откати (`git checkout -- <файл>` или `git stash`), сузь задачу и дай конкретный файл и пример входа и выхода.

## 4. Работа с B

- Контракт — `docs/api-contract.md`. Меняешь поле — предупреждаешь B в том же сообщении, где говоришь про push.
- B может запускать backend у себя без ключей: `AI_PROVIDER=stub`. Свои ключи не передаём: правила запрещают передавать ключи другим лицам. У B есть свои персональные доступы.
- На S1–S3 пушишь `main`, B делает `git pull` и переключает UI с моков на реальный API.

## 5. Мой чек-лист

- [ ] T+0:10 — Brev-инстанс создан, модель грузится.
- [ ] S1 — конструктор и рейтинг в `main`.
- [ ] S2 — публикация, каталог, рекомендации, Inspector в `main`.
- [ ] S3 — отклики, решения, этапы в `main`; сценарий проходит целиком.
- [ ] Eval-отчёт или честная пометка «не успели».
- [ ] Brev остановлен после демо.
- [ ] README по факту, проверка на секреты, push, сдача на платформе.

## 6. Проверка на секреты перед push

```powershell
git grep -nE "(sk-[A-Za-z0-9_-]{20,}|nvapi-[A-Za-z0-9_-]{20,})"   # ключи OpenAI и NVIDIA в отслеживаемых файлах
git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$"          # .env и БД не в git
git status --short | Select-String -Pattern "\.env$|\.db$"         # и не готовятся к коммиту
```

Все три команды должны вернуть пусто. Ключ Brev (`BREV_LLM_API_KEY`) не имеет префикса и по шаблону не ловится, поэтому он живёт только в `.env`. Дополнительно можно запустить `docker run --rm -v "${PWD}:/repo" zricethezav/gitleaks detect --source /repo`.

## 7. Что ты должен уметь объяснить на защите

1. **Формулу рейтинга:** 7 критериев, 18 проверок, баллы только за подтверждённое, уровни 40, 70, 90, пересчёт и `score_event`.
2. **Почему AI не выдумывает:** цитаты, grounding (подстрока или fuzzy-сравнение от 90), проверка чисел и контактов, отклонённые поля в Inspector, метрика `grounding_reject_rate` в eval.
3. **Некорректный ответ модели:** валидация, repair, следующий провайдер, заглушка; всё в `ai_trace`.
4. **NVIDIA:** Nemotron 3 через Build API (OpenAI-совместимо, рассуждение выключено для JSON); эмбеддинги `nemotron-3-embed-1b`; своя модель на Brev через vLLM или NIM, port-forward; почему русский сначала идёт в OpenAI (Nemotron дообучали без русского, это видно по eval).
5. **Почему нет автоназначения и как работают рекомендации:** только навыки и интересы, только задачи от 40 баллов, каталог не фильтруется.
