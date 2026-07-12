import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";


afterEach(() => {
  vi.restoreAllMocks();
});


test("renders the Conditional Access workflow and investigation history", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => []
    })
  );

  render(<App />);

  expect(screen.getByRole("heading", { name: "TRACE IAM Evidence" })).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Conditional Access evidence review" })
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Analyze evidence" })).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Investigation history" })
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Show archived investigations")).toBeInTheDocument();
  expect(await screen.findByText("No persisted investigations yet.")).toBeInTheDocument();

  const csvEvidence = screen.getByLabelText("Redacted Entra sign-in CSV") as HTMLTextAreaElement;
  expect(csvEvidence.value).toContain("Conditional Access Status");
});
