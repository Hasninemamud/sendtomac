import { defineConfig, devices } from "@playwright/test";

const remote = process.env.BASE_URL;
const baseURL = remote || "http://127.0.0.1:4173";

export default defineConfig({
  testDir: ".",
  testMatch: "cross-browser.spec.js",
  timeout: 45_000,
  retries: 1,
  reporter: "list",
  use: {
    baseURL,
    trace: "on-first-retry",
    navigationTimeout: 30_000,
  },
  webServer: remote
    ? undefined
    : {
        command: "python3 -m http.server 4173",
        cwd: "../web",
        url: baseURL,
        reuseExistingServer: true,
      },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
    { name: "mobile-chrome", use: { ...devices["Pixel 7"] } },
    { name: "mobile-safari", use: { ...devices["iPhone 14"] } },
  ],
});
