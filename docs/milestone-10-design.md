# Milestone 10 — Structured findings workspace

TRACE now presents deterministic analysis output as an operator-facing findings workspace rather than only a raw Markdown report.

## Operator model

Each finding is displayed independently with:

- severity and confidence;
- rule ID and rule version;
- supporting evidence facts;
- contradicting evidence facts;
- missing evidence facts;
- safe next checks and their risk classification;
- explicit non-actions under **Do not change yet**;
- analysis limitations.

Operators can filter findings by severity and confidence without altering the immutable report payload.

## Safety and auditability

- Structured cards are rendered from the backend-generated report; the frontend does not infer root cause.
- Unknown or malformed report entries are ignored rather than guessed into a finding.
- Raw Markdown and JSON remain visible for inspection.
- Direct export links always target the immutable persisted run, not the filtered browser view.
- Existing analysis-result and raw-report selectors remain compatible with automated browser proof.

## Scope boundary

This milestone does not add AI-generated conclusions, remediation, policy changes, or external Microsoft Graph connectivity. Findings remain deterministic outputs of versioned TRACE rules applied to redacted evidence.
