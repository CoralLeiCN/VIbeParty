import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import { writeFile } from "node:fs/promises";

const origin = process.env.PORTAL_URL || "http://localhost:8000";
const api = "/api/games/word-by-word";

async function post(page: Page, path: string, data: object) {
  const response = await page.request.post(origin + path, { data });
  expect(response.ok(), `${path}: ${await response.text()}`).toBeTruthy();
  return response.json();
}

async function state(page: Page) {
  const response = await page.request.get(origin + api + "/state");
  expect(response.ok()).toBeTruthy();
  return response.json();
}

function currentTime(video: Locator) {
  return video.evaluate((element: HTMLVideoElement) => element.currentTime);
}

async function expectCurrentCard(page: Page, video: Locator) {
  const snapshot = await state(page);
  const position = await currentTime(video);
  const card = snapshot.cards
    .toReversed()
    .find((item: { at_seconds: number }) => item.at_seconds <= position);
  expect(card).toBeDefined();
  await expect(page.locator(".wbw-current-card")).toContainText(card.text);
}

// Record the first actual frame after an action, so a restart cannot pass by
// eventually playing all the way back to the position before interruption.
function nextPlayingPosition(video: Locator) {
  return video.evaluate(
    (element: HTMLVideoElement) =>
      new Promise<number>((resolve) => {
        element.addEventListener(
          "playing",
          () => resolve(element.currentTime),
          {
            once: true,
          },
        );
      }),
  );
}

test("WW-CAT-01 reconnects HLS and saved playback; Replay starts over even while reconnecting", async ({
  browser,
}, testInfo) => {
  const hostContext = await browser.newContext({
    baseURL: origin,
    extraHTTPHeaders: { Origin: origin },
  });
  const playerContext = await browser.newContext({
    baseURL: origin,
    extraHTTPHeaders: { Origin: origin },
  });
  const host = await hostContext.newPage();
  const player = await playerContext.newPage();
  const recoveryResults: { interrupted: number; resumed: number }[] = [];
  let hosted = false;
  try {
    const lobby = await post(host, api + "/host", {
      passcode: process.env.DEMO_HOST_CODE || "WMHACK",
    });
    hosted = true;
    await post(host, api + "/room/settings", {
      round_id: lobby.round_id,
      player_count: 1,
    });
    await post(player, api + "/join", { code: lobby.code, name: "Bailey" });
    await post(host, api + "/round/start", {
      round_id: lobby.round_id,
      mode: "fixture",
    });
    await host.goto("/games/word-by-word/host");
    const input = await state(player);
    expect(
      input.assignments.map(
        (assignment: { fixture_text: string }) => assignment.fixture_text,
      ),
    ).toEqual([
      "Enchanted forest",
      "A fox wearing a crown",
      "Dances ballet",
      "Glowing snow begins falling",
    ]);

    let blockFromSegment = Number.POSITIVE_INFINITY;
    const blockedSegments: number[] = [];
    await host.route(/\/media\/[^/]+\/segment\d+\.ts$/, async (route) => {
      const segment = Number(
        route
          .request()
          .url()
          .match(/segment(\d+)\.ts$/)![1],
      );
      if (segment >= blockFromSegment) {
        blockedSegments.push(segment);
        await route.abort("connectionfailed");
      } else await route.continue();
    });
    for (const assignment of input.assignments) {
      await post(player, api + "/contribution", {
        round_id: input.round_id,
        slot_index: assignment.index,
        text: assignment.fixture_text,
      });
    }

    const video = host.getByLabel("Continuous story", { exact: true });
    await expect(video).toBeVisible({ timeout: 15000 });
    await expect
      .poll(() => currentTime(video), { timeout: 15000 })
      .toBeGreaterThan(4);
    const streaming = await state(host);
    const mutations: string[] = [];
    host.on("request", (request) => {
      if (request.url().includes("/api/") && request.method() !== "GET") {
        mutations.push(
          `${request.method()} ${new URL(request.url()).pathname}`,
        );
      }
    });

    // Fail real segment requests while the backend continues the same round.
    // The later boundary leaves enough media for progress between reconnects.
    blockFromSegment = 8;
    for (const nextBoundary of [14, Number.POSITIVE_INFINITY]) {
      const reconnect = host.getByRole("button", {
        name: "Reconnect video",
        exact: true,
      });
      await expect(reconnect).toBeVisible({ timeout: 30000 });
      const interrupted = await currentTime(video);
      expect(interrupted).toBeGreaterThan(4);
      blockFromSegment = nextBoundary;
      const playback = nextPlayingPosition(video);
      await reconnect.click();
      const resumed = await playback;
      recoveryResults.push({ interrupted, resumed });
      expect(resumed).toBeGreaterThanOrEqual(interrupted - 0.1);
      expect(resumed).toBeLessThan(interrupted + 1);
      await expect
        .poll(() => currentTime(video))
        .toBeGreaterThan(interrupted + 0.5);
      await expect(reconnect).toHaveCount(0);
      const recovered = await state(host);
      expect(recovered.round_id).toBe(streaming.round_id);
      expect(recovered.stream_url).toBe(streaming.stream_url);
      expect(recovered.live_attempts_left).toBe(streaming.live_attempts_left);
      await expectCurrentCard(host, video);
    }
    expect(blockedSegments).toContain(8);
    expect(blockedSegments).toContain(14);

    await expect
      .poll(async () => (await state(host)).phase, { timeout: 40000 })
      .toBe("RESULTS");
    const replay = host.getByRole("button", {
      name: "Replay saved story ↻",
      exact: true,
    });
    const replayPlayback = nextPlayingPosition(video);
    await replay.click();
    const replayStart = await replayPlayback;
    expect(replayStart).toBeLessThan(0.5);
    const savedVideo = host.getByLabel("Saved story", { exact: true });
    await expect
      .poll(() => currentTime(savedVideo), { timeout: 10000 })
      .toBeGreaterThan(4);

    // MP4 is already buffered on this local server. Simulate its error event,
    // then exercise the real source reload, metadata load, seek, and playback.
    const mp4Interrupted = await savedVideo.evaluate(
      (element: HTMLVideoElement) => {
        element.pause();
        element.dispatchEvent(new Event("error"));
        return element.currentTime;
      },
    );
    const reconnect = host.getByRole("button", {
      name: "Reconnect video",
      exact: true,
    });
    await expect(reconnect).toBeVisible();
    const mp4Playback = nextPlayingPosition(savedVideo);
    await reconnect.click();
    const mp4Resumed = await mp4Playback;
    expect(mp4Resumed).toBeGreaterThanOrEqual(mp4Interrupted - 0.5);
    expect(mp4Resumed).toBeLessThan(mp4Interrupted + 1);
    await expect
      .poll(() => currentTime(savedVideo))
      .toBeGreaterThan(mp4Interrupted + 0.5);
    await expectCurrentCard(host, savedVideo);

    // Hold a real MP4 request before metadata arrives, then choose Replay.
    // The later metadata callback must honor the new requested position of 0.
    let releaseMedia = () => {};
    const mediaGate = new Promise<void>((resolve) => {
      releaseMedia = resolve;
    });
    let mediaRequested = false;
    const recordingPattern = /\/media\/[^/]+\/story\.mp4$/;
    await host.route(recordingPattern, async (route) => {
      mediaRequested = true;
      await mediaGate;
      await route.continue();
    });
    let replayWhileLoadingStart: number;
    try {
      await savedVideo.evaluate((element: HTMLVideoElement) => {
        element.pause();
        element.dispatchEvent(new Event("error"));
      });
      await expect(reconnect).toBeVisible();
      const loadingPlayback = nextPlayingPosition(savedVideo);
      await reconnect.click();
      await expect.poll(() => mediaRequested).toBe(true);
      await replay.click();
      releaseMedia();
      replayWhileLoadingStart = await loadingPlayback;
      expect(replayWhileLoadingStart).toBeLessThan(0.5);
      await expect.poll(() => currentTime(savedVideo)).toBeGreaterThan(0.5);
      await expectCurrentCard(host, savedVideo);
    } finally {
      releaseMedia();
      await host.unroute(recordingPattern);
    }
    expect(mutations).toEqual([]);
    const evidencePath = testInfo.outputPath("word-playback.json");
    await writeFile(
      evidencePath,
      JSON.stringify(
        {
          scenario: "WW-CAT-01",
          mode: "fixture",
          flow: "one-player demo; Bailey owns Place, Character, Action, Consequence",
          recoveryResults,
          blockedSegments,
          replayStart,
          savedPlayback: {
            interruption: "simulated media error after real playback",
            interrupted: mp4Interrupted,
            resumed: mp4Resumed,
            replayWhileLoadingStart,
          },
          browserApiMutations: mutations,
        },
        null,
        2,
      ),
    );
    await testInfo.attach("WW-CAT-01 playback recovery", {
      path: evidencePath,
      contentType: "application/json",
    });
  } finally {
    if (hosted)
      await host.request.post(origin + "/api/party/close", {
        data: { game_id: "word-by-word" },
      });
    await Promise.all([hostContext.close(), playerContext.close()]);
  }
});
