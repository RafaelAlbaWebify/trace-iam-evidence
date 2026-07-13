import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";


test("operator analyzes and persists Guest B2B lifecycle evidence", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Guest B2B lifecycle evidence review" })
  ).toBeVisible();

  await expect(page.getByLabel("Invitation was sent")).toBeChecked();
  await expect(page.getByLabel("Invitation was redeemed")).not.toBeChecked();
  await expect(page.getByLabel("Tenant restriction was observed")).not.toBeChecked();
  await expect(page.getByLabel("Resource assignment is present")).not.toBeChecked();

  const responsePromise = page.waitForResponse(
    (response) => response.url().includes("analyze-guest-b2b")
  );
  await page.getByRole("button", { name: "Analyze Guest B2B evidence" }).click();
  const response = await responsePromise;
  expect(response.ok()).toBeTruthy();

  await expect(page.getByRole("heading", { name: "Analysis result" })).toBeVisible();
  await expect(page.getByText("Findings:").locator("..")).toContainText("1");
  await expect(page.getByTestId("markdown-report")).toContainText("GB-001");
  await expect(page.getByTestId("markdown-report")).toContainText(
    "Do not recreate the guest or issue repeated invitations"
  );

  const historyRow = page
    .getByRole("button", { name: "Guest B2B lifecycle review" })
    .locator("..");
  await expect(historyRow).toContainText("guest_b2b");
  await expect(historyRow).toContainText("analyzed, 1 run(s)");
  await expect(page.getByText("GB-001@1.0.0+GB-002@1.0.0+GB-003@1.0.0")).toBeVisible();
  await expect(page.getByRole("link", { name: "Export JSON" })).toHaveAttribute(
    "href",
    "/api/investigations/browser-gb-001/runs/1/report.json"
  );
  await expect(page.getByRole("link", { name: "Export Markdown" })).toHaveAttribute(
    "href",
    "/api/investigations/browser-gb-001/runs/1/report.md"
  );

  const jsonReportResponse = await page.request.get(
    "/api/investigations/browser-gb-001/runs/1/report.json"
  );
  const markdownReportResponse = await page.request.get(
    "/api/investigations/browser-gb-001/runs/1/report.md"
  );
  expect(jsonReportResponse.ok()).toBeTruthy();
  expect(markdownReportResponse.ok()).toBeTruthy();

  await mkdir("e2e-artifacts", { recursive: true });
  await writeFile(
    "e2e-artifacts/guest-b2b-report.json",
    JSON.stringify(await jsonReportResponse.json(), null, 2)
  );
  await writeFile("e2e-artifacts/guest-b2b-report.md", await markdownReportResponse.text());
  await page.screenshot({
    path: "e2e-artifacts/guest-b2b-history.png",
    fullPage: true
  });
});
