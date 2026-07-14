import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";

test("operator manages validated case evidence before immutable analysis", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "TRACE IAM Evidence" })).toBeVisible();
  await page.locator("#case-name").fill("Conditional Access sign-in review");
  await page.getByRole("combobox", { name: "Scenario", exact: true }).selectOption("conditional_access");
  await page.locator("#case-priority").selectOption("high");
  await page.locator("#case-reference").fill("INC-REDACTED-CA-01");
  await page.locator("#case-summary").fill("Redacted sign-in failure affecting a managed application.");
  const createResponse = page.waitForResponse((response) => response.url().endsWith("/api/investigations") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Create investigation" }).click();
  expect((await createResponse).ok()).toBeTruthy();

  const activeCase = page.locator(".active-case");
  const investigationId = (await activeCase.locator("code").textContent())?.trim();
  expect(investigationId).toMatch(/^trace-[a-f0-9]{12}$/);
  await expect(page.getByRole("heading", { name: "Active-case evidence inventory" })).toBeVisible();

  await page.locator("#evidence-id").fill("signin-log-001");
  await page.locator("#evidence-kind").selectOption("generic_text_excerpt");
  await page.locator("#evidence-source").fill("Redacted Entra sign-in log export");
  await page.locator("#evidence-reliability").selectOption("high");
  await page.locator("#evidence-excerpt").fill("Conditional Access result: failure; device compliance claim absent.");
  const addResponse = page.waitForResponse((response) => response.url().endsWith(`/api/investigations/${investigationId}/evidence`) && response.request().method() === "POST");
  await page.getByRole("button", { name: "Add evidence item" }).click();
  expect((await addResponse).ok()).toBeTruthy();
  const evidenceCard = page.getByText("signin-log-001").locator("..");
  await expect(evidenceCard).toContainText("High");
  await expect(evidenceCard).toContainText("Pending validation");

  const validateResponse = page.waitForResponse((response) => response.url().endsWith(`/evidence/signin-log-001/validate`));
  await evidenceCard.getByRole("button", { name: "Validate evidence" }).click();
  expect((await validateResponse).ok()).toBeTruthy();
  await expect(evidenceCard).toContainText("Validated");
  await expect(activeCase).toContainText("evidence_validated");

  await page.locator("#edit-priority").selectOption("critical");
  await page.locator("#edit-summary").fill("Escalated redacted sign-in failure under active review.");
  await page.getByRole("button", { name: "Save case metadata" }).click();
  await expect(activeCase.getByText("Critical priority")).toBeVisible();

  const analysisResponse = page.waitForResponse((response) => response.url().includes("analyze-conditional-access-csv"));
  await page.getByRole("button", { name: "Analyze evidence" }).click();
  expect((await analysisResponse).ok()).toBeTruthy();
  await expect(page.getByRole("heading", { name: "Analysis result" })).toBeVisible();
  await expect(page.locator(".result-summary")).toContainText("CA-001");
  await expect(page.getByTestId("markdown-report")).toContainText("Do not disable Conditional Access globally");
  await expect(evidenceCard.getByRole("button", { name: "Protected by immutable run" })).toBeDisabled();

  const historyRow = page.getByRole("button", { name: "Conditional Access sign-in review" }).locator("..");
  await expect(historyRow).toContainText("analyzed · 1 run(s)");
  await page.getByRole("button", { name: "Mark reviewed" }).click();
  await expect(historyRow).toContainText("reviewed · 1 run(s)");
  await historyRow.getByRole("button", { name: "Archive" }).click();
  await page.getByLabel("Show archived investigations").check();
  await page.getByRole("button", { name: "Reopen" }).click();
  await expect(page.getByText("reviewed · 1 run(s)")).toBeVisible();

  const jsonReportResponse = await page.request.get(`/api/investigations/${investigationId}/runs/1/report.json`);
  const markdownReportResponse = await page.request.get(`/api/investigations/${investigationId}/runs/1/report.md`);
  expect(jsonReportResponse.ok()).toBeTruthy();
  expect(markdownReportResponse.ok()).toBeTruthy();
  await mkdir("e2e-artifacts", { recursive: true });
  await writeFile("e2e-artifacts/report.json", JSON.stringify(await jsonReportResponse.json(), null, 2));
  await writeFile("e2e-artifacts/report.md", await markdownReportResponse.text());
  await page.screenshot({ path: "e2e-artifacts/evidence-workspace.png", fullPage: true });
});
