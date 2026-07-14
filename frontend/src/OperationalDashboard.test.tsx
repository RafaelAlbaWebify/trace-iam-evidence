import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { OperationalDashboard } from "./OperationalDashboard";

const dashboard = {
  total_cases: 3,
  active_cases: 2,
  waiting_for_evidence: 1,
  ready_for_analysis: 0,
  under_review: 1,
  critical_active: 1,
  archived_cases: 1,
  filtered_case_count: 1,
  cases: [{
    investigation_id: "trace-critical001",
    title: "Critical finance review",
    scenario_type: "conditional_access",
    status: "reviewed",
    priority: "critical",
    external_reference: "INC-CRIT-7",
    summary: "Redacted critical access review.",
    created_at: "2026-07-14T08:00:00Z",
    archived_at: null,
    last_activity_at: "2026-07-14T10:00:00Z",
    analysis_run_count: 2,
  }],
};

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

test("shows operational workload, applies filters, and opens by generated ID", async () => {
  const fetchMock = vi.fn(async () => ({ ok: true, status: 200, json: async () => dashboard }));
  vi.stubGlobal("fetch", fetchMock);
  const onOpenCase = vi.fn(async () => undefined);
  render(<OperationalDashboard onOpenCase={onOpenCase} onError={vi.fn()} />);

  expect(await screen.findByRole("heading", { name: "Case search and workload dashboard" })).toBeInTheDocument();
  expect(await screen.findByText("Critical finance review")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Search cases"), { target: { value: "INC-CRIT-7" } });
  fireEvent.change(screen.getByLabelText("Priority"), { target: { value: "critical" } });
  fireEvent.click(screen.getByRole("button", { name: "Apply operational filters" }));
  await waitFor(() => {
    const latestCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
    expect(String(latestCall?.[0])).toContain("query=INC-CRIT-7");
  });
  const latestCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
  expect(String(latestCall?.[0])).toContain("priority=critical");

  fireEvent.click(screen.getByRole("button", { name: "Open investigation" }));
  expect(onOpenCase).toHaveBeenCalledWith("trace-critical001");
});
