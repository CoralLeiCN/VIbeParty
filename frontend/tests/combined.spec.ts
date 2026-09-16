import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const origin = process.env.PORTAL_URL || "http://localhost:8000";
const hostCode = process.env.DEMO_HOST_CODE || "WMHACK";
const word = "/api/games/word-by-word";
const reverse = "/api/games/reverse-prompt";
const royale = "/api/games/prompt-royale";
function checkCode(code: unknown) {
  expect(typeof code).toBe("string");
  expect(code).toMatch(/^[0-9]{4}$/);
  if (process.env.PORTAL_EXPECT_CODE)
    expect(code).toBe(process.env.PORTAL_EXPECT_CODE);
}
async function read(page: Page, route: string) {
  const response = await page.request.get(origin + route);
  expect(response.ok(), `GET ${route}: ${response.status()}`).toBeTruthy();
  return response.json();
}
async function post(page: Page, route: string, data: object = {}) {
  const response = await page.request.post(origin + route, { data });
  expect(
    response.ok(),
    `POST ${route}: ${response.status()} ${await response.text()}`,
  ).toBeTruthy();
  return response.json();
}
async function returnAndContinue(page: Page, path: string) {
  await page.getByRole("link", { name: /Back to games/ }).click();
  await page.getByRole("link", { name: /Continue party/ }).click();
  await expect(page).toHaveURL(new RegExp(path + "$"));
  await page.reload();
}

// Real local game APIs and browser forms. Fixture submissions use their supplied examples.
test("complete all three games with continuation, cleanup, and fresh joins", async ({
  browser,
}) => {
  const contexts = await Promise.all(
    [0, 1, 2, 3].map((index) =>
      browser.newContext({
        baseURL: origin,
        viewport: index
          ? { width: 390, height: 844 }
          : { width: 1360, height: 1000 },
        extraHTTPHeaders: { Origin: origin },
      }),
    ),
  );
  const [host, ...phones] = await Promise.all(
    contexts.map((context) => context.newPage()),
  );
  try {
    const localMode = (await read(host, "/api/config")).local_mode;
    expect((await read(host, "/api/session")).party).toBeNull();
    await host.goto("/");
    await host
      .getByRole("button", { name: "Host Word by Word", exact: true })
      .click();
    if (!localMode) await host.getByLabel("Host passcode").fill(hostCode);
    await host
      .getByRole("button", { name: "Open host screen", exact: true })
      .click();
    await expect(
      host.getByText("FIXTURE REHEARSAL", { exact: true }),
    ).toBeVisible();
    const lobby = await read(host, word + "/state");
    checkCode(lobby.code);
    expect(lobby.role).toBe("host");
    expect(lobby.players).toHaveLength(0);
    const joinLink = await host.getByLabel("Phone join link").inputValue();
    expect(new URL(joinLink).origin).toBe(origin);
    expect(new URL(joinLink).searchParams.get("code")).toBe(lobby.code);
    for (let i = 0; i < phones.length; i++) {
      const phone = phones[i];
      if (i === 0) {
        await phone.goto("/join");
        await phone.getByLabel("Room code", { exact: true }).fill(lobby.code);
        await phone.getByRole("button", { name: "Find my party" }).click();
      } else if (i === 1) await phone.goto(joinLink);
      else {
        await phone.goto("/games/word-by-word/join");
        await phone.getByLabel("Room code", { exact: true }).fill(lobby.code);
      }
      await phone
        .getByLabel("Your name", { exact: true })
        .fill(["Bailey", "Casey", "Drew"][i]);
      await phone
        .getByRole("button", { name: "Join the story", exact: true })
        .click();
      await expect
        .poll(async () => (await read(phone, word + "/state")).role)
        .toBe("player");
    }
    await phones[0].reload();
    await expect(
      phones[0].getByText("PLAYING AS Bailey", { exact: true }),
    ).toBeVisible();
    await host.getByRole("button", { name: /Start round/ }).click();
    await expect
      .poll(async () => (await read(host, word + "/state")).phase)
      .toBe("INPUT");
    for (const phone of phones) {
      const state = await read(phone, word + "/state");
      for (const assignment of state.assignments)
        await post(phone, word + "/contribution", {
          round_id: state.round_id,
          slot_index: assignment.index,
          text: assignment.fixture_text,
        });
    }
    await expect(host.getByLabel("Continuous story")).toBeVisible({
      timeout: 15000,
    });
    await expect(
      host.getByRole("button", {
        name: /Next addition|Play the first addition/,
      }),
    ).toHaveCount(0);
    await expect
      .poll(async () =>
        host
          .locator("video")
          .evaluate((video) => (video as HTMLVideoElement).currentTime),
      )
      .toBeGreaterThan(0.2);
    // One source remains attached across category updates and through completion.
    const stream = (await read(host, word + "/state")).stream_url;
    await host.reload();
    await expect(host.getByLabel("Continuous story")).toBeVisible();
    expect((await read(host, word + "/state")).stream_url).toBe(stream);
    await expect
      .poll(async () => (await read(host, word + "/state")).phase, {
        timeout: 40000,
      })
      .toBe("RESULTS");
    await expect(
      host.getByRole("heading", { name: "Made together", exact: true }),
    ).toBeVisible();
    const result = await read(host, word + "/state");
    expect(result.cards).toHaveLength(4);
    expect(result.live_attempts_left).toBe(lobby.live_attempts_left);
    const oldClip = result.recording_url;
    await host
      .getByRole("button", { name: "Replay saved story ↻", exact: true })
      .click();
    await expect
      .poll(async () =>
        host
          .locator("video")
          .evaluate((video) => (video as HTMLVideoElement).currentTime),
      )
      .toBeGreaterThan(0.2);
    await host.screenshot({
      path: "../docs/development/evidence/portal/word-connected.png",
      fullPage: true,
    });
    await returnAndContinue(host, "/games/word-by-word/host");
    await expect(
      host.getByRole("heading", { name: "Made together", exact: true }),
    ).toBeVisible();
    await returnAndContinue(phones[0], "/games/word-by-word/join");
    expect((await read(phones[0], word + "/state")).cards).toHaveLength(4);
    await host
      .getByRole("button", {
        name: "Another round · same players →",
        exact: true,
      })
      .click();
    await expect
      .poll(async () => (await read(host, word + "/state")).phase)
      .toBe("LOBBY");
    expect((await read(host, word + "/state")).code).toBe(lobby.code);
    await host
      .getByRole("button", { name: "Reset party", exact: true })
      .click();
    await host
      .getByRole("button", { name: "Reset party now", exact: true })
      .click();
    await expect
      .poll(async () => (await read(host, word + "/state")).players.length)
      .toBe(0);
    const resetWord = await read(host, word + "/state");
    expect(resetWord.code).not.toBe(lobby.code);
    expect(resetWord.code).toMatch(/^[0-9]{4}$/);
    expect(
      (await post(host, "/api/party/resolve", { code: resetWord.code }))
        .game_id,
    ).toBe("word-by-word");
    await host.goto("/");
    await host
      .getByRole("button", { name: "Host Reverse Prompt", exact: true })
      .click();
    await expect(host.getByRole("dialog")).toContainText(
      "Everyone will need to rejoin",
    );
    await host
      .getByRole("button", { name: "Close & switch", exact: true })
      .click();
    await expect(host).toHaveURL(/\/games\/reverse-prompt\/host$/);
    expect([401, 404]).toContain(
      (await phones[0].request.get(origin + oldClip)).status(),
    );
    expect(
      (
        await phones[0].request.post(origin + "/api/party/resolve", {
          data: { code: lobby.code },
        })
      ).status(),
    ).toBe(404);
    await host.getByLabel("Your name", { exact: true }).fill("Alex");
    if (!localMode)
      await host.getByLabel("Organizer code", { exact: true }).fill(hostCode);
    await host
      .getByRole("button", { name: "Create party as author A", exact: true })
      .click();
    await expect
      .poll(async () => (await read(host, reverse + "/state")).role)
      .toBe("A");
    const reverseLobby = await read(host, reverse + "/state");
    checkCode(reverseLobby.code);
    expect(reverseLobby.players).toHaveLength(1);
    for (let i = 0; i < 2; i++) {
      const phone = phones[i];
      if (i === 0) {
        await phone.goto("/join");
        await phone
          .getByLabel("Room code", { exact: true })
          .fill(reverseLobby.code);
        await phone.getByRole("button", { name: "Find my party" }).click();
      } else await phone.goto(reverseLobby.join_url);
      await phone
        .getByLabel("Your name", { exact: true })
        .fill(["Bailey", "Casey"][i]);
      await phone
        .getByRole("button", { name: "Join party", exact: true })
        .click();
      await expect
        .poll(async () => (await read(phone, reverse + "/state")).role)
        .toBe(["B", "C"][i]);
    }
    await host
      .getByRole("button", { name: "Start round", exact: true })
      .click();
    for (const page of [host, phones[0], phones[1]])
      await page
        .getByRole("button", { name: "Send this scene", exact: true })
        .click();
    for (const phone of phones.slice(0, 2))
      await phone
        .getByRole("button", { name: "Lock my final guess", exact: true })
        .click();
    await expect
      .poll(async () => (await read(host, reverse + "/state")).phase, {
        timeout: 10000,
      })
      .toBe("reveal");
    const reverseResult = await read(host, reverse + "/state");
    expect(
      reverseResult.results.map((row: { points: number }) => row.points),
    ).toEqual([88, 46]);
    await expect(
      host.getByRole("heading", { name: "The whole story", exact: true }),
    ).toBeVisible();
    await host.screenshot({
      path: "../docs/development/evidence/portal/reverse-connected.png",
      fullPage: true,
    });
    await returnAndContinue(host, "/games/reverse-prompt/host");
    expect((await read(host, reverse + "/state")).phase).toBe("reveal");
    await expect(phones[0].locator("video")).toHaveCount(3);
    for (const video of await phones[0].locator("video").all())
      await video.evaluate((element) => (element as HTMLVideoElement).play());
    await expect
      .poll(async () =>
        phones[0]
          .locator("video")
          .evaluateAll((elements) =>
            elements.every(
              (element) =>
                (element as HTMLVideoElement).currentTime > 0.1 &&
                !(element as HTMLVideoElement).error,
            ),
          ),
      )
      .toBeTruthy();
    await phones[0]
      .locator("video")
      .evaluateAll((elements) =>
        elements.forEach((element) => (element as HTMLVideoElement).pause()),
      );
    await phones[0].screenshot({
      path: "../docs/development/evidence/portal/reverse-phone-connected.png",
      fullPage: true,
    });
    const reverseClip = reverseResult.chain[0].media.url;
    await host
      .getByRole("button", {
        name: "Another round · return to lobby",
        exact: true,
      })
      .click();
    await host
      .getByRole("button", { name: "Confirm reset to lobby", exact: true })
      .click();
    await expect
      .poll(async () => (await read(host, reverse + "/state")).phase)
      .toBe("lobby");
    expect((await read(host, reverse + "/state")).code).toBe(reverseLobby.code);
    await host.goto("/");
    await host
      .getByRole("button", { name: "Host Prompt Royale", exact: true })
      .click();
    await host
      .getByRole("button", { name: "Close & switch", exact: true })
      .click();
    await expect(host).toHaveURL(/\/games\/prompt-royale\/host$/);
    expect(
      (
        await phones[0].request.post(origin + "/api/party/resolve", {
          data: { code: reverseLobby.code },
        })
      ).status(),
    ).toBe(404);
    expect([401, 404]).toContain(
      (await phones[0].request.get(origin + reverseClip)).status(),
    );
    await host.getByLabel("Your name", { exact: true }).fill("Alex");
    if (!localMode) await host.getByLabel("Host access code").fill(hostCode);
    await host
      .getByLabel("Number of players")
      .selectOption(String(phones.length + 1));
    await host
      .getByRole("button", { name: "Create party", exact: true })
      .click();
    const royaleJoin = await host
      .getByLabel("Invite your friends")
      .inputValue();
    expect(new URL(royaleJoin).origin).toBe(origin);
    checkCode(new URL(royaleJoin).searchParams.get("code"));
    expect((await read(host, royale + "/room")).players).toHaveLength(1);
    for (let i = 0; i < phones.length; i++) {
      if (i === 0) {
        await phones[i].goto("/join");
        await phones[i]
          .getByLabel("Room code", { exact: true })
          .fill(new URL(royaleJoin).searchParams.get("code")!);
        await phones[i].getByRole("button", { name: "Find my party" }).click();
      } else if (i === 1) await phones[i].goto(royaleJoin);
      else {
        await phones[i].goto("/games/prompt-royale/join");
        await phones[i]
          .getByLabel("Room code", { exact: true })
          .fill(new URL(royaleJoin).searchParams.get("code")!);
      }
      await phones[i]
        .getByLabel("Your name", { exact: true })
        .fill(["Bailey", "Casey", "Drew"][i]);
      await phones[i]
        .getByRole("button", { name: "Join party", exact: true })
        .click();
    }
    await expect(host.getByText("4/4", { exact: true })).toBeVisible();
    await host.getByLabel("Choose a topic").selectOption({ index: 1 });
    await host.getByRole("button", { name: "Start round ↗" }).click();
    for (const [i, page] of [host, ...phones].entries()) {
      await page
        .getByLabel("Your private scene")
        .fill(`A dancing penguin in scene ${i + 1}`);
      await page.getByRole("button", { name: "Submit scene" }).click();
    }
    for (const page of [host, ...phones]) {
      await expect(
        page.getByRole("region", { name: "Anonymous arena" }),
      ).toBeVisible();
      await expect(page.locator("video")).toHaveCount(4);
      await page
        .getByRole("button", { name: "Play arena", exact: true })
        .click();
      await expect
        .poll(() =>
          page
            .locator("video")
            .evaluateAll((videos) =>
              videos.every(
                (video) =>
                  (video as HTMLVideoElement).currentTime > 0.1 &&
                  !(video as HTMLVideoElement).error,
              ),
            ),
        )
        .toBeTruthy();
    }
    await host.screenshot({
      path: "../docs/development/evidence/portal/royale-connected.png",
      fullPage: true,
    });
    await phones[0].screenshot({
      path: "../docs/development/evidence/portal/royale-phone-connected.png",
      fullPage: true,
    });
    const royaleArena = await read(host, royale + "/room");
    await returnAndContinue(host, "/games/prompt-royale/host");
    await returnAndContinue(phones[0], "/games/prompt-royale/join");
    expect((await read(phones[0], royale + "/room")).arena).toEqual(
      royaleArena.arena,
    );
    await host.getByRole("checkbox").check();
    await host
      .getByRole("button", { name: "Open voting", exact: true })
      .click();
    for (const page of [host, ...phones]) {
      await page
        .getByRole("button", { name: /^Choose Clip/ })
        .first()
        .click();
      await page.getByRole("button", { name: "Vote", exact: true }).click();
    }
    await expect(
      host.getByText(/We have a winner!|A shared crown!/),
    ).toBeVisible();
    await host.screenshot({
      path: "../docs/development/evidence/portal/royale-results-connected.png",
      fullPage: true,
    });
    await host.getByRole("button", { name: "Play again", exact: true }).click();
    await expect(host.getByLabel("Choose a topic")).toHaveValue("");
    expect(
      new URL(
        await host.getByLabel("Invite your friends").inputValue(),
      ).searchParams.get("code"),
    ).toBe(new URL(royaleJoin).searchParams.get("code"));
    await host.goto("/");
    await host
      .getByRole("button", { name: "Close party", exact: true })
      .click();
    await host
      .getByRole("dialog")
      .getByRole("button", { name: "Close party", exact: true })
      .click();
    await expect
      .poll(async () => (await read(host, "/api/session")).party)
      .toBeNull();
    expect((await read(phones[0], "/api/session")).status).toBe("anonymous");
    expect([401, 404]).toContain(
      (await phones[0].request.get(origin + royaleArena.arena[0].url)).status(),
    );
  } finally {
    const session = await read(host, "/api/session");
    if (session.status === "authenticated" && session.session.can_close)
      await host.request.post(origin + "/api/party/close", {
        data: { game_id: session.session.game_id },
      });
    await Promise.all(contexts.map((context) => context.close()));
  }
});

test("Reverse direct join accepts a pasted code and preserves it on refresh", async ({
  browser,
}) => {
  const hostContext = await browser.newContext({
    baseURL: origin,
    extraHTTPHeaders: { Origin: origin },
  });
  const phoneContext = await browser.newContext({
    baseURL: origin,
    viewport: { width: 390, height: 844 },
    extraHTTPHeaders: { Origin: origin },
  });
  const host = await hostContext.newPage();
  const phone = await phoneContext.newPage();
  try {
    await post(host, reverse + "/room", {
      organizer_code: hostCode,
      name: "Alex",
      mode: "rehearsal",
    });
    const lobby = await read(host, reverse + "/state");
    checkCode(lobby.code);
    await phone.goto("/games/reverse-prompt/join");
    await phone.getByLabel("Your name", { exact: true }).fill("Bailey");
    const field = phone.getByLabel("Room code", { exact: true });
    await field.fill("１２３４");
    await phone
      .getByRole("button", { name: "Join party", exact: true })
      .click();
    await expect(phone.getByRole("alert")).toHaveText(
      "Enter a 4-digit room code.",
    );
    await field.fill(` ${lobby.code} `);
    await phone
      .getByRole("button", { name: "Join party", exact: true })
      .click();
    await expect
      .poll(async () => (await read(phone, reverse + "/state")).role)
      .toBe("B");
    await phone.reload();
    expect((await read(phone, reverse + "/state")).code).toBe(lobby.code);
  } finally {
    await host.request.post(origin + "/api/party/close", {
      data: { game_id: "reverse-prompt" },
    });
    await Promise.all([hostContext.close(), phoneContext.close()]);
  }
});
