# Structured Conditional Access Workflow

This Milestone 2 slice connects validated redacted manual evidence to deterministic analysis and reports.

## Endpoint

`POST /api/investigations/analyze-conditional-access`

The request accepts:

- investigation and evidence identifiers;
- a human-readable title and evidence source;
- explicit failed and successful Conditional Access outcomes;
- an optional policy name;
- a required redacted-evidence flag.

## Processing path

1. Pydantic validates the HTTP request.
2. The manual evidence adapter creates one `EvidenceItem`.
3. The adapter normalizes explicit fields into `EvidenceFact` values.
4. `CA-001` evaluates the normalized facts.
5. TRACE generates equivalent JSON and Markdown report representations.
6. The response returns the evaluated rule identifiers, finding count, and both reports.

## Safety boundary

- unredacted manual evidence is rejected;
- no free-text interpretation occurs;
- no tenant, Graph, credential, or external-system access occurs;
- no remediation occurs;
- reports retain explicit missing evidence, contradictions, safe checks, and non-actions.

## Not included yet

- Entra sign-in CSV validation and normalization;
- browser operator workflow;
- persistence and history;
- report file download;
- browser screenshots and end-to-end proof artifacts.
