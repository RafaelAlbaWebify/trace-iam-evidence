import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";

test("operator creates and analyzes a persisted resource-assignment case", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Create investigation" })).toBeEnabled();

  await page.getByLabel("Case title").fill("Resource assignment review");
  await page.getByRole("combobox", { name: "Scenario", exact: true }).selectOption("resource_assignment");
  const createResponsePromise = page.waitForResponse((response) => response.url().endsWith("/api/investigations") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Create investigation" }).click();
  expect((await createResponsePromise).ok()).toBeTruthy();

  const investigationId = (await page.locator(".active-case code").textContent())?.trim();
  expect(investigationId).toMatch(/^trace-[a-f0-9]{12}$/);
  await expect(page.getByRole("button", { name: "Analyze resource assignment" })).toBeEnabled();

  const responsePromise = page.waitForResponse((response) => response.url().includes("analyze-resource-assignment"));
  await page.getByRole("button", { name: "Analyze resource assignment" }).click();
  expect((await responsePromise).ok()).toBeTruthy();

  await expect(page.getByRole("heading", { name: "Analysis result" })).toBeVisible();
  const summary = page.locator(".result-summary");
  await expect(summary).toContainText("RA-001");
  await expect(page.getByTestId("markdown-report")).toContainText("Do not grant broad or tenant-wide privileges");

  const historyRow = page.getByRole("button", { name: "Resource assignment review" }).locator("..");
  await expect(historyRow).toContainText("resource_assignment");
  await expect(historyRow).toContainText("analyzed · 1 run(s)");
  await expect(page.getByRole("link", { name: "Export JSON" })).toHaveAttribute("href", `/api/investigations/${investigationId}/runs/1/report.json`);

  const jsonReportResponse = await page.request.get(`/api/investigations/${investigationId}/runs/1/report.json`);
  const markdownReportResponse = await page.request.get(`/api/investigations/${investigationId}/runs/1/report.md`);
  expect(jsonReportResponse.ok()).toBeTruthy();
  expect(markdownReportResponse.ok()).toBeTruthy();

  await mkdir("e2e-artifacts", { recursive: true });
  await writeFile("e2e-artifacts/resource-assignment-report.json", JSON.stringify(await jsonReportResponse.json(), null, 2));
  await writeFile("e2e-artifacts/resource-assignment-report.md", await markdownReportResponse.text());
  await page.screenshot({ path: "e2e-artifacts/resource-assignment-history.png", fullPage: true });
});
