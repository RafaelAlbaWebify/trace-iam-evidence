import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";

test("operator analyzes and persists resource assignment evidence", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Resource assignment evidence review" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Resource assignment/ })).toHaveAttribute("href", "#resource-assignment");

  const responsePromise = page.waitForResponse(
    (response) => response.url().includes("analyze-resource-assignment")
  );
  await page.getByRole("button", { name: "Analyze resource assignment" }).click();
  const response = await responsePromise;
  expect(response.ok()).toBeTruthy();

  await expect(page.getByRole("heading", { name: "Analysis result" })).toBeVisible();
  const summary = page.getByRole("region", { name: "Analysis result" }).getByLabel("Analysis summary");
  await expect(summary).toContainText("1");
  await expect(summary).toContainText("RA-001");
  await expect(page.getByTestId("markdown-report")).toContainText("Do not grant broad or tenant-wide privileges");

  const historyRow = page.getByRole("button", { name: "Resource assignment review" }).locator("..");
  await expect(historyRow).toBeVisible();
  await expect(historyRow).toContainText("resource_assignment");
  await expect(historyRow).toContainText("analyzed · 1 run(s)");
  await expect(page.getByRole("link", { name: "Export JSON" })).toHaveAttribute("href", "/api/investigations/browser-ra-001/runs/1/report.json");
  await expect(page.getByRole("link", { name: "Export Markdown" })).toHaveAttribute("href", "/api/investigations/browser-ra-001/runs/1/report.md");

  const jsonReportResponse = await page.request.get("/api/investigations/browser-ra-001/runs/1/report.json");
  const markdownReportResponse = await page.request.get("/api/investigations/browser-ra-001/runs/1/report.md");
  expect(jsonReportResponse.ok()).toBeTruthy();
  expect(markdownReportResponse.ok()).toBeTruthy();

  await mkdir("e2e-artifacts", { recursive: true });
  await writeFile("e2e-artifacts/resource-assignment-report.json", JSON.stringify(await jsonReportResponse.json(), null, 2));
  await writeFile("e2e-artifacts/resource-assignment-report.md", await markdownReportResponse.text());
  await page.screenshot({ path: "e2e-artifacts/resource-assignment-history.png", fullPage: true });
});
