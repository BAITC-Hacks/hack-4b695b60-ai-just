import type {
  Business,
  Card,
  CardField,
  CriterionKey,
  FieldKey,
  Meta,
  Team,
  TaskDetail,
  Rating,
} from "../types";
export const DEMO_DRAFT =
  "Хотим чат-бота для клиентов, чтобы меньше звонили в колл-центр.";
export const demoAnswers: Partial<Record<FieldKey, string>> = {
  data: "Есть выгрузка обращений из CRM за 6 месяцев — около 12 000 записей в Excel, плюс FAQ на 40 вопросов. Данные обезличим и дадим доступ после NDA.",
  context:
    "Колл-центр получает 300–400 звонков в день, 60% — вопросы о статусе доставки и сроках.",
  success_criteria:
    "Бот самостоятельно закрывает не менее 40% обращений о статусе доставки, среднее время ответа — до 10 секунд.",
  constraints:
    "Пилот нужен за 6 недель, канал — Telegram, интеграция с нашей CRM через REST API.",
  contact: "Айгерим, руководитель клиентского сервиса, aigerim@example.com",
  interaction_format:
    "Созвон раз в неделю, оперативные вопросы — в Telegram-чате.",
  users: "Клиенты, ожидающие доставку, и операторы колл-центра",
};
const fieldRows: [FieldKey, string, CriterionKey | null, string][] = [
  ["title", "Название задачи", null, "Коротко назовите задачу"],
  [
    "context",
    "Контекст",
    "context_need",
    "Что происходит сейчас и где возникает проблема?",
  ],
  [
    "need",
    "Потребность",
    "context_need",
    "Что должно измениться после работы команды?",
  ],
  ["users", "Пользователи", "users", "Кто будет пользоваться решением?"],
  [
    "data",
    "Данные и материалы",
    "data",
    "Источник, формат, объём и условия доступа",
  ],
  [
    "constraints",
    "Ограничения",
    "constraints",
    "Сроки, технологии, доступы и бюджет",
  ],
  [
    "expected_result",
    "Ожидаемый результат",
    "expected_result",
    "Прототип, бот, дашборд или другой результат",
  ],
  [
    "success_criteria",
    "Критерии успеха",
    "success_criteria",
    "Как измерить, что задача решена?",
  ],
  ["contact", "Контакт", "business_link", "Email, телефон или Telegram"],
  [
    "interaction_format",
    "Формат взаимодействия",
    "business_link",
    "Как и насколько часто вы готовы общаться?",
  ],
];
export const meta: Meta = {
  fields: fieldRows.map(([key, label, criterion, placeholder]) => ({
    key,
    label,
    criterion,
    placeholder,
  })),
  criteria: [
    {
      key: "context_need",
      label: "Контекст и потребность",
      weight: 20,
      description: "Понятная и конкретная проблема",
    },
    {
      key: "data",
      label: "Данные и материалы",
      weight: 20,
      description: "Источник, формат и доступ",
    },
    {
      key: "expected_result",
      label: "Ожидаемый результат",
      weight: 15,
      description: "Конкретный артефакт",
    },
    {
      key: "success_criteria",
      label: "Критерии успеха",
      weight: 15,
      description: "Измеримый результат",
    },
    {
      key: "constraints",
      label: "Ограничения",
      weight: 10,
      description: "Сроки и технологии",
    },
    {
      key: "users",
      label: "Пользователи",
      weight: 10,
      description: "Роли и сегменты",
    },
    {
      key: "business_link",
      label: "Связь с бизнесом",
      weight: 10,
      description: "Контакт и обратная связь",
    },
  ],
  levels: [
    { key: "draft", label: "Черновик", min: 0, max: 39 },
    { key: "working", label: "Рабочая", min: 40, max: 69 },
    { key: "ready", label: "Готовая", min: 70, max: 89 },
    { key: "priority", label: "Приоритетная", min: 90, max: 100 },
  ],
  topics: [
    ["retail", "Ритейл"],
    ["logistics", "Логистика"],
    ["finance", "Финансы"],
    ["education", "Образование"],
    ["healthcare", "Здравоохранение"],
    ["agro", "Агро"],
    ["government", "Госсектор"],
    ["manufacturing", "Производство"],
    ["it_telecom", "IT и телеком"],
    ["other", "Другое"],
  ].map(([key, label]) => ({ key, label })),
};
export const businesses: Business[] = [
  "Дала Логистик",
  "Зерде Маркет",
  "Кадам Финанс",
  "Оркен Образование",
  "Таза Агро",
  "Сана Телеком",
].map((name, i) => ({ id: i + 1, name, industry: meta.topics[i].key }));
export const teams: Team[] = [
  "Nomad AI",
  "Qadam Tech",
  "Data Qazaq",
  "Steppe Builders",
  "Jas AI",
  "Digital Orda",
].map((name, i) => ({
  id: i + 1,
  name,
  interests: ["logistics", "education"],
  skills:
    i === 0
      ? ["Python", "NLP", "Telegram-боты"]
      : ["Аналитика", "React", "Python"],
  technologies: ["FastAPI", "React"],
  progress_points: 0,
}));
export const now = () => new Date().toISOString();
export function emptyCard(): Card {
  return Object.fromEntries(
    meta.fields.map((f) => [
      f.key,
      {
        value: null,
        status: "empty",
        source: null,
        evidence: [],
        updated_at: null,
      } as CardField,
    ]),
  ) as Card;
}
// Only the isolated mock adapter uses these rules. Live scores always come from the backend.
export function mockRating(card: Card, previous = 0): Rating {
  const rules: [
    CriterionKey,
    FieldKey,
    string,
    number,
    (s: string) => boolean,
  ][] = [
    ["context_need", "context", "Контекст описан", 6, () => true],
    ["context_need", "context", "Контекст подробный", 4, (s) => s.length >= 80],
    ["context_need", "need", "Потребность описана", 6, () => true],
    [
      "context_need",
      "need",
      "Потребность конкретная",
      4,
      (s) => s.length >= 60,
    ],
    ["data", "data", "Данные указаны", 10, () => true],
    [
      "data",
      "data",
      "Есть источник, формат или объём",
      6,
      (s) =>
        /\d|csv|xls|excel|json|sql|api|crm|erp|1с|база|бд|выгрузк|таблиц|датасет|лог|журнал|фото|видео|документ|отчёт|записей|строк/i.test(
          s,
        ),
    ],
    [
      "data",
      "data",
      "Понятны условия доступа",
      4,
      (s) =>
        /доступ|nda|предостав|переда|пример|образец|демо|обезлич|анонимиз|тестов|дадим/i.test(
          s,
        ),
    ],
    ["expected_result", "expected_result", "Результат описан", 8, () => true],
    [
      "expected_result",
      "expected_result",
      "Назван конкретный артефакт",
      7,
      (s) =>
        /прототип|mvp|бот|дашборд|модель|сервис|приложени|api|отчёт|сайт|скрипт|интеграц|панель|алгоритм|система/i.test(
          s,
        ),
    ],
    ["success_criteria", "success_criteria", "Критерии указаны", 7, () => true],
    [
      "success_criteria",
      "success_criteria",
      "Результат измерим",
      8,
      (s) => /\d|%|не менее|не более|минимум|максимум/i.test(s),
    ],
    ["constraints", "constraints", "Ограничения указаны", 5, () => true],
    [
      "constraints",
      "constraints",
      "Есть срок, технология или доступ",
      5,
      (s) =>
        /\d+\s*(дн|день|недел|месяц|мес|час|квартал)|\d{1,4}[./-]\d{1,2}[./-]\d{1,4}|python|java|react|1с|sql|postgres|docker|облак|сервер|telegram|whatsapp|android|ios|api|доступ|nda|vpn|бюджет|персональн/i.test(
          s,
        ),
    ],
    ["users", "users", "Пользователи указаны", 6, () => true],
    ["users", "users", "Описаны роли или сегмент", 4, (s) => s.length >= 20],
    [
      "business_link",
      "contact",
      "Есть рабочий контакт",
      5,
      (s) =>
        /[^\s@]+@[^\s@]+\.[^\s@]+|@\w{3,}|https?:\/\/|\+?\d[\d\s()-]{8,}/i.test(
          s,
        ),
    ],
    ["business_link", "interaction_format", "Формат указан", 3, () => true],
    [
      "business_link",
      "interaction_format",
      "Понятны частота или канал",
      2,
      (s) =>
        /раз в|еженедел|ежедн|каждый|созвон|встреч|звонок|чат|telegram|zoom|meet|почт|email|очно|онлайн|демо/i.test(
          s,
        ),
    ],
  ];
  const checks = rules.map(([criterion, field, label, points, check], i) => {
    const text = (card[field].value || "").trim().replace(/\s+/g, " ");
    const filled = text.replace(/\s/g, "").length >= 3;
    return {
      criterion,
      id: `check-${i}`,
      field,
      label,
      points,
      passed: card[field].status === "confirmed" && filled && check(text),
      potential: card[field].status !== "empty" && filled && check(text),
    };
  });
  const score = checks.reduce((n, c) => n + (c.passed ? c.points : 0), 0);
  const breakdown = meta.criteria.map((c) => ({
    criterion: c.key,
    label: c.label,
    max: c.weight,
    earned: checks
      .filter((x) => x.criterion === c.key && x.passed)
      .reduce((n, x) => n + x.points, 0),
    checks: checks
      .filter((x) => x.criterion === c.key)
      .map(({ id, field, label, points, passed }) => ({
        id,
        field,
        label,
        points,
        passed,
      })),
  }));
  const level = meta.levels.find((l) => score >= l.min && score <= l.max)!;
  const next = meta.levels.find((l) => l.min > score);
  const achievementNames = [
    "Понятная боль",
    "Данные на столе",
    "Ясная цель",
    "Измеримо",
    "Рамки заданы",
    "Знаем пользователя",
    "На связи",
  ];
  return {
    score,
    potential_score: checks.reduce(
      (n, c) => n + (c.potential ? c.points : 0),
      0,
    ),
    delta: score - previous,
    level,
    next_level: next
      ? { key: next.key, label: next.label, points_needed: next.min - score }
      : null,
    breakdown,
    missing: checks
      .filter((c) => !c.passed)
      .map((c) => ({
        check_id: c.id,
        criterion: c.criterion,
        field: c.field,
        hint: meta.fields.find((f) => f.key === c.field)!.placeholder,
        points_gain: c.points,
      }))
      .sort((a, b) => b.points_gain - a.points_gain),
    achievements: [
      ...breakdown.map((c, i) => ({
        key: c.criterion,
        label: achievementNames[i],
        description: c.label,
        earned: c.earned === c.max,
      })),
      {
        key: "perfect",
        label: "Идеальная карточка",
        description: "100 баллов готовности",
        earned: score === 100,
      },
    ],
  };
}
export function makeTask(
  id: number,
  businessId: number,
  draft: string,
  topic: string | null,
): TaskDetail {
  const card = emptyCard();
  return {
    id,
    business: businesses.find((b) => b.id === businessId)!,
    status: "clarifying",
    topic,
    draft_text: draft,
    card,
    questions: [],
    rating: mockRating(card),
    catalog_position: null,
    catalog_position_preview: 7,
    proposals_count: 0,
    ai: null,
    created_at: now(),
    updated_at: now(),
    published_at: null,
  };
}
export function seedTasks(): TaskDetail[] {
  const titles = [
    "Прогноз спроса для сети магазинов",
    "Поиск по базе знаний для студентов",
    "Контроль качества урожая по фото",
    "Аналитика обращений в поддержку",
    "Умный помощник для финансовых отчётов",
    "Автоматизация маршрутов доставки",
  ];
  const needs = [
    "Помогите планировать закупки и сократить списания: нужна модель прогноза спроса на товары по истории продаж.",
    "Студентам нужен быстрый поиск ответов в учебных материалах с указанием источников.",
    "Определять качество овощей по фотографии, чтобы ускорить сортировку на складе.",
    "Разделять обращения по темам и показывать наиболее частые проблемы пользователей.",
    "Ускорить подготовку ежемесячного финансового отчёта из нескольких таблиц.",
    "Хотим оптимизировать маршруты курьеров.",
  ];
  return titles.map((title, i) => {
    const t = makeTask(
      i + 1,
      i + 1,
      needs[i],
      ["retail", "education", "agro", "it_telecom", "finance", "logistics"][i],
    );
    const values: Partial<Record<FieldKey, string>> = {
      title,
      need: needs[i],
      users: "Аналитики и сотрудники операционного отдела",
      expected_result: "Рабочий прототип приложения с документацией",
      context:
        "Сейчас сотрудники обрабатывают заявки вручную в таблицах. Это занимает несколько часов каждый день и приводит к повторным ошибкам.",
      data: "Обезличенная выгрузка CRM в Excel, 12 000 строк; дадим тестовый доступ.",
      success_criteria: "Сократить время обработки не менее чем на 40%",
      constraints: "Пилот за 6 недель на Python",
      contact: "team@example.com",
      interaction_format: "Созвон раз в неделю",
    };
    const keep =
      i === 0 ? 10 : i === 1 ? 9 : i === 2 ? 8 : i === 3 ? 6 : i === 4 ? 5 : 2;
    Object.entries(values)
      .slice(0, keep)
      .forEach(([key, value]) => {
        t.card[key as FieldKey] = {
          value,
          status: "confirmed",
          source: "user",
          evidence: [],
          updated_at: now(),
        };
      });
    t.status = "published";
    t.published_at = new Date(Date.UTC(2026, 8, 20, i)).toISOString();
    t.rating = mockRating(t.card);
    return t;
  });
}
