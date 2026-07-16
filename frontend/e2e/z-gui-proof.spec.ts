import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const artifactDirectory = path.resolve("e2e-artifacts");

async function prepareArtifacts() {
  await mkdir(artifactDirectory, { recursive: true });
}

test("captures focused desktop GUI proof and browser diagnostics", async ({ page }) => {
  await prepareArtifacts();
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];

  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: /TRACE IAM Evidence/i })).toBeVisible();
  await expect(page.locator("#operations-dashboard")).toBeVisible();

  await page.screenshot({
    path: path.join(artifactDirectory, "gui-desktop-shell.png"),
    fullPage: false,
  });
  await page.locator("#operations-dashboard").screenshot({
    path: path.join(artifactDirectory, "gui-desktop-dashboard.png"),
  });

  const duplicateIds = await page.evaluate(() => {
    const counts = new Map<string, number>();
    document.querySelectorAll<HTMLElement>("[id]").forEach((element) => {
      counts.set(element.id, (counts.get(element.id) ?? 0) + 1);
    });
    return [...counts.entries()].filter(([, count]) => count > 1);
  });

  const unnamedButtons = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLButtonElement>("button")]
      .filter((button) => !button.disabled)
      .filter((button) => !(button.innerText || button.getAttribute("aria-label") || button.getAttribute("title")))
      .length,
  );

  const landmarkSummary = await page.evaluate(() => ({
    main: document.querySelectorAll("main").length,
    navigation: document.querySelectorAll("nav").length,
    headings: document.querySelectorAll("h1, h2, h3, h4").length,
  }));

  await writeFile(
    path.join(artifactDirectory, "gui-browser-diagnostics.json"),
    JSON.stringify({ consoleErrors, pageErrors, duplicateIds, unnamedButtons, landmarkSummary }, null, 2),
    "utf8",
  );

  expect(pageErrors).toEqual([]);
  expect(duplicateIds).toEqual([]);
  expect(unnamedButtons).toBe(0);
  expect(landmarkSummary.main).toBeGreaterThanOrEqual(1);
  expect(landmarkSummary.navigation).toBeGreaterThanOrEqual(1);
});

test("captures narrow responsive GUI proof and keyboard focus", async ({ page }) => {
  await prepareArtifacts();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: /TRACE IAM Evidence/i })).toBeVisible();

  await page.keyboard.press("Tab");
  const focusedTag = await page.evaluate(() => document.activeElement?.tagName ?? null);
  expect(focusedTag).not.toBe("BODY");

  await page.screenshot({
    path: path.join(artifactDirectory, "gui-narrow-shell.png"),
    fullPage: false,
  });

  await page.locator("#operations-dashboard").scrollIntoViewIfNeeded();
  await page.locator("#operations-dashboard").screenshot({
    path: path.join(artifactDirectory, "gui-narrow-dashboard.png"),
  });

  const horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  await writeFile(
    path.join(artifactDirectory, "gui-responsive-diagnostics.json"),
    JSON.stringify({ viewport: { width: 390, height: 844 }, focusedTag, horizontalOverflow }, null, 2),
    "utf8",
  );

  expect(horizontalOverflow).toBe(false);
});
