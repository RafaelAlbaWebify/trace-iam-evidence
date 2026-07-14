import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";

test("operator creates and analyzes a persisted Guest B2B case", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Create investigation" })).toBeEnabled();

  await page.getByLabel("Case title").fill("Guest B2B lifecycle review");
  await page.getByRole("combobox", { name: "Scenario", exact: true }).selectOption("guest_b2b");
  const createResponsePromise = page.waitForResponse((response) => response.url().endsWith("/api/investigations") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Create investigation" }).click();
  expect((await createResponsePromise).ok()).toBeTruthy();

  const investigationId = (await page.locator(".active-case code").textContent())?.trim();
  expect(investigationId).toMatch(/^trace-[a-f0-9]{12}$/);
  await expect(page.getByLabel("Invitation was sent")).toBeChecked();
  await expect(page.getByLabel("Invitation was redeemed")).not.toBeChecked();
  await expect(page.getByRole("button", { name: "Analyze Guest B2B evidence" })).toBeEnabled();

  const responsePromise = page.waitForResponse((response) => response.url().includes("analyze-guest-b2b"));
  await page.getByRole("button", { name: "Analyze Guest B2B evidence" }).click();
  expect((await responsePromise).ok()).toBeTruthy();

  await expect(page.getByRole("heading", { name: "Analysis result" })).toBeVisible();
  const summary = page.locator(".result-summary");
  await expect(summary).toContainText("GB-002, GB-001, GB-003");
  await expect(page.getByTestId("markdown-report")).toContainText("Do not recreate the guest or issue repeated invitations");

  const historyRow = page.getByRole("button", { name: "Guest B2B lifecycle review" }).locator("..");
  await expect(historyRow).toContainText("guest_b2b");
  await expect(historyRow).toContainText("analyzed · 1 run(s)");
  const runsPanel = page.getByRole("heading", { name: `Analysis runs for ${investigationId}` }).locator("..");
  await expect(runsPanel).toContainText("GB-001@1.0.0+GB-002@1.0.0+GB-003@1.0.0");
  await expect(runsPanel.getByRole("link", { name: "Export JSON" })).toHaveAttribute("href", `/api/investigations/${investigationId}/runs/1/report.json`);

  const jsonReportResponse = await page.request.get(`/api/investigations/${investigationId}/runs/1/report.json`);
  const markdownReportResponse = await page.request.get(`/api/investigations/${investigationId}/runs/1/report.md`);
  expect(jsonReportResponse.ok()).toBeTruthy();
  expect(markdownReportResponse.ok()).toBeTruthy();

  await mkdir("e2e-artifacts", { recursive: true });
  await writeFile("e2e-artifacts/guest-b2b-report.json", JSON.stringify(await jsonReportResponse.json(), null, 2));
  await writeFile("e2e-artifacts/guest-b2b-report.md", await markdownReportResponse.text());
  await page.screenshot({ path: "e2e-artifacts/guest-b2b-history.png", fullPage: true });
});
