import type {
  AiTrace,
  Business,
  CardPatch,
  CatalogItem,
  Health,
  Meta,
  Milestone,
  Proposal,
  ProviderName,
  ProviderState,
  PublicTask,
  Recommendation,
  ScoreEvent,
  TaskDetail,
  TaskSummary,
  Team,
} from "./types";
export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";
export class ApiError extends Error {
  status: number;
  code: string;
  constructor(message: string, status = 500, code = "") {
    super(message);
    this.status = status;
    this.code = code;
  }
}
export async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  if (USE_MOCKS) {
    const { mockRequest } = await import("./mock/server");
    return mockRequest(path, method, body) as Promise<T>;
  }
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers:
        body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(90000),
    });
  } catch {
    throw new ApiError(
      "Не удалось связаться с сервером. Проверьте подключение и запуск backend.",
      0,
    );
  }
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data ? data.detail : null;
    if (detail && typeof detail === "object" && "message" in detail)
      throw new ApiError(
        String(detail.message),
        response.status,
        "code" in detail ? String(detail.code) : "",
      );
    if (Array.isArray(detail))
      throw new ApiError(
        "Проверьте заполненные поля: сервер отклонил данные.",
        response.status,
        "VALIDATION_ERROR",
      );
    throw new ApiError(
      response.status === 404
        ? "Запись не найдена."
        : "Сервер не смог выполнить запрос. Попробуйте ещё раз.",
      response.status,
    );
  }
  return data as T;
}
export interface Prompt {
  name: string;
  version: string;
  system: string;
  user_template: string;
  output_schema: unknown;
}
export const api = {
  meta: () => request<Meta>("/meta"),
  health: () => request<Health>("/health"),
  businesses: () => request<Business[]>("/businesses"),
  teams: () => request<Team[]>("/teams"),
  provider: (mode: "auto" | ProviderName) =>
    request<ProviderState>("/ai/provider", "PUT", { mode }),
  reset: () => request<{ ok: true }>("/admin/reset", "POST"),
  create: (business_id: number, draft_text: string, topic: string) =>
    request<TaskDetail>("/tasks", "POST", {
      business_id,
      draft_text,
      topic: topic || null,
    }),
  task: (id: number) => request<TaskDetail>(`/tasks/${id}`),
  tasks: (id: number) => request<TaskSummary[]>(`/tasks?business_id=${id}`),
  answers: (id: number, answers: { question_id: string; text: string }[]) =>
    request<TaskDetail>(`/tasks/${id}/answers`, "POST", { answers }),
  patch: (id: number, fields: CardPatch["fields"]) =>
    request<TaskDetail>(`/tasks/${id}/card`, "PATCH", { fields }),
  confirm: (id: number) =>
    request<TaskDetail>(`/tasks/${id}/confirm-all`, "POST"),
  clarify: (id: number) => request<TaskDetail>(`/tasks/${id}/clarify`, "POST"),
  publish: (id: number) =>
    request<TaskDetail>(`/tasks/${id}/publish`, "POST", { confirm: true }),
  history: (id: number) => request<ScoreEvent[]>(`/tasks/${id}/history`),
  catalog: (params: URLSearchParams = new URLSearchParams()) =>
    request<{ items: CatalogItem[]; total: number }>(`/catalog?${params}`),
  publicTask: (id: number) => request<PublicTask>(`/catalog/${id}`),
  recommendations: (id: number) =>
    request<{ items: Recommendation[]; method: string; note: string }>(
      `/teams/${id}/recommendations?limit=5`,
    ),
  propose: (
    id: number,
    body: {
      team_id: number;
      idea: string;
      plan: string;
      timeline: string;
      prototype_url: string | null;
    },
  ) => request<Proposal>(`/tasks/${id}/proposals`, "POST", body),
  proposals: (id: number, business: number) =>
    request<Proposal[]>(`/tasks/${id}/proposals?business_id=${business}`),
  teamProposals: (id: number) => request<Proposal[]>(`/teams/${id}/proposals`),
  decision: (
    id: number,
    business_id: number,
    decision: "selected" | "rejected",
    comment: string,
  ) =>
    request<Proposal>(`/proposals/${id}/decision`, "POST", {
      business_id,
      decision,
      comment,
    }),
  milestone: (id: number, business_id: number, title: string, points: number) =>
    request<Milestone>(`/proposals/${id}/milestones`, "POST", {
      business_id,
      title,
      points,
    }),
  confirmMilestone: (id: number, business_id: number) =>
    request<{ milestone: Milestone; team: Team }>(
      `/milestones/${id}/confirm`,
      "POST",
      { business_id },
    ),
  leaderboard: () =>
    request<{
      items: { rank: number; team: Team; confirmed_milestones: number }[];
    }>("/leaderboard/teams"),
  traces: (id: number) =>
    request<AiTrace[]>(`/ai/traces?task_id=${id}&limit=20`),
  prompts: () => request<Prompt[]>("/ai/prompts"),
};
