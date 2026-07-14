import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { RunComparisonWorkspace } from "./RunComparisonWorkspace";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

test("compares two immutable runs and exposes an export", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/runs")) return new Response(JSON.stringify([
      { run_number: 1, created_at: "2026-07-14T10:00:00", ruleset_version: "CA-001@1.0.0", finding_count: 1 },
      { run_number: 2, created_at: "2026-07-14T10:05:00", ruleset_version: "CA-001@1.1.0", finding_count: 2 },
    ]), { status: 200, headers: { "Content-Type": "application/json" } });
    return new Response(JSON.stringify({
      base_run_number: 1, target_run_number: 2,
      base_ruleset_version: "CA-001@1.0.0", target_ruleset_version: "CA-001@1.1.0", ruleset_changed: true,
      added_findings: [{ title: "New assignment finding" }], resolved_findings: [],
      changed_findings: [{ identity: "CA-001", before: { confidence: "medium" }, after: { confidence: "high" }, changed_fields: ["confidence"] }],
      added_evidence_ids: ["evidence-002"], removed_evidence_ids: ["evidence-001"], unchanged_finding_count: 0,
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  });
  render(<RunComparisonWorkspace activeCase={{ investigation_id: "trace-test", analysis_run_count: 2 }} unavailable={false} onError={vi.fn()} />);
  await screen.findByRole("button", { name: "Compare immutable runs" });
  fireEvent.click(screen.getByRole("button", { name: "Compare immutable runs" }));
  const result = await screen.findByRole("region", { name: "Run comparison result" });
  expect(within(result).getByText("New assignment finding")).toBeInTheDocument();
  expect(within(result).getByText("confidence")).toBeInTheDocument();
  expect(within(result).getByText(/evidence-002/)).toBeInTheDocument();
  expect(within(result).getByText(/CA-001@1.0.0/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Export comparison JSON" })).toHaveAttribute("download", "trace-trace-test-runs-1-2.json");
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/investigations/trace-test/compare-runs?base_run=1&target_run=2"));
});
