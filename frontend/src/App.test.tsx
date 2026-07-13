import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";


afterEach(() => {
  vi.restoreAllMocks();
});


test("renders all supported operator workflows and investigation history", async () => {
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
    screen.getByRole("heading", { name: "Guest B2B lifecycle evidence review" })
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Redacted guest subject")).toHaveValue("redacted-guest");
  expect(screen.getByLabelText("Guest resource")).toHaveValue("Partner portal");
  expect(screen.getByLabelText("Invitation was sent")).toBeChecked();
  expect(screen.getByLabelText("Invitation was redeemed")).not.toBeChecked();
  expect(screen.getByLabelText("Tenant restriction was observed")).not.toBeChecked();
  expect(screen.getByLabelText("Resource assignment is present")).not.toBeChecked();
  expect(
    screen.getByRole("button", { name: "Analyze Guest B2B evidence" })
  ).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Investigation history" })
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Show archived investigations")).toBeInTheDocument();
  expect(await screen.findByText("No persisted investigations yet.")).toBeInTheDocument();

  const csvEvidence = screen.getByLabelText("Redacted Entra sign-in CSV") as HTMLTextAreaElement;
  expect(csvEvidence.value).toContain("Conditional Access Status");
});
