import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./EvidenceWorkspace.css";
import "./CaseEvidenceRefurbishment.css";
import "./AnalysisFindingsPresentation.css";
import "./TimelineComparisonHistoryPresentation.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("TRACE root element was not found");
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
