import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";

const createdCase = {
  investigation_id: "trace-a1b2c3d4e5f6", title: "Access investigation", scenario_type: "conditional_access", status: "draft", priority: "normal",
  external_reference: "INC-REDACTED-001", summary: "Redacted IAM access issue requiring evidence review.", created_at: "2026-07-14T00:00:00Z",
  evidence_item_count: 0, analysis_run_count: 0
};
const summaryCase = { ...createdCase, archived_at: null };
const emptyDashboard = {
  total_cases: 0, active_cases: 0, waiting_for_evidence: 0, ready_for_analysis: 0, under_review: 0,
  critical_active: 0, archived_cases: 0, filtered_case_count: 0, cases: []
};

function response(payload: unknown, ok = true, status = 200) { return { ok, status, json: async () => payload }; }
function installApi(overrides?: (url: string, init?: RequestInit) => unknown) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const overridden = overrides?.(url, init);
    if (overridden) return overridden;
    if (url.startsWith("/api/operations/dashboard")) return response(emptyDashboard);
    if (url === "/api/investigations" && init?.method === "POST") return response(createdCase);
    if (url === "/api/investigations") return response([]);
    if (url === `/api/investigations/${createdCase.investigation_id}/evidence`) return response([]);
    if (url === `/api/investigations/${createdCase.investigation_id}`) return response(createdCase);
    if (url.endsWith("/runs")) return response([]);
    return response([]);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function waitUntilReady() {
  await waitFor(() => expect(screen.getByRole("button", { name: "Create investigation" })).toBeEnabled());
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

test("requires a persisted investigation before scenario analysis", async () => {
  installApi(); render(<App />);
  expect(screen.getByRole("heading", { name: "TRACE IAM Evidence" })).toBeInTheDocument();
  expect(await screen.findByText("No persisted investigations yet.")).toBeInTheDocument();
  expect(screen.getByText("Create or open an investigation to manage its evidence inventory.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Select a Conditional Access case" })).toBeDisabled();
});

test("creates and activates a server-generated investigation with operational metadata", async () => {
  const fetchMock = installApi((url, init) => url === "/api/investigations" && !init?.method ? response([summaryCase]) : undefined);
  render(<App />); await waitUntilReady();
  fireEvent.click(screen.getByRole("button", { name: "Create investigation" }));
  const caseId = await screen.findByText(createdCase.investigation_id);
  const activePanel = caseId.closest(".active-case");
  expect(activePanel).not.toBeNull();
  expect(within(activePanel as HTMLElement).getByText("Normal priority")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Analyze evidence" })).toBeEnabled();
  expect(await screen.findByRole("button", { name: "Add evidence item" })).toBeEnabled();
  const createCall = fetchMock.mock.calls.find(([url, init]) => String(url) === "/api/investigations" && init?.method === "POST");
  expect(JSON.parse(String(createCall?.[1]?.body))).toMatchObject({ title: "Access investigation", scenario_type: "conditional_access", priority: "normal" });
});

test("adds and validates evidence in the active investigation", async () => {
  let evidence: Array<Record<string, unknown>> = [];
  let detail = { ...createdCase };
  const fetchMock = installApi((url, init) => {
    if (url === "/api/investigations" && !init?.method) return response([summaryCase]);
    if (url === `/api/investigations/${createdCase.investigation_id}/evidence` && init?.method === "POST") {
      const body = JSON.parse(String(init.body));
      const item = { ...body, captured_at: null, validated_at: null };
      evidence = [item]; detail = { ...detail, evidence_item_count: 1 }; return response(item, true, 201);
    }
    if (url === `/api/investigations/${createdCase.investigation_id}/evidence`) return response(evidence);
    if (url.endsWith("/evidence/evidence-001/validate")) {
      evidence = [{ ...evidence[0], validated_at: "2026-07-14T00:10:00Z" }]; detail = { ...detail, status: "evidence_validated" }; return response(evidence[0]);
    }
    if (url === `/api/investigations/${createdCase.investigation_id}`) return response(detail);
    return undefined;
  });
  render(<App />); await waitUntilReady();
  fireEvent.click(screen.getByRole("button", { name: "Create investigation" }));
  fireEvent.click(await screen.findByRole("button", { name: "Add evidence item" }));
  expect(await screen.findByText("evidence-001")).toBeInTheDocument();
  expect(screen.getByText("Pending validation")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Validate evidence" }));
  expect(await screen.findByText("Validated")).toBeInTheDocument();
  expect(screen.getByText("Evidence Validated")).toBeInTheDocument();
  expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/evidence/evidence-001/validate"))).toBe(true);
});

test("edits active case metadata without replacing the case", async () => {
  const updatedCase = { ...createdCase, title: "Escalated access investigation", priority: "critical", summary: "Escalated redacted IAM review." };
  installApi((url, init) => {
    if (url === "/api/investigations" && !init?.method) return response([summaryCase]);
    if (url === `/api/investigations/${createdCase.investigation_id}` && init?.method === "PATCH") return response(updatedCase);
    return undefined;
  });
  render(<App />); await waitUntilReady(); fireEvent.click(screen.getByRole("button", { name: "Create investigation" }));
  await screen.findByText(createdCase.investigation_id);
  fireEvent.change(screen.getByLabelText("Case title", { selector: "#edit-title" }), { target: { value: updatedCase.title } });
  fireEvent.change(screen.getByLabelText("Priority", { selector: "#edit-priority" }), { target: { value: "critical" } });
  fireEvent.click(screen.getByRole("button", { name: "Save case metadata" }));
  expect(await screen.findByText("Case metadata saved without changing immutable analysis runs.")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("Critical priority")).toBeInTheDocument());
});

test("renders structured API validation errors as readable operator guidance", async () => {
  installApi((url, init) => {
    if (url === "/api/investigations" && !init?.method) return response([summaryCase]);
    if (url.endsWith("analyze-conditional-access-csv") && init?.method === "POST") return response({ detail: [{ loc: ["body", "csv_text"], msg: "CSV headers do not match the documented contract" }] }, false, 422);
    return undefined;
  });
  render(<App />); await waitUntilReady(); fireEvent.click(screen.getByRole("button", { name: "Create investigation" }));
  fireEvent.click(await screen.findByRole("button", { name: "Analyze evidence" }));
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("csv_text: CSV headers do not match the documented contract");
});
