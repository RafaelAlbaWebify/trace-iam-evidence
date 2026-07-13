import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";


afterEach(() => {
  vi.restoreAllMocks();
});


test("renders Conditional Access, resource assignment, and investigation history workflows", async () => {
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
    screen.getByRole("heading", { name: "Resource assignment evidence review" })
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Redacted subject")).toHaveValue("redacted-user");
  expect(screen.getByLabelText("Resource")).toHaveValue("Finance application");
  expect(screen.getByLabelText("Expected assignment")).toHaveValue("Finance App User");
  expect(
    screen.getByRole("button", { name: "Analyze resource assignment" })
  ).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Investigation history" })
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Show archived investigations")).toBeInTheDocument();
  expect(await screen.findByText("No persisted investigations yet.")).toBeInTheDocument();

  const csvEvidence = screen.getByLabelText("Redacted Entra sign-in CSV") as HTMLTextAreaElement;
  expect(csvEvidence.value).toContain("Conditional Access Status");
});
