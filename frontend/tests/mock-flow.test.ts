import { beforeAll, describe, expect, test } from "vitest";
import { emptyCard, mockRating } from "../src/api/mock/fixtures";
import type { FieldKey, Proposal, TaskDetail, Team } from "../src/api/types";
let mock: typeof import("../src/api/mock/server").mockRequest;
beforeAll(async () => {
  const memory = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    value: {
      getItem: (k: string) => memory.get(k) || null,
      setItem: (k: string, v: string) => memory.set(k, v),
      removeItem: (k: string) => memory.delete(k),
    },
    configurable: true,
  });
  mock = (await import("../src/api/mock/server")).mockRequest;
});
describe("Демонстрационный контракт", () => {
  test("баллы появляются только после подтверждения, веса дают 100", () => {
    const card = emptyCard();
    card.data = {
      value: "Excel, 12000 строк, дадим доступ после NDA",
      status: "suggested",
      source: "ai",
      evidence: [],
      updated_at: null,
    };
    expect(mockRating(card).score).toBe(0);
    expect(mockRating(card).potential_score).toBe(20);
    card.data.status = "confirmed";
    expect(mockRating(card).score).toBe(20);
    expect(mockRating(card).breakdown.reduce((n, c) => n + c.max, 0)).toBe(100);
  });
  test("золотой пример рейтинга: 27 → 76 → 96 → 100", () => {
    const card = emptyCard();
    const fill = (field: FieldKey, value: string) => {
      card[field] = {
        value,
        status: "confirmed",
        source: "user",
        evidence: [],
        updated_at: null,
      };
    };
    fill("need", "Меньше звонков клиентов в колл-центр");
    fill("users", "Клиенты");
    fill("expected_result", "Чат-бот для клиентов");
    expect(mockRating(card).score).toBe(27);
    fill(
      "context",
      "Колл-центр получает 300–400 звонков в день, 60% — вопросы о статусе доставки и сроках.",
    );
    fill(
      "need",
      "Уменьшить количество звонков клиентов в колл-центр по вопросам доставки и срокам заказов",
    );
    fill(
      "data",
      "Выгрузка CRM: 12 000 записей в Excel, обезличим и дадим доступ после NDA",
    );
    fill(
      "success_criteria",
      "Не менее 40% обращений закрыты, ответ до 10 секунд",
    );
    expect(mockRating(card).score).toBe(76);
    fill("constraints", "Пилот за 6 недель, Telegram, REST API");
    fill("contact", "aigerim@example.com");
    fill("interaction_format", "Созвон раз в неделю, вопросы в Telegram-чате");
    expect(mockRating(card).score).toBe(96);
    fill("users", "Клиенты, ожидающие доставку, и операторы колл-центра");
    expect(mockRating(card).score).toBe(100);
  });
  test("AI не заменяет подтверждённое, публичная карточка исключает предложенное", async () => {
    await mock("/admin/reset", "POST");
    const t = (await mock("/tasks", "POST", {
      business_id: 1,
      draft_text: "Нужен бот для автоматизации поддержки клиентов",
      topic: "it_telecom",
    })) as TaskDetail;
    expect(t.questions.length).toBeGreaterThanOrEqual(3);
    await mock(`/tasks/${t.id}/card`, "PATCH", {
      fields: {
        data: { value: "Подтверждённые данные" },
        title: { value: "Проверенное название" },
      },
    });
    const q = t.questions.find((q) => q.field === "data")!;
    const updated = (await mock(`/tasks/${t.id}/answers`, "POST", {
      answers: [
        { question_id: q.id, text: "Новый ответ не должен перезаписать поле" },
      ],
    })) as TaskDetail;
    expect(updated.card.data.value).toBe("Подтверждённые данные");
    await mock(`/tasks/${t.id}/publish`, "POST", { confirm: true });
    const pub = (await mock(`/catalog/${t.id}`)) as {
      card: Record<string, string>;
    };
    expect(pub.card.need).toBeUndefined();
    expect(pub.card.title).toBe("Проверенное название");
  });
  test("решение только владельцем, этап начисляет баллы один раз", async () => {
    const p = (await mock("/tasks/1/proposals", "POST", {
      team_id: 1,
      idea: "Идея решения задачи с помощью прототипа",
      plan: "Разобрать данные и провести пилотное тестирование",
      timeline: "6 недель",
      prototype_url: null,
    })) as Proposal;
    await expect(
      mock(`/proposals/${p.id}/decision`, "POST", {
        business_id: 2,
        decision: "selected",
      }),
    ).rejects.toThrow("владелец");
    await expect(
      mock(`/proposals/${p.id}/milestones`, "POST", {
        business_id: 1,
        title: "Пилот",
        points: 10,
      }),
    ).rejects.toThrow("выберите");
    await mock(`/proposals/${p.id}/decision`, "POST", {
      business_id: 1,
      decision: "selected",
    });
    const m = (await mock(`/proposals/${p.id}/milestones`, "POST", {
      business_id: 1,
      title: "Пилот",
      points: 10,
    })) as { id: number };
    const result = (await mock(`/milestones/${m.id}/confirm`, "POST", {
      business_id: 1,
    })) as { team: Team };
    expect(result.team.progress_points).toBe(10);
    await expect(
      mock(`/milestones/${m.id}/confirm`, "POST", { business_id: 1 }),
    ).rejects.toThrow("уже подтверждён");
  });
});
