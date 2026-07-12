import { render, screen } from "@testing-library/react";

import { App } from "./App";


test("renders the TRACE engineering foundation status", () => {
  render(<App />);

  expect(screen.getByRole("heading", { name: "TRACE IAM Evidence" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Engineering foundation" })).toBeInTheDocument();
});
