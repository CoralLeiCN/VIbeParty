import { expect, test } from "@playwright/test";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";

const origin = process.env.PORTAL_URL || "http://localhost:8000";
const api = "/api/games/word-by-word";
const passcode = process.env.HOST_PASSCODE || "WMHACK";
const recoveryFile = resolve(
  process.env.RECOVERY_MEDIA_ROOT || "../.local/vibeparty",
  "word-by-word/host-recovery.txt",
);

test.use({ extraHTTPHeaders: { Origin: origin } });

test.afterEach(async ({ request }) => {
  const options = await (await request.get(api + "/host/recovery")).json();
  if (options.available) {
    const credential =
      options.method === "local_code"
        ? (await readFile(recoveryFile, "utf8")).trim()
        : passcode;
    await request.post(api + "/host/recovery", {
      data: { party_id: options.party_id, credential },
    });
    await request.post("/api/party/close", {
      data: { game_id: "word-by-word" },
    });
  }
});

test("lost cookies: prove ownership, confirm close, then host Prompt Royale", async ({
  page,
  context,
}) => {
  const created = await page.request.post(api + "/host", {
    data: { passcode },
  });
  expect(created.ok()).toBeTruthy();
  const lobby = await created.json();
  const local = (await (await page.request.get("/api/config")).json())
    .local_mode;
  const credential = local
    ? (await readFile(recoveryFile, "utf8")).trim()
    : passcode;
  await context.clearCookies();
  await page.goto("/#games");
  await page
    .getByRole("button", { name: "Host Prompt Royale", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Recover host access", exact: true })
    .click();
  await page
    .getByLabel(local ? "Host recovery code" : "Host passcode", { exact: true })
    .fill(lobby.code);
  await page
    .getByRole("button", { name: "Restore host controls", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("incorrect");
  await expect(
    page.getByRole("button", { name: "Close & switch", exact: true }),
  ).toHaveCount(0);
  await page
    .getByLabel(local ? "Host recovery code" : "Host passcode", { exact: true })
    .fill(credential);
  await page
    .getByRole("button", { name: "Restore host controls", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "Everyone will need to rejoin for Prompt Royale",
  );
  expect((await (await page.request.get(api + "/state")).json()).round_id).toBe(
    lobby.round_id,
  );
  await page
    .getByRole("button", { name: "Close & switch", exact: true })
    .click();
  await expect(page).toHaveURL(/\/games\/prompt-royale\/host$/);
  await page.getByLabel("Your name", { exact: true }).fill("Recovered host");
  if (!local) await page.getByLabel("Host access code").fill(passcode);
  await page.getByRole("button", { name: "Create party", exact: true }).click();
  await expect(page.getByLabel("Invite your friends")).toBeVisible();
  expect(
    (
      await page.request.post("/api/party/close", {
        data: { game_id: "prompt-royale" },
      })
    ).ok(),
  ).toBeTruthy();
});

test("direct host entry offers recovery for a stale host cookie", async ({
  page,
  context,
}) => {
  expect(
    (await page.request.post(api + "/host", { data: { passcode } })).ok(),
  ).toBeTruthy();
  const local = (await (await page.request.get("/api/config")).json())
    .local_mode;
  const credential = local
    ? (await readFile(recoveryFile, "utf8")).trim()
    : passcode;
  await context.clearCookies();
  await context.addCookies([
    { name: "vp_word_by_word", value: "stale", url: origin },
  ]);
  await page.goto("/#games");
  await expect(
    page.getByText("This party has ended", { exact: true }),
  ).toHaveCount(0);
  await page.goto("/games/word-by-word/host");
  await page
    .getByRole("button", { name: "Recover host access", exact: true })
    .click();
  await page
    .getByRole("region", { name: "Host recovery" })
    .getByLabel(local ? "Host recovery code" : "Host passcode", { exact: true })
    .fill(credential);
  await page
    .getByRole("button", { name: "Restore host controls", exact: true })
    .click();
  await expect(page.getByLabel("Phone join link")).toBeVisible();
  await page.getByRole("link", { name: /Back to games/ }).click();
  await expect(
    page.getByRole("button", { name: "End game", exact: true }),
  ).toBeVisible();
  await page.request.post("/api/party/close", {
    data: { game_id: "word-by-word" },
  });
});

test("same browser tabs and restart retain host; alternate hostname does not", async ({
  playwright,
}) => {
  const profile = await mkdtemp(resolve(tmpdir(), "vibeparty-recovery-"));
  let context = await playwright.chromium.launchPersistentContext(profile, {
    baseURL: origin,
  });
  try {
    const created = await context.request.post(origin + api + "/host", {
      data: { passcode },
      headers: { Origin: origin },
    });
    expect(created.ok()).toBeTruthy();
    const cookies = await context.cookies();
    expect(
      cookies.find((cookie) => cookie.name === "vp_word_by_word")!.expires,
    ).toBeGreaterThan(Date.now() / 1000);
    for (const page of context.pages()) await page.close();
    let page = await context.newPage();
    await page.goto(origin + "/#games");
    await expect(
      page.getByRole("button", { name: "End game", exact: true }),
    ).toBeVisible();
    await context.close();
    context = await playwright.chromium.launchPersistentContext(profile, {
      baseURL: origin,
    });
    page = await context.newPage();
    await page.goto(origin + "/#games");
    await expect(
      page.getByRole("button", { name: "End game", exact: true }),
    ).toBeVisible();
    const alternate = new URL(origin);
    alternate.hostname =
      alternate.hostname === "localhost" ? "127.0.0.1" : "localhost";
    await page.goto(alternate.origin + "/#games");
    await expect(
      page.getByRole("button", { name: "End game", exact: true }),
    ).toHaveCount(0);
    await page
      .getByRole("button", { name: "Host Prompt Royale", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Recover host access", exact: true }),
    ).toBeVisible();
    await context.request.post(origin + "/api/party/close", {
      data: { game_id: "word-by-word" },
      headers: { Origin: origin },
    });
  } finally {
    await context.close();
    await rm(profile, { recursive: true, force: true });
  }
});
