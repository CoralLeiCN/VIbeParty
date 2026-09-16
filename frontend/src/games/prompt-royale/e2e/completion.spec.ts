import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "../../../../..");
const passcode =
  fs
    .readFileSync(path.join(root, ".env"), "utf8")
    .split("\n")
    .find((line) => line.startsWith("HOST_PASSCODE="))
    ?.slice("HOST_PASSCODE=".length)
    .trim()
    .replace(/^['"]|['"]$/g, "") || "WMHACK";
const live = process.env.ROYALE_LIVE_E2E === "1";

test(`background host finishes a scored ${live ? "live" : "fixture"} round`, async ({
  browser,
  baseURL,
}, testInfo) => {
  test.setTimeout(300_000);
  const contexts = await Promise.all(
    [0, 1, 2].map((index) =>
      browser.newContext({
        viewport:
          index === 1
            ? { width: 390, height: 844 }
            : { width: 1360, height: 1000 },
      }),
    ),
  );
  const pages = await Promise.all(contexts.map((context) => context.newPage()));
  const host = pages[0];
  const errors: string[] = [];
  pages.forEach((page) =>
    page.on("pageerror", (error) => errors.push(error.message)),
  );
  let ownsRoom = false;
  try {
    await host.goto(baseURL + "/games/prompt-royale/host");
    await host.getByLabel("Your name", { exact: true }).fill("Alex");
    await host.getByLabel("Host access code").fill(passcode);
    await host.getByLabel("Number of players").selectOption("3");
    await host
      .getByRole("button", { name: "Create party", exact: true })
      .click();
    await expect(host.getByLabel("Invite your friends")).toBeVisible();
    ownsRoom = true;
    const joinURL = await host.getByLabel("Invite your friends").inputValue();
    const code = new URL(joinURL).searchParams.get("code")!;
    await host
      .getByLabel("Video generation")
      .selectOption(live ? "live" : "fixture");
    for (const [index, name] of [
      [1, "Bailey"],
      [2, "Casey"],
    ] as const) {
      await pages[index].goto(
        `${baseURL}/games/prompt-royale/join?code=${code}`,
      );
      await pages[index].getByLabel("Your name", { exact: true }).fill(name);
      await pages[index]
        .getByRole("button", { name: "Join party", exact: true })
        .click();
      await expect(
        pages[index].getByRole("listitem").filter({ hasText: `${name} · You` }),
      ).toBeVisible();
    }
    await expect(host.getByText("3/3", { exact: true })).toBeVisible();
    await host.getByLabel("Choose a topic").selectOption({ index: 1 });
    await host.getByRole("button", { name: "Start round ↗" }).click();
    await expect(host.getByLabel("Your private scene")).toBeVisible();

    // Exercise the actual visibility branch that previously stopped presence polling.
    let backgroundPolls = 0;
    host.on("response", (response) => {
      if (
        response.url().endsWith("/api/games/prompt-royale/room") &&
        response.status() === 200
      )
        backgroundPolls += 1;
    });
    await host.evaluate(() => {
      Object.defineProperty(document, "hidden", {
        configurable: true,
        get: () => true,
      });
      Object.defineProperty(document, "visibilityState", {
        configurable: true,
        get: () => "hidden",
      });
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await host.waitForTimeout(35_000);
    expect(backgroundPolls).toBeGreaterThan(20);
    await expect(host.getByLabel("Your private scene")).toBeVisible();
    const prompts = [
      "A penguin in a business suit slides through an office carrying a stack of coffee cups.",
      "A robot receptionist shakes hands with a coat rack in a bright office lobby.",
      "A tiny dragon in a tie accidentally toasts paperwork while sneezing at a desk.",
    ];
    for (let index = 0; index < pages.length; index += 1) {
      await pages[index].getByLabel("Your private scene").fill(prompts[index]);
      await pages[index]
        .getByRole("button", { name: "Submit scene", exact: true })
        .click();
    }
    await expect(
      host.getByRole("region", { name: "Anonymous arena" }),
    ).toBeVisible({ timeout: 190_000 });
    await expect(host.locator("video")).toHaveCount(3);
    await expect(
      host.getByText("Unscored / no winner", { exact: true }),
    ).not.toBeVisible();
    await host.evaluate(() => {
      delete (document as unknown as Record<string, unknown>).hidden;
      delete (document as unknown as Record<string, unknown>).visibilityState;
      document.dispatchEvent(new Event("visibilitychange"));
    });
    const screening = await (
      await host.request.get(baseURL + "/api/games/prompt-royale/room")
    ).json();
    expect(screening.mode).toBe(live ? "live" : "fixture");
    expect(screening.phase).toBe("screening");
    await host.locator("video").evaluateAll((nodes) => {
      nodes.forEach((node) => {
        const video = node as HTMLVideoElement;
        video.dataset.completedPlays = "0";
        video.addEventListener("ended", () => {
          video.dataset.completedPlays = String(
            Number(video.dataset.completedPlays) + 1,
          );
        });
      });
    });
    for (const page of pages) {
      await expect(
        page.getByRole("button", { name: "Play arena", exact: true }),
      ).toBeEnabled();
      await page
        .getByRole("button", { name: "Play arena", exact: true })
        .click();
    }
    await expect
      .poll(() =>
        host.locator("video").evaluateAll((nodes) =>
          nodes.every((node) => {
            const video = node as HTMLVideoElement;
            return (
              video.currentTime > 0 &&
              (!video.paused || video.ended) &&
              video.videoWidth > 0 &&
              video.error === null
            );
          }),
        ),
      )
      .toBeTruthy();
    await host.waitForTimeout(6_000);
    const playback = await host.locator("video").evaluateAll((nodes) =>
      nodes.map((node) => {
        const video = node as HTMLVideoElement;
        return {
          duration: video.duration,
          width: video.videoWidth,
          height: video.videoHeight,
          error: video.error,
          paused: video.paused,
          ended: video.ended,
          completedPlays: Number(video.dataset.completedPlays),
        };
      }),
    );
    expect(
      playback.every(
        (video) =>
          video.duration > 0 &&
          video.duration <= 5.08 &&
          !video.error &&
          (!video.paused || video.ended) &&
          video.completedPlays >= 1,
      ),
    ).toBeTruthy();
    if (process.env.ROYALE_EXPECT_SHORT_E2E === "1") {
      expect(playback.some((video) => video.duration < 0.1)).toBeTruthy();
      expect(playback.some((video) => video.duration > 4.9)).toBeTruthy();
    }
    await testInfo.attach("arena", {
      body: await host.screenshot({ fullPage: true }),
      contentType: "image/png",
    });
    if (live) {
      const clipURLs = await host
        .locator("video")
        .evaluateAll((nodes) =>
          nodes.map((node) => (node as HTMLVideoElement).currentSrc),
        );
      for (const [index, url] of clipURLs.entries()) {
        const clip = await host.request.get(url);
        expect(clip.ok()).toBeTruthy();
        await testInfo.attach(`live-clip-${index + 1}`, {
          body: await clip.body(),
          contentType: "video/mp4",
        });
      }
    }
    await host.getByRole("checkbox").check();
    await host
      .getByRole("button", { name: "Open voting", exact: true })
      .click();
    await Promise.all(
      pages.map(async (page) => {
        await page
          .getByRole("button", { name: /^Choose Clip/ })
          .first()
          .click();
        await page.getByRole("button", { name: "Vote", exact: true }).click();
      }),
    );
    for (const page of pages)
      await expect(
        page.getByText(/We have a winner!|A shared crown!/),
      ).toBeVisible();
    const result = await (
      await host.request.get(baseURL + "/api/games/prompt-royale/room")
    ).json();
    expect(result.scored).toBe(true);
    expect(result.winners.length).toBeGreaterThan(0);
    expect(
      result.arena.reduce(
        (sum: number, tile: { votes?: number }) => sum + (tile.votes || 0),
        0,
      ),
    ).toBe(3);
    await testInfo.attach("result", {
      body: Buffer.from(
        JSON.stringify(
          {
            mode: result.mode,
            code,
            phase: result.phase,
            scored: result.scored,
            winners: result.winners,
            backgroundPolls,
            playback,
          },
          null,
          2,
        ),
      ),
      contentType: "application/json",
    });
    await testInfo.attach("results", {
      body: await host.screenshot({ fullPage: true }),
      contentType: "image/png",
    });
    await testInfo.attach("phone-results", {
      body: await pages[1].screenshot({ fullPage: true }),
      contentType: "image/png",
    });
    await host.getByRole("button", { name: "Play again", exact: true }).click();
    await expect(host.getByLabel("Invite your friends")).toHaveValue(joinURL);
    await expect(host.getByLabel("Choose a topic")).toHaveValue("");
    await host.getByRole("button", { name: "End room", exact: true }).click();
    ownsRoom = false;
    await expect(
      host.getByRole("button", { name: "Create party", exact: true }),
    ).toBeVisible();
    const retired = await host.request.post(baseURL + "/api/party/resolve", {
      data: { code },
      headers: { Origin: baseURL! },
    });
    expect(retired.status()).toBe(404);
    expect(errors).toEqual([]);
  } finally {
    if (ownsRoom)
      await host.request
        .delete(baseURL + "/api/games/prompt-royale/room", {
          data: {},
          headers: { Origin: baseURL! },
        })
        .catch(() => {});
    await Promise.all(contexts.map((context) => context.close()));
  }
});
