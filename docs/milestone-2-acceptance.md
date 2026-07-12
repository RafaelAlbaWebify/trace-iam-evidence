# Milestone 2 Acceptance Proof

Milestone 2 completes one public-safe Conditional Access evidence workflow:

1. an operator supplies a redacted CSV matching the documented contract;
2. the API validates and normalizes row-level evidence;
3. deterministic rule `CA-001` evaluates the normalized facts;
4. TRACE returns equivalent JSON and Markdown reports;
5. the browser displays the supported finding, safe next check, and explicit non-action.

## Automated acceptance

The GitHub Actions `browser-proof` job starts the FastAPI backend and Vite frontend together, submits the public-safe sample through the real HTTP API, and verifies the rendered result.

The retained `milestone-2-browser-proof` artifact contains:

- the generated JSON report;
- the generated Markdown report;
- a full-page result screenshot;
- Playwright HTML results and failure traces when applicable;
- backend and frontend service logs.

## Safety boundary

- no Microsoft tenant or Graph connection;
- no credentials or tokens;
- no remediation;
- no silent guessing of unsupported CSV formats;
- no persistence yet;
- only redacted, public-safe evidence is accepted.

Milestone 3 may begin only after all Linux, Windows, and browser-proof jobs pass for this slice.
