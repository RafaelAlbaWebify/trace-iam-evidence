import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";


test("operator submits redacted CSV and receives CA-001 report", async ({ page }) => {
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
  await expect(page.getByTestId("markdown-report")).toContainText("CA-001");
  await expect(page.getByTestId("markdown-report")).toContainText(
    "Do not disable Conditional Access globally"
  );

  await mkdir("e2e-artifacts", { recursive: true });
  await writeFile("e2e-artifacts/report.json", JSON.stringify(payload.json_report, null, 2));
  await writeFile("e2e-artifacts/report.md", payload.markdown_report);
  await page.screenshot({
    path: "e2e-artifacts/conditional-access-report.png",
    fullPage: true
  });
});
