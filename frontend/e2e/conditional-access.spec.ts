import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";

test("operator creates, triages, analyzes, reviews, and reopens a real case", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "TRACE IAM Evidence" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create investigation" })).toBeEnabled();

  await page.locator("#case-name").fill("Conditional Access sign-in review");
  await page.getByRole("combobox", { name: "Scenario", exact: true }).selectOption("conditional_access");
  await page.locator("#case-priority").selectOption("high");
  await page.locator("#case-reference").fill("INC-REDACTED-CA-01");
  await page.locator("#case-summary").fill("Redacted sign-in failure affecting a managed application.");
  const createResponsePromise = page.waitForResponse((response) => response.url().endsWith("/api/investigations") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Create investigation" }).click();
  expect((await createResponsePromise).ok()).toBeTruthy();

  const activeCase = page.locator(".active-case");
  const investigationId = (await activeCase.locator("code").textContent())?.trim();
  expect(investigationId).toMatch(/^trace-[a-f0-9]{12}$/);
  await expect(activeCase.getByText("High priority")).toBeVisible();
  await expect(activeCase.getByText("INC-REDACTED-CA-01")).toBeVisible();
  await expect(page.getByRole("button", { name: "Analyze evidence" })).toBeEnabled();

  await page.locator("#edit-priority").selectOption("critical");
  await page.locator("#edit-summary").fill("Escalated redacted sign-in failure under active review.");
  const patchResponsePromise = page.waitForResponse((response) => response.url().endsWith(`/api/investigations/${investigationId}`) && response.request().method() === "PATCH");
  await page.getByRole("button", { name: "Save case metadata" }).click();
  expect((await patchResponsePromise).ok()).toBeTruthy();
  await expect(activeCase.getByText("Critical priority")).toBeVisible();
  await expect(page.getByText("Case metadata saved without changing immutable analysis runs.")).toBeVisible();

  const responsePromise = page.waitForResponse((response) => response.url().includes("analyze-conditional-access-csv"));
  await page.getByRole("button", { name: "Analyze evidence" }).click();
  expect((await responsePromise).ok()).toBeTruthy();

  await expect(page.getByRole("heading", { name: "Analysis result" })).toBeVisible();
  const summary = page.getByRole("region", { name: "Analysis result" }).getByLabel("Analysis summary");
  await expect(summary).toContainText("CA-001");
  await expect(page.getByTestId("markdown-report")).toContainText("Do not disable Conditional Access globally");

  const historyRow = page.getByRole("button", { name: "Conditional Access sign-in review" }).locator("..");
  await expect(historyRow).toContainText("analyzed · 1 run(s)");
  await expect(historyRow).toContainText("Critical priority");
  await expect(page.getByRole("link", { name: "Export JSON" })).toHaveAttribute("href", `/api/investigations/${investigationId}/runs/1/report.json`);

  const reviewResponsePromise = page.waitForResponse((response) => response.url().endsWith(`/api/investigations/${investigationId}/transition`));
  await page.getByRole("button", { name: "Mark reviewed" }).click();
  expect((await reviewResponsePromise).ok()).toBeTruthy();
  await expect(page.getByText("Lifecycle moved to reviewed.")).toBeVisible();
  await expect(historyRow).toContainText("reviewed · 1 run(s)");

  await historyRow.getByRole("button", { name: "Archive" }).click();
  await page.getByLabel("Show archived investigations").check();
  await expect(page.getByText("archived · 1 run(s)")).toBeVisible();
  await page.getByRole("button", { name: "Reopen" }).click();
  await expect(page.getByText("reviewed · 1 run(s)")).toBeVisible();

  const jsonReportResponse = await page.request.get(`/api/investigations/${investigationId}/runs/1/report.json`);
  const markdownReportResponse = await page.request.get(`/api/investigations/${investigationId}/runs/1/report.md`);
  expect(jsonReportResponse.ok()).toBeTruthy();
  expect(markdownReportResponse.ok()).toBeTruthy();

  await mkdir("e2e-artifacts", { recursive: true });
  await writeFile("e2e-artifacts/report.json", JSON.stringify(await jsonReportResponse.json(), null, 2));
  await writeFile("e2e-artifacts/report.md", await markdownReportResponse.text());
  await page.screenshot({ path: "e2e-artifacts/investigation-history.png", fullPage: true });
});
