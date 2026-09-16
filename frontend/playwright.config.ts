import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  testMatch: ["portal.spec.ts", "room-entry.spec.ts"],
  workers: 1,
  retries: 0,
  reporter: "list",
  timeout: 30000,
  use: {
    baseURL: process.env.PORTAL_URL || "http://localhost:8000",
    viewport: { width: 1360, height: 1000 },
    trace: "retain-on-failure",
  },
});
