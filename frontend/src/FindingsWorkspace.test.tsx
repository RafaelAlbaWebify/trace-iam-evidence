import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";

import { FindingsWorkspace } from "./FindingsWorkspace";

const result = {
  run_number: 2,
  finding_count: 2,
  evaluated_rule_ids: ["CA-001", "CA-002"],
  markdown_report: "# TRACE report\n\nDo not disable Conditional Access globally.",
  json_report: {
    findings: [
      {
        finding_id: "finding-high",
        rule_id: "CA-001",
        rule_version: "1.0.0",
        title: "Conditional Access blocked the sign-in",
        severity: "high",
        confidence: "high",
        supporting_fact_types: ["conditional_access_failed"],
        contradicting_fact_types: [],
        missing_fact_types: ["device_compliance_state"],
        limitations: ["The evidence is a redacted export."],
        recommended_checks: [{ description: "Review the named policy", purpose: "Confirm the exact grant control.", risk: "low" }],
        non_actions: [{ description: "Do not disable Conditional Access globally", reason: "That would broaden access beyond the affected sign-in." }],
      },
      {
        finding_id: "finding-medium",
        rule_id: "CA-002",
        rule_version: "1.0.0",
        title: "Additional evidence is required",
        severity: "medium",
        confidence: "medium",
        supporting_fact_types: [],
        contradicting_fact_types: [],
        missing_fact_types: ["policy_result"],
        limitations: [],
        recommended_checks: [],
        non_actions: [],
      },
    ],
  },
} as const;

afterEach(cleanup);

test("presents structured evidence, safe checks, non-actions and raw reports", () => {
  render(<FindingsWorkspace result={result} />);
  expect(screen.getByRole("heading", { name: "Structured findings workspace" })).toBeInTheDocument();
  const highCard = screen.getByRole("heading", { name: "Conditional Access blocked the sign-in" }).closest("article");
  expect(highCard).not.toBeNull();
  expect(within(highCard as HTMLElement).getByText("high severity")).toBeInTheDocument();
  expect(within(highCard as HTMLElement).getByText("conditional_access_failed")).toBeInTheDocument();
  expect(within(highCard as HTMLElement).getByText("device_compliance_state")).toBeInTheDocument();
  expect(within(highCard as HTMLElement).getByText("Review the named policy")).toBeInTheDocument();
  expect(within(highCard as HTMLElement).getByText("Do not disable Conditional Access globally")).toBeInTheDocument();
  expect(screen.getByTestId("markdown-report")).toHaveTextContent("TRACE report");
  expect(screen.getByTestId("json-report")).toHaveTextContent("finding-high");
});

test("filters findings without altering the raw report", () => {
  render(<FindingsWorkspace result={result} />);
  fireEvent.change(screen.getByLabelText("Severity"), { target: { value: "medium" } });
  expect(screen.queryByRole("heading", { name: "Conditional Access blocked the sign-in" })).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Additional evidence is required" })).toBeInTheDocument();
  expect(screen.getByText("1 of 2 finding(s)")).toBeInTheDocument();
  expect(screen.getByTestId("json-report")).toHaveTextContent("finding-high");
});
