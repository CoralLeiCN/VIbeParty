import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import type { Snapshot } from "../src/games/reverse-prompt/types";

const origin = process.env.PORTAL_URL || "http://localhost:8000";
const api = "/api/games/reverse-prompt";
const names = ["Alex", "Bailey", "Casey"];

async function state(page: Page): Promise<Snapshot> {
  const response = await page.request.get(origin + api + "/state");
  expect(response.ok()).toBeTruthy();
  return response.json();
}

async function post(page: Page, route: string, data: object) {
  const response = await page.request.post(origin + route, { data });
  expect(
    response.ok(),
    `POST ${route}: ${response.status()} ${await response.text()}`,
  ).toBeTruthy();
  return response.json();
}

test("Reverse reveals scenes before scores and rotates all three authors while the creator keeps controls", async ({
  browser,
}, testInfo) => {
  const contexts = await Promise.all(
    names.map((_, index) =>
      browser.newContext({
        baseURL: origin,
        viewport: index
          ? { width: 390, height: 844 }
          : { width: 1360, height: 1000 },
        extraHTTPHeaders: { Origin: origin },
      }),
    ),
  );
  const pages = await Promise.all(contexts.map((context) => context.newPage()));
  const creator = pages[0];
  const completed: object[] = [];
  let hosted = false;
  try {
    await post(creator, api + "/room", {
      organizer_code: process.env.DEMO_HOST_CODE || "WMHACK",
      name: names[0],
      mode: "rehearsal",
    });
    hosted = true;
    const originalLobby = await state(creator);
    for (const index of [1, 2])
      await post(pages[index], api + "/join", {
        code: originalLobby.code,
        name: names[index],
      });
    await Promise.all(
      pages.map((page, index) =>
        page.goto(`/games/reverse-prompt/${index ? "join" : "host"}`),
      ),
    );

    for (let round = 0; round < 3; round++) {
      const order = [round, (round + 1) % 3, (round + 2) % 3];
      const roundNames = order.map((index) => names[index]);
      const roundPages = order.map((index) => pages[index]);
      const lobby = await state(creator);
      expect(lobby.phase).toBe("lobby");
      expect(lobby.players.map((player) => player.name)).toEqual(roundNames);
      expect(lobby.players.filter((player) => player.is_host)).toEqual([
        { name: "Alex", role: ["A", "C", "B"][round], is_host: true },
      ]);
      expect(lobby.code).toBe(originalLobby.code);
      for (const [index, page] of pages.entries()) {
        const own = await state(page);
        expect(own.role).toBe("ABC"[order.indexOf(index)]);
        expect(own.is_host).toBe(index === 0);
        await expect(
          page.getByText(`Next author: ${roundNames[0]}.`, { exact: false }),
        ).toBeVisible();
        await expect(
          page.getByRole("group", { name: "Host controls" }),
        ).toHaveCount(index === 0 ? 1 : 0);
      }
      await creator
        .getByRole("button", { name: "Start round", exact: true })
        .click();

      const submittedPrompts: string[] = [];
      let activeRoundId = "";
      for (const [step, page] of roundPages.entries()) {
        const field = page.getByLabel(
          step === 0
            ? "Write the scene that starts it all"
            : "Describe only what you see",
          { exact: true },
        );
        await expect(field).toBeVisible();
        const input = await state(page);
        if (step === 0) activeRoundId = input.round_id;
        expect(input.phase).toBe(step === 0 ? "author_input" : "relay_input");
        expect(input.scripted_text).toBeTruthy();
        await expect(field).toHaveValue(input.scripted_text!);
        if (step > 0) {
          await expect(
            page.getByLabel("Your private clue", { exact: true }),
          ).toBeVisible();
          await expect(
            page.getByRole("timer", { name: "Relay time remaining" }),
          ).toBeVisible();
        }
        submittedPrompts.push(input.scripted_text!);
        await page
          .getByRole("button", { name: "Send this scene", exact: true })
          .click();
      }

      const submittedGuesses: string[] = [];
      for (const page of roundPages.slice(1)) {
        const field = page.getByLabel(
          "Your final guess of the original scene",
          { exact: true },
        );
        await expect(field).toBeVisible();
        const guessing = await state(page);
        expect(guessing.scripted_text).toBeTruthy();
        await expect(field).toHaveValue(guessing.scripted_text!);
        submittedGuesses.push(guessing.scripted_text!);
        await page
          .getByRole("button", { name: "Lock my final guess", exact: true })
          .click();
      }
      await expect
        .poll(async () => (await state(creator)).phase)
        .toBe("reveal");

      for (let step = 0; step < 3; step++) {
        for (const [index, page] of pages.entries()) {
          const chain = page.getByRole("list", { name: "Revealed scenes" });
          await expect(chain.locator("video")).toHaveCount(step + 1);
          await expect(chain.locator("blockquote")).toHaveText(
            submittedPrompts.slice(0, step + 1),
          );
          for (const prompt of submittedPrompts.slice(step + 1))
            await expect(page.getByText(prompt, { exact: true })).toHaveCount(
              0,
            );
          await expect(
            page.getByRole("region", { name: "Guesses and scores" }),
          ).toHaveCount(0);
          await expect(page.getByText(/Similarity:/)).toHaveCount(0);
          await expect(
            page.getByRole("button", {
              name: "Start another round",
              exact: true,
            }),
          ).toHaveCount(0);
          await expect(
            page.getByRole("button", {
              name: /Reveal next scene|Reveal guesses and scores/,
            }),
          ).toHaveCount(index === 0 ? 1 : 0);
        }

        if (step === 1) {
          // Reload both the creator and a guest after the second pair. Their
          // identity, host authority, and shared disclosure step must survive.
          await Promise.all([creator.reload(), pages[1].reload()]);
          for (const page of [creator, pages[1]]) {
            await expect(
              page
                .getByRole("list", { name: "Revealed scenes" })
                .locator("video"),
            ).toHaveCount(2);
            const restored = await state(page);
            expect(restored.round_id).toBe(activeRoundId);
            expect(restored.reveal_index).toBe(1);
            expect(restored.results_revealed).toBe(false);
            expect(restored.is_host).toBe(page === creator);
          }
        }
        if (step === 2 && round === 0) {
          const clip = pages[1]
            .getByRole("list", { name: "Revealed scenes" })
            .locator("video")
            .last();
          await clip.evaluate((element: HTMLVideoElement) => element.play());
          await expect
            .poll(() =>
              clip.evaluate((element: HTMLVideoElement) => element.currentTime),
            )
            .toBeGreaterThan(0.1);
          await clip.evaluate((element: HTMLVideoElement) => element.pause());
          await pages[1].screenshot({
            path: testInfo.outputPath("reverse-phone-before-scores.png"),
            fullPage: true,
          });
        }
        await creator
          .getByRole("button", {
            name:
              step === 2 ? "Reveal guesses and scores" : "Reveal next scene",
            exact: true,
          })
          .click();
      }

      for (const page of pages) {
        const results = page.getByRole("region", {
          name: "Guesses and scores",
        });
        await expect(results).toBeVisible();
        await expect(results.getByRole("article")).toHaveCount(2);
        for (const guess of submittedGuesses)
          await expect(results.getByText(guess, { exact: true })).toBeVisible();
        await expect(
          results.getByText(`Similarity: 88 / 100`, { exact: true }),
        ).toBeVisible();
        await expect(
          results.getByText(`Similarity: 46 / 100`, { exact: true }),
        ).toBeVisible();
      }
      const revealed = await state(creator);
      expect(revealed.results_revealed).toBe(true);
      expect(revealed.results?.map((result) => result.player)).toEqual(
        roundNames.slice(1),
      );
      if (round > 0)
        expect(
          revealed.results?.find((result) => result.player === "Alex")?.guess,
        ).toBe(revealed.own.guess);
      completed.push({
        round: round + 1,
        order: roundNames,
        creatorRole: revealed.role,
        revealIndex: revealed.reveal_index,
        scores: revealed.results?.map(({ player, points }) => ({
          player,
          points,
        })),
      });
      await creator.screenshot({
        path: testInfo.outputPath(`reverse-round-${round + 1}-results.png`),
        fullPage: true,
      });
      await creator
        .getByRole("button", { name: "Start another round", exact: true })
        .click();
      await expect.poll(async () => (await state(creator)).phase).toBe("lobby");
      expect((await state(creator)).round_id).not.toBe(revealed.round_id);
    }
    const wrapped = await state(creator);
    expect(wrapped.role).toBe("A");
    expect(wrapped.players.map((player) => player.name)).toEqual(names);
    expect(wrapped.code).toBe(originalLobby.code);
    expect(wrapped.remaining_attempts).toBe(originalLobby.remaining_attempts);
    await testInfo.attach("Reverse three-round rehearsal", {
      body: JSON.stringify(
        { mode: "rehearsal", completed, liveAttemptsConsumed: 0 },
        null,
        2,
      ),
      contentType: "application/json",
    });
  } finally {
    if (hosted)
      await creator.request.post(origin + "/api/party/close", {
        data: { game_id: "reverse-prompt" },
      });
    await Promise.all(contexts.map((context) => context.close()));
  }
});
