import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";

afterEach(() => {
  vi.restoreAllMocks();
});

test("renders navigable supported workflows and investigation history", async () => {
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

  expect(screen.getByRole("heading", { name: "Conditional Access evidence review" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Analyze evidence" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Resource assignment evidence review" })).toBeInTheDocument();
  expect(screen.getByLabelText("Redacted subject")).toHaveValue("redacted-user");
  expect(screen.getByLabelText("Expected assignment")).toHaveValue("Finance App User");
  expect(screen.getByRole("heading", { name: "Guest B2B lifecycle evidence review" })).toBeInTheDocument();
  expect(screen.getByLabelText("Redacted guest subject")).toHaveValue("redacted-guest");
  expect(screen.getByLabelText("Invitation was sent")).toBeChecked();
  expect(screen.getByLabelText("Invitation was redeemed")).not.toBeChecked();
  expect(screen.getByRole("heading", { name: "Investigation history" })).toBeInTheDocument();
  expect(screen.getByLabelText("Show archived investigations")).toBeInTheDocument();
  expect(await screen.findByText("No persisted investigations yet.")).toBeInTheDocument();

  const csvEvidence = screen.getByLabelText("Redacted Entra sign-in CSV") as HTMLTextAreaElement;
  expect(csvEvidence.value).toContain("Conditional Access Status");
});
