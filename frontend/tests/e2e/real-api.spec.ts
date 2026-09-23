import { expect, test, type Page } from "@playwright/test";

const API = process.env.E2E_API_URL;
const answers = {
  data: "Есть выгрузка обращений из CRM за 6 месяцев — около 12 000 записей в Excel, плюс FAQ на 40 вопросов. Данные обезличим и дадим доступ после NDA.",
  context:
    "Колл-центр получает 300–400 звонков в день, 60% — вопросы о статусе доставки и сроках.",
  success_criteria:
    "Бот самостоятельно закрывает не менее 40% обращений о статусе доставки, среднее время ответа — до 10 секунд.",
};
const contact = "aigerim" + "@" + "example.com";

const score = (page: Page) => page.locator(".score-ring strong");

test.beforeEach(async ({ request }) => {
  if (!API || API !== `${process.env.API_PROXY_TARGET}/api`) {
    throw new Error(
      "Укажите E2E_API_URL и API_PROXY_TARGET для одного отдельного тестового backend: сценарий сбрасывает его базу.",
    );
  }
  const reset = await request.post(`${API}/admin/reset`);
  expect(reset.ok()).toBeTruthy();
});

test("Настоящий API: черновик → публикация → отклик → решение → баллы", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/builder");
  await page.getByRole("button", { name: "Попробовать пример" }).click();
  await page
    .getByRole("combobox", { name: "Тема задачи", exact: true })
    .click();
  await page.getByRole("option", { name: "Логистика", exact: true }).click();
  await page
    .getByRole("button", { name: "Проанализировать", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Уточним самое важное" }),
  ).toBeVisible();
  const taskId = page.url().split("/").pop()!;
  await expect(score(page)).toHaveText("0");
  await page
    .getByRole("button", { name: "Подтвердить всё", exact: true })
    .click();
  await expect(score(page)).toHaveText("31");

  await page.locator("#q1").fill(answers.data);
  await page.locator("#q2").fill(answers.context);
  await page.locator("#q3").fill(answers.success_criteria);
  await page.getByRole("button", { name: "Собрать карточку" }).click();
  await expect(
    page.getByRole("heading", { name: "Сделаем задачу понятной" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Подтвердить всё", exact: true })
    .click();
  await expect(async () => {
    expect(Number(await score(page).textContent())).toBeGreaterThanOrEqual(70);
  }).toPass();

  const edit = async (key: string, value: string) => {
    const section = page.locator(`#field-section-${key}`);
    const input = section.locator(`#field-${key}`);
    if (!(await input.isVisible())) {
      await section.locator(".field-heading").click();
    }
    await expect(input).toHaveAttribute("maxlength", "2000");
    await input.fill(value);
    await section
      .getByRole("button", { name: "Сохранить", exact: true })
      .click();
    await expect(
      section.getByText("Подтверждено", { exact: true }),
    ).toBeVisible();
  };
  await edit("title", "Telegram-бот для ответов о статусе доставки");
  await edit(
    "need",
    "Уменьшить количество звонков клиентов в колл-центр по вопросам доставки и срокам заказов",
  );
  await edit(
    "constraints",
    "Пилот за 6 недель, Telegram, интеграция через REST API",
  );
  await edit("contact", contact);
  await edit(
    "interaction_format",
    "Созвон раз в неделю, вопросы в Telegram-чате",
  );
  await edit("users", "Клиенты, ожидающие доставку, и операторы колл-центра");
  await expect(score(page)).toHaveText("100");

  await page.getByRole("button", { name: "Опубликовать задачу" }).click();
  await page.getByLabel("Я проверил карточку").check();
  await page.getByRole("button", { name: "Опубликовать", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Задача опубликована!" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Команда", exact: true }).click();
  await page.getByRole("link", { name: "Рекомендации", exact: true }).click();
  await expect(
    page.getByText("Рекомендации не ограничивают каталог."),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Смотреть все задачи →", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Задачи с реальным смыслом",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("link")
    .filter({
      has: page.getByRole("heading", {
        name: "Telegram-бот для ответов о статусе доставки",
      }),
    })
    .click();
  await page
    .getByLabel("Идея · от 20 символов")
    .fill(
      "Telegram-бот на базе LLM с поиском по FAQ и статусом заказа из CRM через REST API.",
    );
  await page
    .getByLabel("План · от 20 символов")
    .fill(
      "Разбор обращений и FAQ. Прототип бота. Интеграция статуса доставки. Пилот на 10% клиентов.",
    );
  await page.getByLabel("Срок", { exact: true }).fill("6 недель");
  await page.getByRole("button", { name: "Отправить отклик" }).click();
  await expect(
    page.getByText("Отклик отправлен.", { exact: false }).first(),
  ).toBeVisible();

  await page.getByRole("button", { name: "Бизнес", exact: true }).click();
  await page
    .locator(".my-task-row")
    .filter({ hasText: "Telegram-бот для ответов о статусе доставки" })
    .getByRole("link", { name: /Отклики/ })
    .click();
  const comment = page.getByLabel("Комментарий · необязательно");
  await expect(comment).toHaveAttribute("maxlength", "500");
  await comment.fill("Проверили прототип. ".repeat(25));
  await page.getByRole("button", { name: "Выбрать", exact: true }).click();
  await expect(page.getByText("Выбрана", { exact: true })).toBeVisible();
  await page.getByLabel("Название этапа").fill("  а  ");
  await expect(
    page.getByRole("button", { name: "Добавить", exact: true }),
  ).toBeDisabled();
  await page.getByLabel("Название этапа").fill("Прототип бота на 40 FAQ");
  await page.getByRole("button", { name: "Добавить", exact: true }).click();
  await page.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(page.getByText("Подтверждён", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Лидерборд", exact: true }).click();
  const row = page.locator(".leader-row").filter({ hasText: "Nomad AI" });
  await expect(row.locator(".leader-points")).toHaveText("10");

  await page.goto(`/builder/${taskId}`);
  await page.getByRole("button", { name: "Как это работает" }).click();
  await expect(
    page.getByRole("heading", { name: "AI Inspector" }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Промпты и схемы" }).click();
  await expect(
    page
      .getByRole("tabpanel", { name: "Промпты и схемы" })
      .getByText("analyze_draft", { exact: false })
      .first(),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("Настоящий API: каталог, фильтры, пустое состояние", async ({ page }) => {
  await page.goto("/catalog");
  await expect(page.locator(".task-tile")).toHaveCount(6);
  await page.getByRole("button", { name: "Приоритетная", exact: true }).click();
  await expect(page.locator(".task-tile")).toHaveCount(1);
  await page.getByRole("button", { name: "Все уровни" }).click();
  await page.getByLabel("Поиск задач").fill("несуществующая задача");
  await expect(
    page.getByRole("heading", { name: "Задачи не найдены" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Сбросить фильтры" }).click();
  await expect(page.locator(".task-tile")).toHaveCount(6);
});
