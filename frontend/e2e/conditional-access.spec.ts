import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";

test("operator manages evidence, findings, chronology, and immutable run comparison", async ({ page }) => {
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
  const evidenceWorkspace = page.getByRole("region", { name: "Active-case evidence inventory" });
  const timelineWorkspace = page.getByRole("region", { name: "Investigation timeline" });
  const comparisonWorkspace = page.getByRole("region", { name: "Analysis run comparison" });
  const investigationId = (await activeCase.locator("code").textContent())?.trim();
  expect(investigationId).toMatch(/^trace-[a-f0-9]{12}$/);
  await expect(evidenceWorkspace).toBeVisible();
  await expect(timelineWorkspace).toBeVisible();
  await expect(comparisonWorkspace).toBeVisible();
  await expect(timelineWorkspace.getByText("Investigation created.")).toBeVisible();

  await page.locator("#evidence-id").fill("signin-log-001");
  await page.locator("#evidence-kind").selectOption("generic_text_excerpt");
  await page.locator("#evidence-source").fill("Redacted Entra sign-in log export");
  await page.locator("#evidence-reliability").selectOption("high");
  await page.locator("#evidence-excerpt").fill("Conditional Access result: failure; device compliance claim absent.");
  const addResponse = page.waitForResponse((response) => response.url().endsWith(`/api/investigations/${investigationId}/evidence`) && response.request().method() === "POST");
  await page.getByRole("button", { name: "Add evidence item" }).click();
  expect((await addResponse).ok()).toBeTruthy();
  const evidenceCard = evidenceWorkspace.getByText("signin-log-001", { exact: true }).locator("xpath=ancestor::li");
  await expect(evidenceCard).toContainText("Pending validation");

  const validateResponse = page.waitForResponse((response) => response.url().endsWith(`/evidence/signin-log-001/validate`));
  await evidenceCard.getByRole("button", { name: "Validate evidence" }).click();
  expect((await validateResponse).ok()).toBeTruthy();
  await expect(activeCase).toContainText("evidence_validated");

  await page.locator("#timeline-note").fill("Redacted escalation context confirmed with the application owner.");
  const noteResponse = page.waitForResponse((response) => response.url().endsWith(`/timeline/notes`) && response.request().method() === "POST");
  await page.getByRole("button", { name: "Add timeline note" }).click();
  expect((await noteResponse).ok()).toBeTruthy();

  const firstAnalysis = page.waitForResponse((response) => response.url().includes("analyze-conditional-access-csv"));
  await page.getByRole("button", { name: "Analyze evidence" }).click();
  expect((await firstAnalysis).ok()).toBeTruthy();
  await expect(page.getByRole("heading", { name: "Analysis result" })).toBeVisible();
  await expect(timelineWorkspace.getByText("Analysis run 1 completed.")).toBeVisible();

  const secondAnalysis = page.waitForResponse((response) => response.url().includes("analyze-conditional-access-csv"));
  await page.getByRole("button", { name: "Analyze evidence" }).click();
  expect((await secondAnalysis).ok()).toBeTruthy();
  await expect(timelineWorkspace.getByText("Analysis run 2 completed.")).toBeVisible();
  await expect(comparisonWorkspace.getByRole("button", { name: "Compare immutable runs" })).toBeEnabled();
  const comparisonResponse = page.waitForResponse((response) => response.url().includes("compare-runs?base_run=1&target_run=2"));
  await comparisonWorkspace.getByRole("button", { name: "Compare immutable runs" }).click();
  expect((await comparisonResponse).ok()).toBeTruthy();
  const comparisonResult = comparisonWorkspace.getByRole("region", { name: "Run comparison result" });
  await expect(comparisonResult).toContainText("Unchanged findings");
  await expect(comparisonResult).toContainText("CA-001@1.0.0");
  await expect(comparisonWorkspace.getByRole("link", { name: "Export comparison JSON" })).toHaveAttribute("download", new RegExp(`trace-${investigationId}-runs-1-2\\.json`));

  const historyRow = page.getByRole("button", { name: "Conditional Access sign-in review" }).locator("..");
  await expect(historyRow).toContainText("analyzed · 2 run(s)");
  await page.getByRole("button", { name: "Mark reviewed" }).click();
  await expect(historyRow).toContainText("reviewed · 2 run(s)");
  await historyRow.getByRole("button", { name: "Archive" }).click();
  await page.getByLabel("Show archived investigations").check();
  await page.getByRole("button", { name: "Reopen" }).click();
  await expect(page.getByText("reviewed · 2 run(s)")).toBeVisible();

  const comparisonApiResponse = await page.request.get(`/api/investigations/${investigationId}/compare-runs?base_run=1&target_run=2`);
  expect(comparisonApiResponse.ok()).toBeTruthy();
  const comparison = await comparisonApiResponse.json();
  expect(comparison.base_run_number).toBe(1);
  expect(comparison.target_run_number).toBe(2);
  expect(comparison.unchanged_finding_count).toBeGreaterThanOrEqual(1);

  const timelineResponse = await page.request.get(`/api/investigations/${investigationId}/timeline`);
  const timeline = await timelineResponse.json();
  expect(timeline.filter((event: { event_type: string }) => event.event_type === "analysis_completed")).toHaveLength(2);

  const jsonReportResponse = await page.request.get(`/api/investigations/${investigationId}/runs/1/report.json`);
  const jsonReport = await jsonReportResponse.json();
  expect(jsonReport.evidence_snapshot).toHaveLength(1);
  await mkdir("e2e-artifacts", { recursive: true });
  await writeFile("e2e-artifacts/report.json", JSON.stringify(jsonReport, null, 2));
  await writeFile("e2e-artifacts/timeline.json", JSON.stringify(timeline, null, 2));
  await writeFile("e2e-artifacts/comparison.json", JSON.stringify(comparison, null, 2));
  await page.screenshot({ path: "e2e-artifacts/run-comparison.png", fullPage: true });
});
