import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";


test("operator analyzes evidence and manages persisted investigation history", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "TRACE IAM Evidence" })).toBeVisible();

  const responsePromise = page.waitForResponse(
    (response) => response.url().includes("analyze-conditional-access-csv")
  );
  await page.getByRole("button", { name: "Analyze evidence" }).click();
  const response = await responsePromise;
  expect(response.ok()).toBeTruthy();

  const payload = await response.json();
  await expect(page.getByRole("heading", { name: "Analysis result" })).toBeVisible();
  await expect(page.getByText("Findings:").locator(".." )).toContainText("1");
  await expect(page.getByText("Run:").locator(".." )).toContainText("1");
  await expect(page.getByTestId("markdown-report")).toContainText("CA-001");
  await expect(page.getByTestId("markdown-report")).toContainText(
    "Do not disable Conditional Access globally"
  );

  await expect(
    page.getByRole("heading", { name: "Investigation history" })
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Conditional Access sign-in review" })).toBeVisible();
  await expect(page.getByText("analyzed, 1 run(s)")).toBeVisible();
  await expect(page.getByRole("link", { name: "Export JSON" })).toHaveAttribute(
    "href",
    "/api/investigations/browser-ca-001/runs/1/report.json"
  );
  await expect(page.getByRole("link", { name: "Export Markdown" })).toHaveAttribute(
    "href",
    "/api/investigations/browser-ca-001/runs/1/report.md"
  );

  await page.getByRole("button", { name: "Archive" }).click();
  await expect(page.getByText("No persisted investigations yet.")).toBeVisible();
  await page.getByLabel("Show archived investigations").check();
  await expect(page.getByText("archived, 1 run(s)")).toBeVisible();
  await page.getByRole("button", { name: "Reopen" }).click();
  await expect(page.getByText("analyzed, 1 run(s)")).toBeVisible();

  const jsonReportResponse = await page.request.get(
    "/api/investigations/browser-ca-001/runs/1/report.json"
  );
  const markdownReportResponse = await page.request.get(
    "/api/investigations/browser-ca-001/runs/1/report.md"
  );
  expect(jsonReportResponse.ok()).toBeTruthy();
  expect(markdownReportResponse.ok()).toBeTruthy();

  await mkdir("e2e-artifacts", { recursive: true });
  await writeFile(
    "e2e-artifacts/report.json",
    JSON.stringify(await jsonReportResponse.json(), null, 2)
  );
  await writeFile("e2e-artifacts/report.md", await markdownReportResponse.text());
  await page.screenshot({
    path: "e2e-artifacts/investigation-history.png",
    fullPage: true
  });
});
