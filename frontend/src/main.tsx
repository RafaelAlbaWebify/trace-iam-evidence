import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./EvidenceWorkspace.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("TRACE root element was not found");
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>
);
