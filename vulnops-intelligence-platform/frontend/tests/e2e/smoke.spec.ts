import { test, expect } from "@playwright/test";

test.describe("public routes", () => {
  test("login page shows sign-in form", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  test("root redirects to login without a session", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login$/, { timeout: 15_000 });
  });
});
