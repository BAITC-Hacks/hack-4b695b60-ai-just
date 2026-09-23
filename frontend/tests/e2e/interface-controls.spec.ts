import { expect, test } from "@playwright/test";

for (const screen of [
  { name: "desktop dark", width: 1440, height: 1000, theme: "Тёмная" },
  { name: "mobile light", width: 390, height: 844, theme: "Светлая" },
]) {
  test.describe(screen.name, () => {
    test.use({ viewport: { width: screen.width, height: screen.height } });

    test("Списки: клавиатура, фильтры, меню в диалоге и сохранение темы", async ({
      page,
    }) => {
      await page.goto("/my-tasks");
      await page.getByRole("button", { name: /^Тема оформления:/ }).click();
      await page
        .getByRole("menuitemradio", { name: screen.theme, exact: true })
        .click();

      const business = page.getByRole("combobox", { name: "Выбор бизнеса" });
      await business.focus();
      await business.press("Enter");
      await page.keyboard.press("End");
      const lastBusiness = page.getByRole("option", {
        name: "Алтын Финанс",
        exact: true,
      });
      await expect(lastBusiness).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(business).toContainText("Алтын Финанс");
      await expect(business).toBeFocused();

      await page
        .getByRole("navigation", { name: "Основная навигация" })
        .getByRole("link", { name: "Каталог", exact: true })
        .click();
      const topic = page.getByRole("combobox", { name: "Тема", exact: true });
      await topic.click();
      await page.getByRole("option", { name: "Финансы", exact: true }).click();
      await expect(page.locator(".task-tile")).toHaveCount(1);
      await expect(page.locator(".task-tile")).toContainText(
        "Проверка комплектности",
      );
      await topic.click();
      await page.getByRole("option", { name: "Все темы", exact: true }).click();
      await expect(page.locator(".task-tile")).not.toHaveCount(1);
      await page.getByRole("combobox", { name: "Сортировка" }).click();
      await page
        .getByRole("option", { name: "Сначала новые", exact: true })
        .click();
      await expect(
        page.getByRole("combobox", { name: "Сортировка" }),
      ).toContainText("Сначала новые");

      await page.locator(".provider-button").click();
      const dialog = page.getByRole("dialog", { name: "Настройки AI и демо" });
      const provider = dialog.getByRole("combobox", { name: "AI-провайдер" });
      await provider.click();
      await expect(
        page.getByRole("option", { name: "Офлайн", exact: true }),
      ).toBeVisible();
      await page.getByRole("listbox").press("Escape");
      await expect(dialog).toBeVisible();
      await expect(provider).toBeFocused();
      await dialog
        .getByRole("button", { name: "Закрыть", exact: true })
        .click();

      const dimensions = await page.evaluate(() => ({
        width: document.documentElement.clientWidth,
        content: document.documentElement.scrollWidth,
      }));
      expect(dimensions.content).toBeLessThanOrEqual(dimensions.width);
      await page.reload();
      await expect(
        page.getByRole("button", { name: `Тема оформления: ${screen.theme}` }),
      ).toBeVisible();
    });
  });
}
