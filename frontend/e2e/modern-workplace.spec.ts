import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";

test("reviewer loads Graph Entra Conditional Access and Intune investigation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Identity · Modern Workplace · Microsoft Graph")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Investigate a Modern Workplace access failure" })).toBeVisible();
  const demoResponse = page.waitForResponse((response) => response.url().endsWith("/api/modern-workplace/demo") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Load Graph + Intune demo" }).click();
  expect((await demoResponse).ok()).toBeTruthy();
  const active = page.locator(".active-case");
  await expect(active).toContainText("Managed device blocked by Conditional Access");
  await expect(active).toContainText("INC-GRAPH-DEMO-001");
  const findings = page.locator("#analysis-result");
  await expect(findings.getByRole("heading", { name: "Analysis result" })).toBeVisible();
  const correlationHeading = findings.getByRole("heading", { name: "Conditional Access failure correlates with noncompliant device evidence" });
  await expect(correlationHeading).toBeVisible();
  const correlation = correlationHeading.locator("xpath=ancestor::article[contains(@class, \"finding-card\")]");
  await expect(correlation.getByText("Correlation does not prove that Intune compliance caused the access failure.", { exact: true })).toBeVisible();
  await expect(correlation.getByText("Do not disable Conditional Access or mark the device compliant manually.", { exact: true })).toBeVisible();
  const evidenceResponse = await page.request.get("/api/investigations/trace-modern-workplace-demo/evidence");
  expect(evidenceResponse.ok()).toBeTruthy();
  const evidence = await evidenceResponse.json();
  expect(evidence.map((item: { source: string }) => item.source).join(" ")).toContain("/auditLogs/signIns");
  expect(evidence.map((item: { source: string }) => item.source).join(" ")).toContain("/deviceManagement/managedDevices");
  await mkdir("e2e-artifacts", { recursive: true });
  await page.screenshot({ path: "e2e-artifacts/modern-workplace-graph.png", fullPage: true });
});
