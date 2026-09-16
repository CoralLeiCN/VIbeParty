import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "../../../../..");
const env = Object.fromEntries(
  fs
    .readFileSync(path.join(ROOT, ".env"), "utf8")
    .split("\n")
    .filter((line) => line && !line.startsWith("#") && line.includes("="))
    .map((line) => [
      line.slice(0, line.indexOf("=")),
      line.slice(line.indexOf("=") + 1).trim(),
    ]),
);

test("three and four directors: both topics, refresh, coordinated arena, vote, replay, cleanup", async ({
  browser,
  baseURL,
}) => {
  for (const size of [3, 4]) {
    const contexts = await Promise.all(
      Array.from({ length: size }, (_, i) =>
        browser.newContext({
          viewport:
            i === 1
              ? { width: 390, height: 844 }
              : { width: 1280, height: 900 },
        }),
      ),
    );
    const pages = await Promise.all(
      contexts.map((context) => context.newPage()),
    );
    const host = pages[0];
    const errors: string[] = [];
    pages.forEach((page) =>
      page.on("pageerror", (error) => errors.push(error.message)),
    );
    try {
      await host.goto(baseURL + "/games/prompt-royale/host");
      await host.getByLabel("Your name", { exact: true }).fill("Director 1");
      await host.getByLabel("Number of players").selectOption(String(size));
      const config = await (
        await host.request.get(baseURL + "/api/config")
      ).json();
      if (!config.local_mode)
        await host
          .getByLabel("Host access code")
          .fill(env.HOST_PASSCODE || "WMHACK");
      await host
        .getByRole("button", { name: "Create party", exact: true })
        .click();
      await expect(host.getByLabel("Invite your friends")).toBeVisible();
      const joinURL = await host.getByLabel("Invite your friends").inputValue();
      const roomCode = new URL(joinURL).searchParams.get("code")!;
      expect(roomCode).toMatch(/^[0-9]{4}$/);
      if (process.env.ROYALE_EXPECT_CODE)
        expect(roomCode).toBe(process.env.ROYALE_EXPECT_CODE);
      await host.reload();
      await expect(host.getByLabel("Invite your friends")).toHaveValue(joinURL);
      await host
        .getByRole("button", { name: "Copy link", exact: true })
        .click();
      await expect(
        host.getByRole("button", { name: "Link copied ✓" }),
      ).toBeVisible();
      for (let i = 1; i < size; i++) {
        if (i === 1) {
          await pages[i].goto(baseURL + "/join");
          await pages[i].getByLabel("Room code", { exact: true }).fill("12 34");
          await pages[i].getByRole("button", { name: /Find my party/ }).click();
          await expect(
            pages[i].getByText("Enter a 4-digit room code."),
          ).toBeVisible();
          await pages[i]
            .getByLabel("Room code", { exact: true })
            .fill(` ${roomCode} `);
          await pages[i].getByRole("button", { name: /Find my party/ }).click();
          await expect(pages[i]).toHaveURL(joinURL);
        } else if (i === 2) {
          await pages[i].goto(baseURL + "/games/prompt-royale/join");
          await pages[i]
            .getByLabel("Room code", { exact: true })
            .fill(` ${roomCode} `);
        } else {
          await pages[i].goto(joinURL);
          await expect(
            pages[i].getByLabel("Room code", { exact: true }),
          ).toHaveValue(roomCode);
        }
        const field = pages[i].getByLabel("Room code", { exact: true });
        await expect(field).toHaveAttribute("type", "text");
        await expect(field).toHaveAttribute("inputmode", "numeric");
        await expect(field).toHaveAttribute("pattern", "[0-9]{4}");
        await pages[i]
          .getByLabel("Your name", { exact: true })
          .fill(`Director ${i + 1}`);
        await pages[i]
          .getByRole("button", { name: "Join party", exact: true })
          .click();
      }
      await expect(
        host.getByText(`${size}/${size}`, { exact: true }),
      ).toBeVisible();
      if (size === 3) {
        await host.getByLabel("Choose a topic").selectOption({ index: 1 });
      } else {
        await host
          .getByRole("button", { name: "Auto-generated topic" })
          .click();
        await host
          .getByRole("button", { name: "Generate topic", exact: true })
          .click();
        await expect(
          host.getByRole("button", { name: "Confirm topic" }),
        ).toBeVisible();
        await host.getByRole("button", { name: "Confirm topic" }).click();
        await expect(
          host.getByRole("button", { name: "Topic confirmed ✓" }),
        ).toBeVisible();
        await host.getByRole("button", { name: "Generate another" }).click();
        await expect(
          host.getByRole("button", { name: "Start round ↗" }),
        ).toBeDisabled();
        await expect(
          host.getByRole("button", { name: "Confirm topic" }),
        ).toBeVisible();
        await host.getByRole("button", { name: "Confirm topic" }).click();
      }
      await host.getByRole("button", { name: "Start round ↗" }).click();
      for (let i = 0; i < size; i++) {
        await pages[i]
          .getByLabel("Your private scene")
          .fill(`A dancing penguin in scene ${i + 1}`);
        if (i === 1) {
          await pages[i].reload();
          await expect(pages[i].getByLabel("Your private scene")).toHaveValue(
            `A dancing penguin in scene ${i + 1}`,
          );
        }
        await pages[i].getByRole("button", { name: "Submit scene" }).click();
      }
      for (const page of pages) {
        await expect(
          page.getByRole("region", { name: "Anonymous arena" }),
        ).toBeVisible();
        await expect(page.locator("video")).toHaveCount(size);
        await expect(
          page.getByRole("button", { name: "Play arena", exact: true }),
        ).toBeEnabled();
      }
      const snapshot = await host.request.get(
        baseURL + "/api/games/prompt-royale/room",
      );
      const state = await snapshot.json();
      if (size === 3) {
        const failedURL = "**" + state.arena[0].url;
        await pages[1].route(failedURL, (route) => route.abort());
        await pages[1].reload();
        await expect(
          pages[1].getByText("Playback unavailable", { exact: true }),
        ).toBeVisible();
        await pages[1].unroute(failedURL);
        await pages[1]
          .getByRole("button", { name: "Retry playback", exact: true })
          .click();
        await expect(
          pages[1].getByRole("button", { name: "Play arena", exact: true }),
        ).toBeEnabled();
        await pages[2].evaluate(() => {
          const original = HTMLMediaElement.prototype.play;
          let blockOnce = true;
          HTMLMediaElement.prototype.play = function () {
            if (blockOnce) {
              blockOnce = false;
              return Promise.reject(
                new DOMException("Blocked for rehearsal", "NotAllowedError"),
              );
            }
            return original.call(this);
          };
        });
      }
      for (const page of pages) {
        const peer = await (
          await page.request.get(baseURL + "/api/games/prompt-royale/room")
        ).json();
        expect(peer.arena).toEqual(state.arena);
        expect(
          peer.arena.every(
            (tile: object) => !("author" in tile) && !("prompt" in tile),
          ),
        ).toBeTruthy();
        await page
          .getByRole("button", { name: "Play arena", exact: true })
          .click();
        if (size === 3 && page === pages[2]) {
          await expect(
            page.getByText(
              "Playback was blocked. Tap Play arena to try again.",
              { exact: true },
            ),
          ).toBeVisible();
          await page
            .getByRole("button", { name: "Play arena", exact: true })
            .click();
        }
      }
      await expect
        .poll(() =>
          host
            .locator("video")
            .evaluateAll((videos) =>
              videos.every((v) => !(v as HTMLVideoElement).paused),
            ),
        )
        .toBeTruthy();
      await host.waitForTimeout(5700);
      const playback = await host.locator("video").evaluateAll((videos) =>
        videos.map((v) => ({
          time: (v as HTMLVideoElement).currentTime,
          paused: (v as HTMLVideoElement).paused,
          duration: (v as HTMLVideoElement).duration,
        })),
      );
      expect(
        playback.every((v) => !v.paused && Math.abs(v.duration - 5) < 0.1),
      ).toBeTruthy();
      expect(
        Math.max(...playback.map((v) => v.time)) -
          Math.min(...playback.map((v) => v.time)),
      ).toBeLessThan(0.35);
      await host.getByRole("button", { name: "Pause all" }).click();
      expect(
        await host
          .locator("video")
          .evaluateAll((videos) =>
            videos.every((v) => (v as HTMLVideoElement).paused),
          ),
      ).toBeTruthy();
      await host.getByRole("button", { name: "Replay all" }).click();
      await host.screenshot({
        path: path.join(ROOT, `.local/prompt-royale-${size}-arena.png`),
        fullPage: true,
      });
      await pages[1].screenshot({
        path: path.join(ROOT, `.local/prompt-royale-${size}-phone.png`),
        fullPage: true,
      });
      await pages[1].reload();
      await expect(pages[1].locator("video")).toHaveCount(size);
      const refreshed = await (
        await pages[1].request.get(baseURL + "/api/games/prompt-royale/room")
      ).json();
      expect(refreshed.arena).toEqual(state.arena);
      if (size === 4) {
        const firstTile = host.getByTestId("tile-0");
        await firstTile.locator("summary").click();
        await firstTile
          .getByLabel("Public exclusion reason")
          .fill("Rehearsal exclusion");
        await firstTile
          .getByRole("button", { name: "Exclude Clip 1", exact: true })
          .click();
        await expect(
          firstTile.getByText("Excluded", { exact: true }),
        ).toBeVisible();
        await expect(host.locator("video")).toHaveCount(3);
      }
      await host.getByRole("checkbox").check();
      await host
        .getByRole("button", { name: "Open voting", exact: true })
        .click();
      for (const page of pages) {
        await page
          .getByRole("button", { name: /^Choose Clip/ })
          .first()
          .click();
        await page.getByRole("button", { name: "Vote", exact: true }).click();
      }
      for (const page of pages)
        await expect(
          page.getByText(/We have a winner!|A shared crown!/),
        ).toBeVisible();
      await host.screenshot({
        path: path.join(ROOT, `.local/prompt-royale-${size}-results.png`),
        fullPage: true,
      });
      await host
        .getByRole("button", { name: "Play again", exact: true })
        .click();
      await expect(host.getByLabel("Choose a topic")).toHaveValue("");
      await expect(host.getByLabel("Invite your friends")).toHaveValue(joinURL);
      await host.goto(baseURL + "/");
      await host.getByRole("link", { name: /Continue party/ }).click();
      await expect(host.getByLabel("Invite your friends")).toHaveValue(joinURL);
      await host.getByRole("button", { name: "End room", exact: true }).click();
      await expect(
        host.getByRole("button", { name: "Create party", exact: true }),
      ).toBeVisible();
      const retired = await host.request.post(baseURL + "/api/party/resolve", {
        data: { code: roomCode },
        headers: { Origin: baseURL! },
      });
      expect(retired.status()).toBe(404);
      expect(errors).toEqual([]);
    } finally {
      await host.request
        .delete(baseURL + "/api/games/prompt-royale/room", {
          data: {},
          headers: { Origin: baseURL! },
        })
        .catch(() => {});
      await Promise.all(contexts.map((context) => context.close()));
    }
  }
});

test("room code correction and code-only links preserve leading zeros", async ({
  browser,
  baseURL,
}) => {
  const contexts = await Promise.all(
    Array.from({ length: 3 }, () => browser.newContext()),
  );
  const host = contexts[0];
  try {
    const created = await host.request.post(
      baseURL + "/api/games/prompt-royale/room",
      {
        data: { name: "Code host", passcode: env.HOST_PASSCODE || "WMHACK" },
        headers: { Origin: baseURL! },
      },
    );
    expect(created.ok()).toBeTruthy();
    const state = await created.json();
    expect(state.mode).toBe("fixture");
    if (process.env.ROYALE_EXPECT_CODE)
      expect(state.code).toBe(process.env.ROYALE_EXPECT_CODE);
    const guest = await contexts[1].newPage();
    await guest.goto(baseURL + "/games/prompt-royale/join");
    await guest.getByLabel("Your name", { exact: true }).fill("Code guest");
    const field = guest.getByLabel("Room code", { exact: true });
    for (const invalid of ["42", "12345", "12 34", "ABCD", "１２３４"]) {
      await field.fill(invalid);
      await guest
        .getByRole("button", { name: "Join party", exact: true })
        .click();
      await expect(guest.getByText("Enter a 4-digit room code.")).toBeVisible();
      await expect(field).toHaveValue(invalid);
      await expect(field).toBeEditable();
    }
    await guest.screenshot({
      path: path.join(ROOT, ".local/prompt-royale-room-code.png"),
      fullPage: true,
    });
    await field.fill(state.code === "9999" ? "0000" : "9999");
    await guest
      .getByRole("button", { name: "Join party", exact: true })
      .click();
    await expect(
      guest.getByText(
        "That party isn't available. Check the code with your host.",
      ),
    ).toBeVisible();
    await field.fill(` ${state.code} `);
    await guest
      .getByRole("button", { name: "Join party", exact: true })
      .click();
    await expect(guest.getByText("2/3", { exact: true })).toBeVisible();
    const linked = await contexts[2].newPage();
    await linked.goto(baseURL + "/join?code=" + state.code);
    await expect(linked).toHaveURL(state.join_url);
    await expect(linked.getByLabel("Room code", { exact: true })).toHaveValue(
      state.code,
    );
    expect(
      (
        await linked.request.get(baseURL + "/api/games/prompt-royale/room")
      ).status(),
    ).toBe(401);
    await linked.getByLabel("Your name", { exact: true }).fill("Linked guest");
    await linked
      .getByRole("button", { name: "Join party", exact: true })
      .click();
    await expect(linked.getByText("3/3", { exact: true })).toBeVisible();
  } finally {
    await host.request
      .delete(baseURL + "/api/games/prompt-royale/room", {
        data: {},
        headers: { Origin: baseURL! },
      })
      .catch(() => {});
    await Promise.all(contexts.map((context) => context.close()));
  }
});
