import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";

const createdCase = {
  investigation_id: "trace-a1b2c3d4e5f6",
  title: "Access investigation",
  scenario_type: "conditional_access",
  status: "draft",
  priority: "normal",
  external_reference: "INC-REDACTED-001",
  summary: "Redacted IAM access issue requiring evidence review.",
  created_at: "2026-07-14T00:00:00Z",
  updated_at: "2026-07-14T00:00:00Z",
  evidence_item_count: 0,
  analysis_run_count: 0
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("requires a persisted investigation before scenario analysis", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
  render(<App />);

  expect(screen.getByRole("heading", { name: "TRACE IAM Evidence" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Create a persisted operational case" })).toBeInTheDocument();
  expect(await screen.findByText("No persisted investigations yet.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Select a Conditional Access case" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Select a resource-assignment case" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Select a Guest/B2B case" })).toBeDisabled();
});

test("creates and activates a server-generated investigation with operational metadata", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => createdCase })
    .mockResolvedValueOnce({ ok: true, json: async () => [{ ...createdCase, archived_at: null }] });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  await screen.findByText("No persisted investigations yet.");
  fireEvent.click(screen.getByRole("button", { name: "Create investigation" }));

  const caseId = await screen.findByText("trace-a1b2c3d4e5f6");
  const activePanel = caseId.closest(".active-case");
  expect(activePanel).not.toBeNull();
  expect(within(activePanel as HTMLElement).getByText("Active investigation")).toBeInTheDocument();
  expect(within(activePanel as HTMLElement).getByText("Normal priority")).toBeInTheDocument();
  expect(within(activePanel as HTMLElement).getByText("INC-REDACTED-001")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Analyze evidence" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Select a resource-assignment case" })).toBeDisabled();

  const createRequest = JSON.parse(String(fetchMock.mock.calls[1][1]?.body));
  expect(createRequest).toMatchObject({
    title: "Access investigation",
    scenario_type: "conditional_access",
    priority: "normal",
    external_reference: "INC-REDACTED-001"
  });
});

test("edits active case metadata without replacing the case", async () => {
  const updatedCase = {
    ...createdCase,
    title: "Escalated access investigation",
    priority: "critical",
    summary: "Escalated redacted IAM review.",
    updated_at: "2026-07-14T00:05:00Z"
  };
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => createdCase })
    .mockResolvedValueOnce({ ok: true, json: async () => [{ ...createdCase, archived_at: null }] })
    .mockResolvedValueOnce({ ok: true, json: async () => updatedCase })
    .mockResolvedValueOnce({ ok: true, json: async () => [{ ...updatedCase, archived_at: null }] });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  await screen.findByText("No persisted investigations yet.");
  fireEvent.click(screen.getByRole("button", { name: "Create investigation" }));
  await screen.findByText("trace-a1b2c3d4e5f6");

  fireEvent.change(screen.getByLabelText("Case title", { selector: "#edit-title" }), { target: { value: "Escalated access investigation" } });
  fireEvent.change(screen.getByLabelText("Priority", { selector: "#edit-priority" }), { target: { value: "critical" } });
  fireEvent.change(screen.getByLabelText("Redacted case summary", { selector: "#edit-summary" }), { target: { value: "Escalated redacted IAM review." } });
  fireEvent.click(screen.getByRole("button", { name: "Save case metadata" }));

  expect(await screen.findByText("Case metadata saved without changing immutable analysis runs.")).toBeInTheDocument();
  expect(screen.getByText("Critical priority")).toBeInTheDocument();
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(5));
  const patchRequest = JSON.parse(String(fetchMock.mock.calls[3][1]?.body));
  expect(patchRequest).toMatchObject({
    title: "Escalated access investigation",
    priority: "critical",
    summary: "Escalated redacted IAM review."
  });
});

test("renders structured API validation errors as readable operator guidance", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => createdCase })
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({ detail: [{ loc: ["body", "csv_text"], msg: "CSV headers do not match the documented contract" }] })
    });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  await screen.findByText("No persisted investigations yet.");
  fireEvent.click(screen.getByRole("button", { name: "Create investigation" }));
  fireEvent.click(await screen.findByRole("button", { name: "Analyze evidence" }));

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("TRACE could not complete the request.");
  expect(alert).toHaveTextContent("csv_text: CSV headers do not match the documented contract");
});
