# Milestone 5 — Guest and B2B lifecycle

TRACE now supports a public-safe, structured external-user investigation workflow.

## Evidence boundaries

The adapter preserves four separate facts:

- invitation issued;
- invitation redeemed;
- cross-tenant restriction observed;
- resource assignment present.

These states are never inferred from one another. A sent invitation does not prove redemption, redemption does not prove resource assignment, and a missing assignment does not explain an observed tenant restriction.

## Rules

- `GB-001` identifies an issued invitation without supplied redemption evidence.
- `GB-002` identifies supplied cross-tenant restriction evidence and explicitly prohibits weakening or bypassing the control without validated scope and approval.
- `GB-003` identifies a redeemed guest with no supplied resource assignment only when no tenant restriction is observed.

## API and persistence

`POST /api/investigations/analyze-guest-b2b` validates redacted structured evidence, evaluates the three deterministic rules, generates JSON and Markdown reports, and stores an immutable analysis run in the existing SQLite history.

## Safety

- no tenant or Microsoft Graph connection;
- no invitation creation or guest modification;
- no automatic access assignment;
- no recommendation to weaken cross-tenant controls;
- no credentials or private evidence required.

## Automatic proof

CI proves that lifecycle states remain distinct, restriction evidence takes precedence over assignment interpretation, unredacted input is rejected, reports persist, and all existing Conditional Access, resource-assignment, persistence, frontend, and browser workflows remain green.
