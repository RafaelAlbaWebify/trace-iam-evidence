import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";


test("operator analyzes and persists resource assignment evidence", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Resource assignment evidence review" })
  ).toBeVisible();

  const responsePromise = page.waitForResponse(
    (response) => response.url().includes("analyze-resource-assignment")
  );
  await page.getByRole("button", { name: "Analyze resource assignment" }).click();
  const response = await responsePromise;
  expect(response.ok()).toBeTruthy();

  await expect(page.getByRole("heading", { name: "Analysis result" })).toBeVisible();
  await expect(page.getByText("Findings:").locator("..")).toContainText("1");
  await expect(page.getByTestId("markdown-report")).toContainText("RA-001");
  await expect(page.getByTestId("markdown-report")).toContainText(
    "Do not grant broad or tenant-wide privileges"
  );

  await expect(page.getByRole("button", { name: "Resource assignment review" })).toBeVisible();
  await expect(page.getByText("resource_assignment")).toBeVisible();
  await expect(page.getByText("analyzed, 1 run(s)")).toBeVisible();
  await expect(page.getByRole("link", { name: "Export JSON" })).toHaveAttribute(
    "href",
    "/api/investigations/browser-ra-001/runs/1/report.json"
  );
  await expect(page.getByRole("link", { name: "Export Markdown" })).toHaveAttribute(
    "href",
    "/api/investigations/browser-ra-001/runs/1/report.md"
  );

  const jsonReportResponse = await page.request.get(
    "/api/investigations/browser-ra-001/runs/1/report.json"
  );
  const markdownReportResponse = await page.request.get(
    "/api/investigations/browser-ra-001/runs/1/report.md"
  );
  expect(jsonReportResponse.ok()).toBeTruthy();
  expect(markdownReportResponse.ok()).toBeTruthy();

  await mkdir("e2e-artifacts", { recursive: true });
  await writeFile(
    "e2e-artifacts/resource-assignment-report.json",
    JSON.stringify(await jsonReportResponse.json(), null, 2)
  );
  await writeFile(
    "e2e-artifacts/resource-assignment-report.md",
    await markdownReportResponse.text()
  );
  await page.screenshot({
    path: "e2e-artifacts/resource-assignment-history.png",
    fullPage: true
  });
});
