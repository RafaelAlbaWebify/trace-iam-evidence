# Known limitations

TRACE IAM Evidence is a portfolio-grade local investigation workbench, not a production identity-management platform.

- It does not connect to Microsoft Graph, Entra ID, applications, or external tenants.
- It accepts only redacted or public-safe structured evidence and the documented sample CSV shape.
- It does not prove root cause; findings are deterministic interpretations of supplied evidence with explicit limitations.
- It does not create users, guests, invitations, assignments, policies, licences, or access changes.
- It does not disable, weaken, or bypass Conditional Access or cross-tenant controls.
- It does not ingest arbitrary Microsoft export formats or silently infer unknown columns.
- SQLite is intended for local single-operator use; concurrent multi-user access is outside the release scope.
- Evidence retention is limited to `full_redacted` and `metadata_only`; automatic expiry and secure deletion are not implemented.
- Authentication, authorization, encryption-at-rest management, installer packaging, and hosted deployment are outside this release.
- Browser proof currently uses Chromium in GitHub Actions; other browser engines are not release gates.
- The Windows release-candidate gate is automated in GitHub Actions. A separate signed desktop installer or physical-device certification is not claimed.
