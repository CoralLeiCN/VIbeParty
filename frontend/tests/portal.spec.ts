import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const ids = ["word-by-word", "prompt-royale", "reverse-prompt"];
const titles = ["Word by Word", "Prompt Royale", "Reverse Prompt"];
const anonymous = { status: "anonymous", reason: "no_session", party: null };
const discovery = (role = "host", status = "active") => ({
  status: "authenticated",
  session: {
    game_id: ids[0],
    role,
    can_close: role === "host",
    continuation_url: `/games/${ids[0]}/${role === "host" ? "host" : "join"}`,
  },
  party: { game_id: ids[0], status },
});
async function available(page: Page) {
  await page.route("**/api/games", (route) =>
    route.fulfill({
      json: { games: ids.map((id) => ({ id, available: true })) },
    }),
  );
}

// These are portal contract rehearsals. Game rules and live acceptance remain game-owned.
test("responsive home, accurate roles, keyboard join, wrong code and refresh", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Word by Word", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/development/evidence/portal/desktop.png",
    fullPage: true,
  });
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Join party", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/join$/);
  const codeField = page.getByLabel("Room code", { exact: true });
  await expect(codeField).toHaveAttribute("type", "text");
  await expect(codeField).toHaveAttribute("inputmode", "numeric");
  await expect(codeField).toHaveAttribute("pattern", "[0-9]{4}");
  for (const value of ["42", "12345", "12 34", "ABCD", "１２３４", ""]) {
    await codeField.fill(value);
    await codeField.press("Enter");
    await expect(page.getByRole("alert")).toHaveText(
      "Enter a 4-digit room code.",
    );
    await expect(codeField).toHaveValue(value);
  }
  await page.getByLabel("Room code", { exact: true }).fill("9999");
  await page.getByLabel("Room code", { exact: true }).press("Enter");
  await expect(page.getByRole("alert")).toContainText(
    "Check the code with your host",
  );
  await expect(page.getByLabel("Room code", { exact: true })).toHaveValue(
    "9999",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "../docs/development/evidence/portal/phone-join.png",
    fullPage: true,
  });
  await page.goto("/join?code=9999");
  await expect(page.getByRole("alert")).toBeVisible();
  await page.reload();
  await expect(page.getByRole("alert")).toBeVisible();
  await page.goto("/");
  await expect(
    page.getByText("Exactly 3 players, including the host"),
  ).toBeVisible();
  await expect(
    page.getByText("Separate laptop host · players join on phones"),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/development/evidence/portal/phone-home.png",
    fullPage: true,
  });
  for (const width of [320, 390, 768, 1360]) {
    await page.setViewportSize({ width, height: 844 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
});

test("all host routes and generic code routing follow the game ID", async ({
  page,
}) => {
  await available(page);
  await page.route("**/api/session", (route) =>
    route.fulfill({ json: anonymous }),
  );
  for (let i = 0; i < ids.length; i++) {
    await page.goto("/");
    await page
      .getByRole("button", { name: `Host ${titles[i]}`, exact: true })
      .click();
    await expect(page).toHaveURL(new RegExp(`/games/${ids[i]}/host$`));
    await page.reload();
    await expect(
      page.getByRole("link", { name: /Back to games/ }),
    ).toBeVisible();
    await page.route("**/api/party/resolve", (route) => {
      expect(route.request().postDataJSON()).toEqual({ code: "0042" });
      return route.fulfill({
        json: { game_id: ids[i], join_url: `/games/${ids[i]}/join?code=0042` },
      });
    });
    await page.goto("/join");
    await page.getByLabel("Room code", { exact: true }).fill(" 0042 ");
    await page.getByRole("button", { name: "Find my party" }).click();
    await expect(page).toHaveURL(
      new RegExp(`/games/${ids[i]}/join\\?code=0042$`),
    );
    await expect(page.getByLabel("Room code", { exact: true })).toHaveValue(
      "0042",
    );
    await page.goto("/join?code=0042");
    await expect(page).toHaveURL(
      new RegExp(`/games/${ids[i]}/join\\?code=0042$`),
    );
    await page.unroute("**/api/party/resolve");
  }
  await page.goto("/host");
  await expect(page).toHaveURL(/\/games\/word-by-word\/host$/);
});

test("authorized continuation survives refresh; player cannot close or switch", async ({
  page,
}) => {
  await available(page);
  await page.route("**/api/session", (route) =>
    route.fulfill({ json: discovery("player") }),
  );
  await page.goto("/");
  await page.getByRole("link", { name: /Continue party/ }).click();
  await expect(page).toHaveURL(/\/games\/word-by-word\/join$/);
  await page.getByRole("link", { name: /Back to games/ }).click();
  await page.reload();
  await expect(
    page.getByRole("link", { name: /Continue party/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "End game", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Host Prompt Royale", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText("Ask its host");
  await expect(
    page.getByRole("button", { name: "Close & switch" }),
  ).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Host Prompt Royale", exact: true }),
  ).toBeFocused();
});

test("host confirmation, unresolved cleanup, refresh and switch after closure", async ({
  page,
}) => {
  await available(page);
  let state: object = discovery();
  let closeRequests = 0;
  await page.route("**/api/session", (route) => route.fulfill({ json: state }));
  await page.route("**/api/party/close", (route) => {
    closeRequests++;
    expect(route.request().postDataJSON().game_id).toBe("word-by-word");
    state = discovery("host", "closing");
    return route.fulfill({
      json: { status: "closing", message: "Finishing the previous session." },
    });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Host Prompt Royale", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Everyone will need to rejoin");
  await page.keyboard.press("Escape");
  expect(closeRequests).toBe(0);
  await page
    .getByRole("button", { name: "Host Prompt Royale", exact: true })
    .click();
  await page.getByRole("button", { name: "Close & switch" }).click();
  await expect(dialog).toContainText("Finishing this party");
  expect(closeRequests).toBe(1);
  await page.screenshot({
    path: "../docs/development/evidence/portal/cleanup.png",
    fullPage: true,
  });
  await page.reload();
  await expect(
    page.getByText("Finishing the previous session", { exact: true }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/$/);
  state = anonymous;
  await expect(page).toHaveURL(/\/games\/prompt-royale\/host$/, {
    timeout: 8000,
  });
  expect(closeRequests).toBe(1);
});

test("network interruption keeps recovery distinct from expired sessions", async ({
  page,
}) => {
  await available(page);
  let offline = false;
  let state: object = discovery();
  await page.route("**/api/session", (route) =>
    offline ? route.abort() : route.fulfill({ json: state }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("link", { name: /Continue party/ }),
  ).toBeVisible();
  offline = true;
  await expect(
    page.getByText("Reconnecting to the laptop…", { exact: true }),
  ).toBeVisible({ timeout: 8000 });
  await expect(
    page.getByText("This party has ended", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Host Prompt Royale", exact: true }),
  ).toBeDisabled();
  offline = false;
  await page.getByRole("button", { name: "Retry connection" }).click();
  await expect(
    page.getByRole("link", { name: /Continue party/ }),
  ).toBeVisible();
  state = { status: "anonymous", reason: "expired", party: null };
  await expect(
    page.getByText("This party has ended", { exact: true }),
  ).toBeVisible({ timeout: 8000 });
  await expect(page.getByRole("link", { name: /Continue party/ })).toHaveCount(
    0,
  );
});

test("a party changed in another tab dismisses the stale close confirmation", async ({
  page,
}) => {
  await available(page);
  let state = discovery();
  let closes = 0;
  await page.route("**/api/session", (route) => route.fulfill({ json: state }));
  await page.route("**/api/party/close", (route) => {
    closes++;
    return route.fulfill({ json: { status: "closed" } });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Host Prompt Royale", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  state = {
    ...discovery(),
    session: {
      ...discovery().session,
      game_id: "reverse-prompt",
      continuation_url: "/games/reverse-prompt/host",
    },
    party: { game_id: "reverse-prompt", status: "active" },
  };
  await expect(page.getByRole("dialog")).toHaveCount(0, { timeout: 8000 });
  expect(closes).toBe(0);
});
