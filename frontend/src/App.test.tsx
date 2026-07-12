import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { App } from "./App";


test("renders the Conditional Access operator workflow", () => {
  render(<App />);

  expect(screen.getByRole("heading", { name: "TRACE IAM Evidence" })).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Conditional Access evidence review" })
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Analyze evidence" })).toBeInTheDocument();

  const csvEvidence = screen.getByLabelText("Redacted Entra sign-in CSV") as HTMLTextAreaElement;
  expect(csvEvidence.value).toContain("Conditional Access Status");
});
