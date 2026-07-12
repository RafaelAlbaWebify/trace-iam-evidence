# TRACE IAM Evidence

TRACE IAM Evidence is a local-first, read-only investigation workbench for structuring redacted IAM and access-support evidence, evaluating deterministic troubleshooting rules, identifying missing evidence, and generating safe, reviewable Markdown and JSON reports.

## Status

This repository is at the architecture and foundation stage. No production tenant connection, credential storage, automated remediation, or external writes are included.

## Initial product boundary

The first vertical slice will focus on Conditional Access evidence investigations:

1. Create a local investigation.
2. Enter structured evidence or import a supported redacted Entra sign-in CSV fixture.
3. Validate and normalize the evidence.
4. Evaluate explicit deterministic rules.
5. Show supporting, contradicting, and missing evidence.
6. Generate safe next checks and explicit non-actions.
7. Export Markdown and JSON reports.

## Safety principles

- Local-first and read-only.
- Redacted or public-safe sample evidence only.
- No credentials or tenant-wide scanning.
- No automatic access, identity, policy, or licensing changes.
- No root-cause claim without sufficient supporting evidence.
- Every finding must expose its rule, evidence, limitations, and uncertainty.

## Development method

Changes will be developed through small vertical slices and verified in GitHub Actions before local manual testing. CI will cover formatting, linting, type checking, unit tests, integration tests, application builds, sample scenario verification, and generated proof artifacts.
