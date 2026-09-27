import { test, expect } from "@playwright/test";

test.describe("SendToMac site", () => {
  test("home loads and shows brand + CTA", async ({ page }) => {
    const res = await page.goto("/", { waitUntil: "domcontentloaded" });
    expect(res?.ok()).toBeTruthy();
    await expect(page.locator(".brand span")).toHaveText("SendToMac");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "Hand the Mac a file"
    );
    await expect(
      page.getByRole("link", { name: /Download for Mac/i }).first()
    ).toBeVisible();
  });

  test("theme toggle flips night mode", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.evaluate(() => {
      localStorage.setItem("sendtomac-theme", "day");
      document.documentElement.removeAttribute("data-theme");
    });
    await page.reload({ waitUntil: "domcontentloaded" });

    const toggle = page.locator("[data-theme-toggle]");
    await expect(toggle).toBeVisible();
    await toggle.click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "night");
    await toggle.click();
    await expect(page.locator("html")).not.toHaveAttribute("data-theme", "night");
  });

  test("privacy page loads", async ({ page }) => {
    const res = await page.goto("/privacy/", { waitUntil: "domcontentloaded" });
    expect(res?.ok()).toBeTruthy();
    await expect(page.locator("body")).toContainText(/privacy/i);
  });
});
