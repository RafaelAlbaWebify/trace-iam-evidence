import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("requires a persisted investigation before scenario analysis", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
  render(<App />);

  expect(screen.getByRole("heading", { name: "TRACE IAM Evidence" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Create a persisted case" })).toBeInTheDocument();
  expect(await screen.findByText("No persisted investigations yet.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Select a Conditional Access case" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Select a resource-assignment case" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Select a Guest/B2B case" })).toBeDisabled();
});

test("creates and activates a server-generated investigation", async () => {
  const created = {
    investigation_id: "trace-a1b2c3d4e5f6",
    title: "Access investigation",
    scenario_type: "conditional_access",
    status: "draft",
    created_at: "2026-07-14T00:00:00Z",
    evidence_item_count: 0,
    analysis_run_count: 0
  };
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => created })
    .mockResolvedValueOnce({ ok: true, json: async () => [{ ...created, archived_at: null }] });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  await screen.findByText("No persisted investigations yet.");
  fireEvent.click(screen.getByRole("button", { name: "Create investigation" }));

  expect(await screen.findByText("Active investigation")).toBeInTheDocument();
  expect(screen.getByText("trace-a1b2c3d4e5f6")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Analyze evidence" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Select a resource-assignment case" })).toBeDisabled();
});

test("renders structured API validation errors as readable operator guidance", async () => {
  const created = {
    investigation_id: "trace-a1b2c3d4e5f6",
    title: "Access investigation",
    scenario_type: "conditional_access",
    status: "draft",
    created_at: "2026-07-14T00:00:00Z",
    evidence_item_count: 0,
    analysis_run_count: 0
  };
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => created })
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
