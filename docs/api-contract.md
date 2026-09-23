# API-контракт: backend ⇄ frontend

Это договорённость между зоной A (backend) и зоной B (frontend). Меняем её только вместе с кодом и в том же изменении. Предупреждаем второго человека.

- Базовый URL: `http://localhost:8000/api`. В dev frontend ходит на `/api` через proxy Vite.
- Формат JSON в UTF-8, даты в ISO-8601 (UTC).
- Авторизации нет. Роль передаётся явными `business_id` и `team_id` (переключатель ролей в UI).
- Источник правды для типов — `GET /openapi.json` (FastAPI). Frontend генерирует типы командой `npm run gen:api`. Ниже — те же типы в нотации TypeScript, по ним B делает моки до готовности backend.

## 1. Типы

```ts
type FieldKey =
  | "title" | "context" | "need" | "users" | "data" | "constraints"
  | "expected_result" | "success_criteria" | "contact" | "interaction_format";

type CriterionKey =
  | "context_need" | "data" | "expected_result" | "success_criteria"
  | "constraints" | "users" | "business_link";

type LevelKey = "draft" | "working" | "ready" | "priority";
type TaskStatus = "clarifying" | "review" | "published";
type FieldStatus = "empty" | "suggested" | "confirmed";
type ProposalStatus = "submitted" | "selected" | "rejected";
type ProviderName = "openai" | "nvidia" | "brev" | "stub";

interface Evidence { source: string; quote: string }   // source: "draft" | "answer:q1" | ...

interface CardField {
  value: string | null;
  status: FieldStatus;
  source: "ai" | "user" | null;
  evidence: Evidence[];
  updated_at: string | null;
}
type Card = Record<FieldKey, CardField>;

interface Question {
  id: string;              // "q1", "q2", ... уникален в пределах задачи
  field: FieldKey;
  question: string;
  why: string;             // зачем спрашиваем, одна строка
  points_gain: number;     // сколько баллов может дать ответ; считается по текущей карточке
  answer: string | null;
  round: number;           // 1 — первичные вопросы, 2+ — дополнительные
}

interface Check { id: string; label: string; field: FieldKey; points: number; passed: boolean }
interface CriterionScore { criterion: CriterionKey; label: string; max: number; earned: number; checks: Check[] }
interface MissingItem { check_id: string; criterion: CriterionKey; field: FieldKey; hint: string; points_gain: number }
interface Level { key: LevelKey; label: string; min: number; max: number }
interface Achievement { key: string; label: string; description: string; earned: boolean }

interface Rating {
  score: number;               // 0..100, только подтверждённые поля
  potential_score: number;     // если подтвердить все suggested-поля
  delta: number;               // изменение с прошлого пересчёта
  level: Level;
  next_level: { key: LevelKey; label: string; points_needed: number } | null;
  breakdown: CriterionScore[]; // всегда 7 критериев, сумма max = 100
  missing: MissingItem[];      // по убыванию points_gain
  achievements: Achievement[];
}

interface AiMeta {
  provider_used: ProviderName;
  model: string;
  degraded: boolean;           // ответил не первый провайдер цепочки
  trace_ids: number[];
}

interface TaskDetail {
  id: number;
  business: { id: number; name: string };
  status: TaskStatus;
  topic: string | null;
  draft_text: string;
  card: Card;
  questions: Question[];
  rating: Rating;
  catalog_position: number | null;     // место в каталоге, если опубликована
  catalog_position_preview: number;    // место при текущем score (для неопубликованной — «если опубликовать сейчас»)
  proposals_count: number;
  ai: AiMeta | null;                   // мета последнего AI-вызова по задаче
  created_at: string;
  updated_at: string;
  published_at: string | null;
}

interface TaskSummary {                // для списка «Мои задачи»
  id: number; title: string | null; status: TaskStatus; topic: string | null;
  score: number; level: Level; proposals_count: number; updated_at: string;
}

interface CatalogItem {
  id: number;
  title: string;
  topic: string | null;
  business_name: string;
  score: number;
  level: Level;
  highlighted: boolean;          // level = priority
  needs_clarification: boolean;  // level = draft
  need_preview: string;          // до 160 символов
  proposals_count: number;
  position: number;              // 1-based, по умолчательной сортировке
  published_at: string;
}

interface PublicTask {           // карточка для команд: только confirmed-поля
  id: number; title: string; topic: string | null; business_name: string;
  card: Partial<Record<FieldKey, string>>;
  rating: Rating; position: number; proposals_count: number; published_at: string;
}

interface Business { id: number; name: string; industry: string | null }
interface Team {
  id: number; name: string;
  interests: string[]; skills: string[]; technologies: string[];
  progress_points: number;
}

interface Milestone {
  id: number; proposal_id: number; title: string; points: number;
  status: "pending" | "confirmed"; confirmed_at: string | null;
}

interface Proposal {
  id: number;
  task: { id: number; title: string };
  team: Team;
  idea: string;
  plan: string;
  timeline: string;
  prototype_url: string | null;
  status: ProposalStatus;
  business_comment: string | null;
  milestones: Milestone[];
  created_at: string;
  decided_at: string | null;
}

interface Recommendation {
  task: CatalogItem;
  match: number;            // 0..1
  reasons: string[];        // человекочитаемые причины
  matched_terms: string[];  // совпавшие навыки и технологии
}

interface ScoreEvent { score: number; delta: number; level: LevelKey; reason: string; created_at: string }

interface AiTrace {
  id: number;
  task_id: number | null;
  operation: "analyze_draft" | "build_card" | "embed" | string;
  provider: ProviderName | "tfidf";
  model: string;
  prompt_version: string | null;
  status: "ok" | "repaired" | "fallback" | "failed";
  input_redacted: string;
  raw_output: string;
  parsed: unknown;
  errors: string[];
  grounding_rejected: { field: FieldKey; value: string; reason: string }[];
  latency_ms: number;
  created_at: string;
}
```

## 2. Ошибки

- **422** — стандартная ошибка валидации FastAPI: `{"detail": [ ... ]}`.
- **400, 403, 404, 409** — доменные ошибки: `{"detail": {"code": "TASK_NOT_FOUND", "message": "Задача не найдена"}}`.

| Код | HTTP | Когда |
| --- | :-: | --- |
| `TASK_NOT_FOUND`, `TEAM_NOT_FOUND`, `BUSINESS_NOT_FOUND`, `PROPOSAL_NOT_FOUND`, `MILESTONE_NOT_FOUND` | 404 | Нет сущности |
| `QUESTION_NOT_FOUND` | 404 | В ответах передан `question_id`, которого нет у этой задачи |
| `NOT_TASK_OWNER` | 403 | `business_id` не владелец задачи (просмотр откликов, решение, этапы) |
| `CONFIRMATION_REQUIRED` | 400 | Публикация без `confirm: true` |
| `TITLE_REQUIRED` | 409 | Публикация без подтверждённого названия |
| `TASK_NOT_PUBLISHED` | 409 | Отклик на неопубликованную задачу |
| `PROPOSAL_NOT_SELECTED` | 409 | Этап для отклика, который не выбран |
| `MILESTONE_ALREADY_CONFIRMED` | 409 | Повторное подтверждение этапа |

## 3. Эндпоинты

### 3.1 Служебные

| Метод | Путь | Ответ | Назначение |
| --- | --- | --- | --- |
| GET | `/api/health` | `Health` | Статус и цепочка AI-провайдеров: бейдж в шапке |
| GET | `/api/meta` | `Meta` | Справочники: поля, критерии и веса, уровни, темы. UI берёт подписи отсюда |
| POST | `/api/admin/reset` | `{ok: true}` | Пересоздать БД из `data/seed` (кнопка «Сбросить демо») |

```ts
interface Health {
  status: "ok";
  version: string;
  ai: { mode: "auto" | ProviderName; chain: { name: ProviderName; model: string; available: boolean }[] };
  embeddings: { chain: string[]; active: string };
}
interface Meta {
  fields: { key: FieldKey; label: string; criterion: CriterionKey | null; placeholder: string }[];
  criteria: { key: CriterionKey; label: string; weight: number; description: string }[];
  levels: Level[];
  topics: { key: string; label: string }[];
}
```

Темы (`topics`): `retail` Ритейл, `logistics` Логистика, `finance` Финансы, `education` Образование, `healthcare` Здравоохранение, `agro` Агро, `government` Госсектор, `manufacturing` Производство, `it_telecom` IT и телеком, `other` Другое.

### 3.2 Участники

| Метод | Путь | Тело | Ответ |
| --- | --- | --- | --- |
| GET | `/api/businesses` | — | `Business[]` |
| POST | `/api/businesses` | `{name, industry?}` | `Business` |
| GET | `/api/teams` | — | `Team[]` |
| GET | `/api/teams/{team_id}` | — | `Team` |

### 3.3 Конструктор задачи (бизнес)

| Метод | Путь | Тело | Ответ | Смысл |
| --- | --- | --- | --- | --- |
| POST | `/api/tasks` | `{business_id, draft_text, topic?}` | `201 TaskDetail` | Создать задачу из черновика: AI вытаскивает факты в `suggested`-поля и задаёт 3–5 вопросов. `status=clarifying` |
| GET | `/api/tasks?business_id=` | — | `TaskSummary[]` | «Мои задачи» |
| GET | `/api/tasks/{id}` | — | `TaskDetail` | |
| POST | `/api/tasks/{id}/answers` | `{answers: [{question_id, text}]}` | `TaskDetail` | Применить ответы, пустой ответ означает «пропустить». AI пересобирает карточку и трогает только `empty` и `suggested` поля. `status=review` |
| POST | `/api/tasks/{id}/clarify` | — | `TaskDetail` | Новый раунд вопросов по оставшимся пробелам: не больше 5, минимум 3, если пробелов не меньше 3 |
| PATCH | `/api/tasks/{id}/card` | `CardPatch` | `TaskDetail` | Правка и подтверждение полей, затем пересчёт рейтинга |
| POST | `/api/tasks/{id}/confirm-all` | — | `TaskDetail` | Подтвердить все `suggested`-поля |
| GET | `/api/tasks/{id}/rating` | — | `Rating` | |
| GET | `/api/tasks/{id}/history` | — | `ScoreEvent[]` | Для графика роста рейтинга |
| POST | `/api/tasks/{id}/publish` | `{confirm: true}` | `TaskDetail` | Публикация при любом рейтинге. Неподтверждённые поля не публикуются и не дают баллов |

```ts
interface CardPatch {
  fields: Partial<Record<FieldKey, {
    value?: string | null;   // передан → value, status=confirmed, source=user; null или "" → поле очищено (empty)
    confirm?: boolean;       // true без value → suggested становится confirmed
    reject?: boolean;        // true → suggested становится empty
  }>>;
}
```

### 3.4 Каталог (все роли)

| Метод | Путь | Ответ | Смысл |
| --- | --- | --- | --- |
| GET | `/api/catalog?topic=&level=&q=&sort=rating\|newest&limit=50&offset=0` | `{items: CatalogItem[], total: number}` | Все опубликованные задачи. Фильтры применяются только по явному выбору пользователя. По умолчанию `sort=rating` |
| GET | `/api/catalog/{task_id}` | `PublicTask` | Публичная карточка с расшифровкой рейтинга: студенты видят, насколько задача готова |

`level` можно передать несколько раз: `?level=ready&level=priority`.

### 3.5 Рекомендации (команда)

| Метод | Путь | Ответ |
| --- | --- | --- |
| GET | `/api/teams/{team_id}/recommendations?limit=5` | `{items: Recommendation[], method: string, note: string}` |

Сюда попадают только опубликованные задачи со `score ≥ 40`. `method` — например `"embeddings:nvidia/nemotron-3-embed-1b"` или `"tfidf"`. `note` всегда `"Рекомендации не ограничивают каталог: все задачи доступны во вкладке «Каталог»"`.

### 3.6 Отклики, решения, этапы

| Метод | Путь | Тело | Ответ | Смысл |
| --- | --- | --- | --- | --- |
| POST | `/api/tasks/{task_id}/proposals` | `{team_id, idea, plan, timeline, prototype_url?}` | `201 Proposal` | Любая команда на любую опубликованную задачу, без лимита |
| GET | `/api/tasks/{task_id}/proposals?business_id=` | — | `Proposal[]` | Отклики для владельца задачи |
| GET | `/api/teams/{team_id}/proposals` | — | `Proposal[]` | «Мои отклики» команды |
| POST | `/api/proposals/{id}/decision` | `{business_id, decision: "selected" \| "rejected", comment?}` | `Proposal` | Только ручное решение. Можно выбрать несколько, можно отклонить всех, можно изменить решение |
| POST | `/api/proposals/{id}/milestones` | `{business_id, title, points?}` | `201 Milestone` | Этап для выбранного отклика; `points` от 5 до 30, по умолчанию 10 |
| POST | `/api/milestones/{id}/confirm` | `{business_id}` | `{milestone: Milestone, team: Team}` | Бизнес подтверждает этап, команда получает баллы |
| GET | `/api/leaderboard/teams` | — | `{items: {rank: number, team: Team, confirmed_milestones: number}[]}` | Рейтинг команд по баллам прогресса |
| GET | `/api/leaderboard/businesses` | — | `{items: {rank: number, business: Business, avg_score: number, published_tasks: number}[]}` | Заказчики по среднему рейтингу опубликованных задач (качество, а не известность) |

Эндпоинтов, которые сами выбирают или назначают команду, **нет и не будет**.

### 3.7 AI-прозрачность и управление (зона A2)

| Метод | Путь | Тело | Ответ |
| --- | --- | --- | --- |
| GET | `/api/ai/traces?task_id=&limit=20` | — | `AiTrace[]` (новые сверху) |
| GET | `/api/ai/prompts` | — | `{name, version, system, user_template, output_schema}[]` |
| GET | `/api/ai/provider` | — | `{mode, chain, active}` |
| PUT | `/api/ai/provider` | `{mode: "auto" \| ProviderName}` | `{mode, chain, active}`: переключение на лету для демо |
| GET | `/api/ai/eval/latest` | — | P2: последний отчёт eval (метрики по провайдерам) |

## 4. Примеры

`POST /api/tasks`:

```json
{ "business_id": 1, "draft_text": "Хотим чат-бота для клиентов, чтобы меньше звонили в колл-центр.", "topic": "logistics" }
```

Ответ (сокращён):

```json
{
  "id": 7,
  "status": "clarifying",
  "card": {
    "title": { "value": "Чат-бот для клиентов", "status": "suggested", "source": "ai",
               "evidence": [{ "source": "draft", "quote": "чат-бота для клиентов" }], "updated_at": "2026-09-23T10:01:00Z" },
    "need":  { "value": "Меньше звонков клиентов в колл-центр", "status": "suggested", "source": "ai",
               "evidence": [{ "source": "draft", "quote": "чтобы меньше звонили в колл-центр" }], "updated_at": "2026-09-23T10:01:00Z" },
    "data":  { "value": null, "status": "empty", "source": null, "evidence": [], "updated_at": null }
  },
  "questions": [
    { "id": "q1", "field": "data", "question": "Какие данные об обращениях клиентов у вас есть: записи звонков, журнал заявок, FAQ? В каком формате и объёме?", "why": "Без данных команда не сможет обучить или проверить бота", "points_gain": 20, "answer": null, "round": 1 },
    { "id": "q2", "field": "context", "question": "Что происходит сейчас: сколько звонков в день и с какими вопросами чаще всего обращаются клиенты?", "why": "Команде нужно понимать масштаб и типовые вопросы", "points_gain": 10, "answer": null, "round": 1 },
    { "id": "q3", "field": "success_criteria", "question": "По какому измеримому показателю вы поймёте, что бот работает?", "why": "Нужен понятный критерий приёмки", "points_gain": 15, "answer": null, "round": 1 }
  ],
  "rating": { "score": 0, "potential_score": 27, "delta": 0, "level": { "key": "draft", "label": "Черновик", "min": 0, "max": 39 } },
  "catalog_position": null,
  "catalog_position_preview": 7,
  "ai": { "provider_used": "openai", "model": "gpt-6-luna", "degraded": false, "trace_ids": [31] }
}
```

`PATCH /api/tasks/7/card`:

```json
{ "fields": { "title": { "value": "Telegram-бот для ответов о статусе доставки" }, "need": { "confirm": true }, "users": { "reject": true } } }
```

`POST /api/proposals/12/decision`:

```json
{ "business_id": 1, "decision": "selected", "comment": "Нравится план пилота на 6 недель" }
```
