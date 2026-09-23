import type {
  AiTrace,
  CatalogItem,
  CardPatch,
  FieldKey,
  Proposal,
  ScoreEvent,
  TaskDetail,
  Team,
} from "../types";
import { ApiError } from "../client";
import {
  businesses,
  emptyCard,
  makeTask,
  meta,
  mockRating,
  now,
  seedTasks,
  teams as seedTeams,
} from "./fixtures";
interface State {
  tasks: TaskDetail[];
  teams: Team[];
  proposals: Proposal[];
  history: Record<number, ScoreEvent[]>;
  traces: AiTrace[];
}
const STORAGE = "ai-sana-mock-v1";
function initial(): State {
  return {
    tasks: seedTasks(),
    teams: structuredClone(seedTeams),
    proposals: [],
    history: {},
    traces: [],
  };
}
function restore(): State {
  try {
    return (
      (JSON.parse(localStorage.getItem(STORAGE) || "null") as State) ||
      initial()
    );
  } catch {
    return initial();
  }
}
let state = restore();
function persist() {
  localStorage.setItem(STORAGE, JSON.stringify(state));
}
function fail(message: string, status = 400): never {
  throw new ApiError(message, status);
}
function findTask(id: number) {
  return state.tasks.find((t) => t.id === id) || fail("Задача не найдена", 404);
}
function rank() {
  return state.tasks
    .filter((t) => t.status === "published")
    .sort(
      (a, b) =>
        b.rating.score - a.rating.score ||
        (a.published_at || "").localeCompare(b.published_at || "") ||
        a.id - b.id,
    );
}
function update(t: TaskDetail, reason: string) {
  t.rating = mockRating(t.card, t.rating.score);
  t.updated_at = now();
  if (t.rating.delta || !state.history[t.id]?.length || reason === "Публикация")
    (state.history[t.id] ??= []).push({
      score: t.rating.score,
      delta: t.rating.delta,
      level: t.rating.level.key,
      reason,
      created_at: now(),
    });
  persist();
  return detail(t);
}
function detail(t: TaskDetail) {
  return {
    ...t,
    catalog_position:
      t.status === "published"
        ? rank().findIndex((x) => x.id === t.id) + 1
        : null,
    catalog_position_preview:
      rank().filter((x) => x.id !== t.id && x.rating.score >= t.rating.score)
        .length + 1,
    proposals_count: state.proposals.filter((p) => p.task.id === t.id).length,
  };
}
function catalog(): CatalogItem[] {
  return rank().map((t, i) => ({
    id: t.id,
    title: t.card.title.value || "Без названия",
    topic: t.topic,
    business_name: t.business.name,
    score: t.rating.score,
    level: t.rating.level,
    highlighted: t.rating.level.key === "priority",
    needs_clarification: t.rating.level.key === "draft",
    need_preview:
      t.card.need.status === "confirmed"
        ? (t.card.need.value || "").slice(0, 160)
        : "",
    proposals_count: detail(t).proposals_count,
    position: i + 1,
    published_at: t.published_at!,
  }));
}
function suggest(
  t: TaskDetail,
  field: FieldKey,
  value: string,
  source = "draft",
  quote = value,
) {
  if (t.card[field].status !== "confirmed")
    t.card[field] = {
      value,
      status: "suggested",
      source: "ai",
      evidence: [{ source, quote }],
      updated_at: now(),
    };
}
function questions(t: TaskDetail) {
  const round = Math.max(0, ...t.questions.map((q) => q.round)) + 1;
  const fields: FieldKey[] = [
    "data",
    "context",
    "success_criteria",
    "constraints",
    "contact",
    "interaction_format",
    "users",
    "need",
    "expected_result",
  ];
  const missing = fields.filter((f) => t.card[f].status !== "confirmed");
  const count =
    round === 1
      ? Math.max(3, Math.min(5, missing.length))
      : Math.min(5, missing.length);
  for (const field of missing.slice(0, count))
    t.questions.push({
      id: `q${t.questions.length + 1}`,
      field,
      question:
        meta.fields
          .find((f) => f.key === field)!
          .placeholder.replace(/[?？]+$/, "") + "?",
      why: "Это поможет команде оценить задачу и предложить конкретный план.",
      points_gain:
        field === "context" || field === "need"
          ? 10
          : field === "contact" || field === "interaction_format"
            ? 5
            : meta.criteria.find(
                (c) =>
                  c.key === meta.fields.find((f) => f.key === field)!.criterion,
              )?.weight || 5,
      answer: null,
      round,
    });
}
function trace(t: TaskDetail, operation: string) {
  const redact = (s: string) =>
    s
      .replace(/[\w.+-]+@[\w.-]+\.[a-z]{2,}/gi, "[EMAIL]")
      .replace(/\+?\d[\d ()-]{8,}\d/g, "[PHONE]")
      .replace(/@[\w]+/g, "[HANDLE]");
  state.traces.unshift({
    id: state.traces.length + 1,
    task_id: t.id,
    operation,
    provider: "stub",
    model: "frontend-demo-fixture",
    prompt_version: "demo.v1",
    status: "fallback",
    input_redacted: redact(
      t.draft_text + "\n" + t.questions.map((q) => q.answer || "").join("\n"),
    ),
    raw_output: redact(JSON.stringify(t.card, null, 2)),
    parsed: JSON.parse(redact(JSON.stringify(t.card))),
    errors: ["Демонстрационная запись frontend, реальный AI не вызывался."],
    grounding_rejected: [],
    latency_ms: 0,
    created_at: now(),
  });
  t.ai = {
    provider_used: "stub",
    model: "frontend-demo-fixture",
    degraded: true,
    trace_ids: [state.traces[0].id],
  };
}
function owner(proposal: Proposal, business: number) {
  if (findTask(proposal.task.id).business.id !== business)
    fail("Только владелец задачи может принять решение", 403);
}
export async function mockRequest(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<unknown> {
  await new Promise((resolve) => setTimeout(resolve, 180));
  const url = new URL(path, "http://mock.local");
  const p = url.pathname;
  const query = url.searchParams;
  const data = (body || {}) as Record<string, unknown>;
  let result: unknown;
  if (p === "/meta") result = meta;
  else if (p === "/health")
    result = {
      status: "ok",
      version: "demo",
      ai: {
        mode: "stub",
        chain: [
          { name: "stub", model: "frontend-demo-fixture", available: true },
        ],
      },
      embeddings: { chain: ["demo"], active: "demo" },
    };
  else if (p === "/businesses") result = businesses;
  else if (p === "/teams") result = state.teams;
  else if (p === "/admin/reset") {
    state = initial();
    persist();
    result = { ok: true };
  } else if (p === "/ai/provider") {
    if (data.mode !== "stub" && data.mode !== "auto")
      fail(
        "В демо доступен только офлайн-провайдер. Подключите backend для реального AI.",
      );
    result = {
      mode: "stub",
      chain: [
        { name: "stub", model: "frontend-demo-fixture", available: true },
      ],
      active: "stub",
    };
  } else if (p === "/ai/traces")
    result = state.traces.filter(
      (t) => t.task_id === Number(query.get("task_id")),
    );
  else if (p === "/ai/prompts")
    result = [
      {
        name: "Демонстрационная заглушка frontend",
        version: "demo.v1",
        system:
          "AI не вызывается. Предлагаются только фрагменты введённого текста. Подтверждённые поля сохраняются.",
        user_template: "Текст черновика и ответы автора",
        output_schema: {
          type: "object",
          description:
            "Реальные промпты и JSON-схемы появятся после подключения backend.",
        },
      },
    ];
  else if (p === "/leaderboard/teams")
    result = {
      items: [...state.teams]
        .sort((a, b) => b.progress_points - a.progress_points || a.id - b.id)
        .map((team, i) => ({
          rank: i + 1,
          team,
          confirmed_milestones: state.proposals
            .filter((p) => p.team.id === team.id)
            .flatMap((p) => p.milestones)
            .filter((m) => m.status === "confirmed").length,
        })),
    };
  else if (p === "/catalog") {
    let items = catalog();
    const levels = query.getAll("level");
    const search = (query.get("q") || "").toLocaleLowerCase();
    if (query.get("topic"))
      items = items.filter((t) => t.topic === query.get("topic"));
    if (levels.length)
      items = items.filter((t) => levels.includes(t.level.key));
    if (search)
      items = items.filter((t) =>
        `${t.title} ${t.need_preview}`.toLocaleLowerCase().includes(search),
      );
    if (query.get("sort") === "newest")
      items.sort((a, b) => b.published_at.localeCompare(a.published_at));
    result = {
      total: items.length,
      items: items.slice(
        Number(query.get("offset") || 0),
        Number(query.get("offset") || 0) + Number(query.get("limit") || 50),
      ),
    };
  } else if (/^\/catalog\/\d+$/.test(p)) {
    const t = findTask(Number(p.split("/")[2]));
    if (t.status !== "published") fail("Задача ещё не опубликована", 404);
    result = {
      id: t.id,
      title: t.card.title.value,
      topic: t.topic,
      business_name: t.business.name,
      card: Object.fromEntries(
        Object.entries(t.card)
          .filter(([, f]) => f.status === "confirmed")
          .map(([k, f]) => [k, f.value]),
      ),
      rating: t.rating,
      position: detail(t).catalog_position,
      proposals_count: detail(t).proposals_count,
      published_at: t.published_at,
    };
  } else if (/^\/teams\/\d+\/recommendations$/.test(p)) {
    const team = state.teams.find((t) => t.id === Number(p.split("/")[2]))!;
    result = {
      method: "demo: совпадение тем",
      note: "Рекомендации не ограничивают каталог: все задачи доступны во вкладке «Каталог»",
      items: catalog()
        .filter((t) => t.score >= 40 && team.interests.includes(t.topic || ""))
        .slice(0, 5)
        .map((t) => ({
          task: t,
          match: 0.75,
          reasons: [
            "Тема совпадает с интересами команды",
            "Карточка готова к обсуждению",
          ],
          matched_terms: [
            meta.topics.find((x) => x.key === t.topic)?.label || "",
          ],
        })),
    };
  } else if (/^\/teams\/\d+\/proposals$/.test(p))
    result = state.proposals.filter(
      (t) => t.team.id === Number(p.split("/")[2]),
    );
  else if (p === "/tasks" && method === "GET")
    result = state.tasks
      .filter((t) => t.business.id === Number(query.get("business_id")))
      .map((t) => ({
        id: t.id,
        title: t.card.title.value,
        status: t.status,
        topic: t.topic,
        score: t.rating.score,
        level: t.rating.level,
        proposals_count: detail(t).proposals_count,
        updated_at: t.updated_at,
      }));
  else if (p === "/tasks" && method === "POST") {
    const text = String(data.draft_text || "").trim();
    if (text.length < 10 || text.length > 4000)
      fail("Черновик должен содержать от 10 до 4000 символов");
    const t = makeTask(
      Math.max(0, ...state.tasks.map((t) => t.id)) + 1,
      Number(data.business_id),
      text,
      data.topic as string | null,
    );
    if (!t.business) fail("Выберите бизнес");
    suggest(t, "title", text.slice(0, 100));
    suggest(t, "need", text);
    if (/чат-бота для клиентов/i.test(text)) {
      suggest(t, "expected_result", "чат-бота для клиентов");
      suggest(t, "users", "клиентов");
      const need = text.match(/чтобы[^.!?]+/i)?.[0];
      if (need) suggest(t, "need", need);
    }
    questions(t);
    trace(t, "analyze_draft");
    state.tasks.push(t);
    result = update(t, "Черновик создан");
  } else if (/^\/tasks\/\d+/.test(p)) {
    const id = Number(p.split("/")[2]);
    const action = p.split("/")[3];
    const t = findTask(id);
    if (!action) result = detail(t);
    else if (action === "history") result = state.history[id] || [];
    else if (action === "rating") result = t.rating;
    else if (action === "answers") {
      for (const answer of data.answers as {
        question_id: string;
        text: string;
      }[]) {
        const q = t.questions.find((q) => q.id === answer.question_id);
        if (q) {
          q.answer = answer.text;
          if (answer.text.trim())
            suggest(
              t,
              q.field,
              answer.text.trim(),
              `answer:${q.id}`,
              answer.text.trim(),
            );
        }
      }
      t.status = t.status === "published" ? "published" : "review";
      trace(t, "build_card");
      result = update(t, "Ответы применены");
    } else if (action === "clarify") {
      questions(t);
      trace(t, "analyze_draft");
      result = update(t, "Новый раунд вопросов");
    } else if (action === "card") {
      const fields = data.fields as CardPatch["fields"];
      for (const key of Object.keys(fields) as FieldKey[]) {
        const change = fields[key]!;
        if ("value" in change)
          t.card[key] = change.value?.trim()
            ? {
                value: change.value.trim(),
                status: "confirmed",
                source: "user",
                evidence: [],
                updated_at: now(),
              }
            : emptyCard()[key];
        else if (change.confirm && t.card[key].status === "suggested")
          t.card[key].status = "confirmed";
        else if (change.reject && t.card[key].status === "suggested")
          t.card[key] = emptyCard()[key];
      }
      result = update(t, "Карточка обновлена");
    } else if (action === "confirm-all") {
      Object.values(t.card).forEach((f) => {
        if (f.status === "suggested") f.status = "confirmed";
      });
      result = update(t, "Предложения подтверждены");
    } else if (action === "publish") {
      if (!data.confirm) fail("Подтвердите публикацию");
      if (t.card.title.status !== "confirmed" || !t.card.title.value)
        fail("Подтвердите название задачи", 409);
      t.status = "published";
      t.published_at ||= now();
      result = update(t, "Публикация");
    } else if (action === "proposals" && method === "GET") {
      if (t.business.id !== Number(query.get("business_id")))
        fail("Отклики доступны владельцу задачи", 403);
      result = state.proposals.filter((p) => p.task.id === id);
    } else if (action === "proposals") {
      if (t.status !== "published") fail("Задача ещё не опубликована");
      const team = state.teams.find((t) => t.id === Number(data.team_id));
      if (!team) fail("Выберите команду");
      if (
        String(data.idea).trim().length < 20 ||
        String(data.plan).trim().length < 20
      )
        fail("Идея и план: не менее 20 символов");
      const proposal: Proposal = {
        id: Math.max(0, ...state.proposals.map((p) => p.id)) + 1,
        task: { id, title: t.card.title.value || "" },
        team,
        idea: String(data.idea).trim(),
        plan: String(data.plan).trim(),
        timeline: String(data.timeline),
        prototype_url: data.prototype_url as string | null,
        status: "submitted",
        business_comment: null,
        milestones: [],
        created_at: now(),
        decided_at: null,
      };
      state.proposals.push(proposal);
      persist();
      result = proposal;
    }
  } else if (/^\/proposals\/\d+/.test(p)) {
    const proposal =
      state.proposals.find((p1) => p1.id === Number(p.split("/")[2])) ||
      fail("Отклик не найден", 404);
    owner(proposal, Number(data.business_id));
    if (p.endsWith("/decision")) {
      proposal.status = data.decision as "selected" | "rejected";
      proposal.business_comment = String(data.comment || "");
      proposal.decided_at = now();
      result = proposal;
    } else if (p.endsWith("/milestones")) {
      if (proposal.status !== "selected") fail("Сначала выберите команду");
      const points = Number(data.points ?? 10);
      if (
        points < 5 ||
        points > 30 ||
        !Number.isInteger(points) ||
        !String(data.title || "").trim()
      )
        fail("Укажите название и от 5 до 30 баллов");
      const m = {
        id:
          Math.max(
            0,
            ...state.proposals.flatMap((p) => p.milestones).map((m) => m.id),
          ) + 1,
        proposal_id: proposal.id,
        title: String(data.title),
        points,
        status: "pending" as const,
        confirmed_at: null,
      };
      proposal.milestones.push(m);
      result = m;
    }
    persist();
  } else if (/^\/milestones\/\d+\/confirm$/.test(p)) {
    const id = Number(p.split("/")[2]);
    const proposal =
      state.proposals.find((p) => p.milestones.some((m) => m.id === id)) ||
      fail("Этап не найден", 404);
    owner(proposal, Number(data.business_id));
    if (proposal.status !== "selected") fail("Команда не выбрана");
    const milestone = proposal.milestones.find((m) => m.id === id)!;
    if (milestone.status === "confirmed") fail("Этап уже подтверждён", 409);
    milestone.status = "confirmed";
    milestone.confirmed_at = now();
    const team = state.teams.find((t) => t.id === proposal.team.id)!;
    team.progress_points += milestone.points;
    state.proposals
      .filter((p) => p.team.id === team.id)
      .forEach((p) => {
        p.team = team;
      });
    persist();
    result = { milestone, team };
  }
  if (result === undefined)
    fail("Этот запрос недоступен в демонстрационном режиме", 404);
  return structuredClone(result);
}
