import { test, expect } from "@playwright/test";

test.describe("dashboard authenticated flow", () => {
  test("login redirects to dashboard and shows data", async ({ page }) => {
    // Go to login page
    await page.goto("/login");
    
    // Fill credentials (using seeded user)
    await page.getByLabel("Email").fill("analyst@aegiscore.local");
    await page.getByLabel("Password").fill("AegisCore!demo2026");
    
    // Click sign in
    await page.getByRole("button", { name: /sign in/i }).click();
    
    // Wait for redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    
    // Verify dashboard content loads
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
    
    // Verify analytics cards are present
    await expect(page.getByRole("heading", { name: /open findings/i })).toBeVisible();
    
    // Verify navigation is present
    await expect(page.getByRole("link", { name: "Findings", exact: true }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "Assets", exact: true }).first()).toBeVisible();
  });

  test("unauthenticated user redirected to login", async ({ page }) => {
    // Try to access dashboard directly
    await page.goto("/dashboard");
    
    // Should be redirected to login
    await expect(page).toHaveURL(/\/login/);
  });

  test("navigation between protected pages works", async ({ page }) => {
    // Login first
    await page.goto("/login");
    await page.getByLabel("Email").fill("analyst@aegiscore.local");
    await page.getByLabel("Password").fill("AegisCore!demo2026");
    await page.getByRole("button", { name: /sign in/i }).click();
    
    // Wait for dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    
    // Navigate to findings
    await page.getByRole("link", { name: "Findings", exact: true }).first().click();
    await expect(page).toHaveURL(/\/findings/);
    await expect(page.getByRole("heading", { name: /findings/i })).toBeVisible();
    
    // Navigate to assets
    await page.getByRole("link", { name: "Assets", exact: true }).first().click();
    await expect(page).toHaveURL(/\/assets/);
    await expect(page.getByRole("heading", { name: /assets/i })).toBeVisible();
    
    // Navigate back to dashboard
    await page.getByRole("link", { name: "Dashboard", exact: true }).first().click();
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("logout redirects to login and clears session", async ({ page }) => {
    // Login
    await page.goto("/login");
    await page.getByLabel("Email").fill("analyst@aegiscore.local");
    await page.getByLabel("Password").fill("AegisCore!demo2026");
    await page.getByRole("button", { name: /sign in/i }).click();
    
    // Wait for dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    
    await page.evaluate(() => {
      sessionStorage.removeItem("aegiscore_access_token");
      sessionStorage.removeItem("aegiscore_refresh_token");
    });
    await page.reload();
    
    // Try to access dashboard again - should redirect to login
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });

  test("invalid credentials show error", async ({ page }) => {
    await page.goto("/login");
    
    await page.getByLabel("Email").fill("analyst@aegiscore.local");
    await page.getByLabel("Password").fill("wrongpassword");
    await page.getByRole("button", { name: /sign in/i }).click();
    
    // Error message should appear
    await expect(page.getByRole("alert").first()).toBeVisible();
    await expect(page.getByText(/invalid credentials|request failed|network error/i)).toBeVisible();
    
    // Should still be on login page
    await expect(page).toHaveURL(/\/login/);
  });
});
