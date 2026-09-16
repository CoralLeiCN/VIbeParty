import { expect, test } from "@playwright/test";

const origin = process.env.PORTAL_URL || "http://localhost:8000";
const hostCode = process.env.DEMO_HOST_CODE || "WMHACK";
const games = [
  {
    id: "word-by-word",
    password: "Host passcode",
    create: "Open host screen",
    join: "Join the story",
    link: "Phone join link",
    copy: "Copy join link",
    copied: "Copied!",
  },
  {
    id: "prompt-royale",
    password: "Host access code",
    create: "Create party",
    join: "Join party",
    link: "Invite your friends",
    copy: "Copy link",
    copied: "Link copied ✓",
  },
  {
    id: "reverse-prompt",
    password: "Organizer code",
    create: "Create party as author A",
    join: "Join party",
    link: null,
    copy: "Copy join link",
    copied: "Copied",
  },
];

for (const game of games) {
  test(`${game.id}: create a room and join its shared link`, async ({
    browser,
  }) => {
    const hostContext = await browser.newContext({
      baseURL: origin,
      extraHTTPHeaders: { Origin: origin },
    });
    const guestContext = await browser.newContext({
      baseURL: origin,
      extraHTTPHeaders: { Origin: origin },
      viewport: { width: 390, height: 844 },
    });
    const host = await hostContext.newPage();
    const guest = await guestContext.newPage();
    const errors: string[] = [];
    for (const page of [host, guest])
      page.on("pageerror", (error) => errors.push(error.message));
    try {
      const config = await (await host.request.get("/api/config")).json();
      await host.goto(`/games/${game.id}/host`);
      if (config.local_mode) {
        await expect(
          host.getByText(/Local mode · Create a room/),
        ).toBeVisible();
        await expect(host.locator('input[type="password"]')).toHaveCount(0);
      } else {
        await host.getByLabel(game.password, { exact: true }).fill(hostCode);
      }
      if (game.id !== "word-by-word")
        await host.getByLabel("Your name", { exact: true }).fill("Host");
      await host
        .getByRole("button", { name: game.create, exact: true })
        .click();
      const copy = host.getByRole("button", { name: game.copy, exact: true });
      await expect(copy).toBeVisible();
      const joinLink = game.link
        ? await host.getByLabel(game.link, { exact: true }).inputValue()
        : await host
            .locator(`a[href*="/games/${game.id}/join?code="]`)
            .getAttribute("href");
      expect(joinLink).toBeTruthy();
      expect(new URL(joinLink!).origin).toBe(origin);
      await copy.click();
      await expect(
        host.getByRole("button", { name: game.copied, exact: true }),
      ).toBeVisible();

      await guest.goto(joinLink!);
      await expect(guest.getByLabel("Room code", { exact: true })).toHaveValue(
        new URL(joinLink!).searchParams.get("code")!,
      );
      await expect(guest.locator('input[type="password"]')).toHaveCount(0);
      await guest.getByLabel("Your name", { exact: true }).fill("Link guest");
      await guest.getByRole("button", { name: game.join, exact: true }).click();
      await expect
        .poll(async () => {
          const discovery = await (
            await guest.request.get("/api/session")
          ).json();
          return discovery.session?.role;
        })
        .toBe("player");
      await expect(host.getByText(/Link guest/).first()).toBeVisible();
      await guest.reload();
      await expect(
        guest.getByRole("button", { name: game.join, exact: true }),
      ).toHaveCount(0);
      await expect(guest.getByText(/Link guest/).first()).toBeVisible();
      expect(
        await guest.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBeTruthy();
      expect(errors).toEqual([]);
    } finally {
      await host.request.post("/api/party/close", { data: {} });
      await hostContext.close();
      await guestContext.close();
    }
  });
}

test("host admission waits for room settings and can retry a failure", async ({
  page,
}) => {
  let attempts = 0;
  await page.route("**/api/config", (route) => {
    attempts += 1;
    return route.fulfill(
      attempts === 1
        ? { status: 503, json: { code: "unavailable", message: "Unavailable" } }
        : { json: { local_mode: true } },
    );
  });
  await page.goto("/games/word-by-word/host");
  await expect(page.getByText("Could not load room settings.")).toBeVisible();
  const create = page.getByRole("button", {
    name: "Open host screen",
    exact: true,
  });
  await expect(create).toBeDisabled();
  await page.getByRole("button", { name: "Try again", exact: true }).click();
  await expect(page.getByText(/Local mode · Create a room/)).toBeVisible();
  await expect(create).toBeEnabled();
});
