import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";

afterEach(() => {
  vi.restoreAllMocks();
});

test("renders guidance for all supported workflows and investigation history", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => []
    })
  );

  render(<App />);

  expect(screen.getByRole("heading", { name: "TRACE IAM Evidence" })).toBeInTheDocument();
  const navigation = screen.getByRole("navigation", { name: "Evidence scenarios" });
  expect(navigation).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Conditional Access/ })).toHaveAttribute("href", "#conditional-access");
  expect(screen.getByRole("link", { name: /Resource assignment/ })).toHaveAttribute("href", "#resource-assignment");
  expect(screen.getByRole("link", { name: /Guest \/ B2B/ })).toHaveAttribute("href", "#guest-b2b");
  expect(screen.getByRole("link", { name: /History/ })).toHaveAttribute("href", "#history");
  expect(screen.getByRole("complementary", { name: "Evidence safety guidance" })).toHaveTextContent("Use redacted evidence only");

  expect(screen.getByText(/exactly these headers/)).toBeInTheDocument();
  expect(screen.getByText(/Do not paste access tokens/)).toBeInTheDocument();
  expect(screen.getByText(/Mark assignment present only/)).toBeInTheDocument();
  expect(screen.getByText(/Do not infer redemption/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Analyze evidence" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Analyze resource assignment" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Analyze Guest B2B evidence" })).toBeInTheDocument();
  expect(await screen.findByText("No persisted investigations yet.")).toBeInTheDocument();
  expect(screen.getByText(/Run any scenario above/)).toBeInTheDocument();
});

test("renders structured API validation errors as readable operator guidance", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({
        detail: [{ loc: ["body", "csv_text"], msg: "CSV headers do not match the documented contract" }]
      })
    });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  await screen.findByText("No persisted investigations yet.");
  fireEvent.click(screen.getByRole("button", { name: "Analyze evidence" }));

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("TRACE could not complete the request.");
  expect(alert).toHaveTextContent("csv_text: CSV headers do not match the documented contract");
});
