import { expect, test } from "@playwright/test";
const answers = {
  data: "Есть выгрузка обращений из CRM за 6 месяцев — около 12 000 записей в Excel, плюс FAQ на 40 вопросов. Данные обезличим и дадим доступ после NDA.",
  context:
    "Колл-центр получает 300–400 звонков в день, 60% — вопросы о статусе доставки и сроках.",
  success_criteria:
    "Бот самостоятельно закрывает не менее 40% обращений о статусе доставки, среднее время ответа — до 10 секунд.",
};
test("Полный сценарий: черновик → публикация → отклик → решение → баллы", async ({
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
  await expect(page.locator(".score-ring strong")).toHaveText("0");
  await page
    .getByRole("button", { name: "Подтвердить всё", exact: true })
    .click();
  await expect(page.locator(".score-ring strong")).toHaveText("27");
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
  await expect(page.locator(".score-ring strong")).toHaveText("72");
  const edit = async (key: string, value: string) => {
    const section = page.locator(`#field-section-${key}`);
    const input = section.locator(`#field-${key}`);
    if (!(await input.isVisible())) {
      await section.locator(".field-heading").click();
    }
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
  await expect(page.locator(".score-ring strong")).toHaveText("76");
  await edit(
    "constraints",
    "Пилот за 6 недель, Telegram, интеграция через REST API",
  );
  await edit("contact", "aigerim@example.com");
  await edit(
    "interaction_format",
    "Созвон раз в неделю, вопросы в Telegram-чате",
  );
  await expect(page.locator(".score-ring strong")).toHaveText("96");
  await edit("users", "Клиенты, ожидающие доставку, и операторы колл-центра");
  await expect(page.locator(".score-ring strong")).toHaveText("100");
  await page.getByRole("button", { name: "Опубликовать задачу" }).click();
  await expect(
    page.getByRole("button", { name: "Опубликовать", exact: true }),
  ).toBeDisabled();
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
  await page.getByRole("button", { name: "Выбрать", exact: true }).click();
  await expect(page.getByText("Выбрана", { exact: true })).toBeVisible();
  await page.getByLabel("Название этапа").fill("Прототип бота на 40 FAQ");
  await page.getByRole("button", { name: "Добавить", exact: true }).click();
  await page.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(page.getByText("Подтверждён", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Лидерборд", exact: true }).click();
  const row = page.locator(".leader-row").filter({ hasText: "Nomad AI" });
  await expect(row.locator(".leader-points")).toHaveText("10");
  await page.reload();
  await expect(row.locator(".leader-points")).toHaveText("10");
  await page.goto(`/builder/${taskId}`);
  await page.getByRole("button", { name: "Как это работает" }).click();
  await expect(
    page.getByRole("heading", { name: "AI Inspector" }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Промпты и схемы" }).click();
  await expect(
    page.getByText("Демонстрационная заглушка frontend", { exact: false }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
test("Каталог: фильтр, пустое состояние, мобильная ширина", async ({
  page,
}) => {
  await page.goto("/catalog");
  await expect(page.locator(".task-tile")).toHaveCount(6);
  await page.getByRole("button", { name: "Приоритетная", exact: true }).click();
  await expect(page.locator(".task-tile")).toHaveCount(3);
  await page.getByRole("button", { name: "Все уровни" }).click();
  await page.getByLabel("Поиск задач").fill("несуществующая задача");
  await expect(
    page.getByRole("heading", { name: "Задачи не найдены" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Сбросить фильтры" }).click();
  await expect(page.locator(".task-tile")).toHaveCount(6);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
});
