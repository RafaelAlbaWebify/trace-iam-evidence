import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";

test("operator creates a case, analyzes evidence, and manages immutable history", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "TRACE IAM Evidence" })).toBeVisible();
  await expect(page.getByText("No persisted investigations yet.")).toBeVisible();

  await page.getByLabel("Case title").fill("Conditional Access sign-in review");
  await page.getByLabel("Scenario").selectOption("conditional_access");
  const createResponsePromise = page.waitForResponse((response) => response.url().endsWith("/api/investigations") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Create investigation" }).click();
  expect((await createResponsePromise).ok()).toBeTruthy();

  const investigationId = (await page.locator(".active-case code").textContent())?.trim();
  expect(investigationId).toMatch(/^trace-[a-f0-9]{12}$/);
  await expect(page.getByRole("button", { name: "Analyze evidence" })).toBeEnabled();

  const responsePromise = page.waitForResponse((response) => response.url().includes("analyze-conditional-access-csv"));
  await page.getByRole("button", { name: "Analyze evidence" }).click();
  expect((await responsePromise).ok()).toBeTruthy();

  await expect(page.getByRole("heading", { name: "Analysis result" })).toBeVisible();
  const summary = page.getByRole("region", { name: "Analysis result" }).getByLabel("Analysis summary");
  await expect(summary).toContainText("CA-001");
  await expect(page.getByTestId("markdown-report")).toContainText("Do not disable Conditional Access globally");

  const historyRow = page.getByRole("button", { name: "Conditional Access sign-in review" }).locator("..");
  await expect(historyRow).toContainText("analyzed · 1 run(s)");
  await expect(page.getByRole("link", { name: "Export JSON" })).toHaveAttribute("href", `/api/investigations/${investigationId}/runs/1/report.json`);

  await historyRow.getByRole("button", { name: "Archive" }).click();
  await page.getByLabel("Show archived investigations").check();
  await expect(page.getByText("archived · 1 run(s)")).toBeVisible();
  await page.getByRole("button", { name: "Reopen" }).click();
  await expect(page.getByText("analyzed · 1 run(s)")).toBeVisible();

  const jsonReportResponse = await page.request.get(`/api/investigations/${investigationId}/runs/1/report.json`);
  const markdownReportResponse = await page.request.get(`/api/investigations/${investigationId}/runs/1/report.md`);
  expect(jsonReportResponse.ok()).toBeTruthy();
  expect(markdownReportResponse.ok()).toBeTruthy();

  await mkdir("e2e-artifacts", { recursive: true });
  await writeFile("e2e-artifacts/report.json", JSON.stringify(await jsonReportResponse.json(), null, 2));
  await writeFile("e2e-artifacts/report.md", await markdownReportResponse.text());
  await page.screenshot({ path: "e2e-artifacts/investigation-history.png", fullPage: true });
});
