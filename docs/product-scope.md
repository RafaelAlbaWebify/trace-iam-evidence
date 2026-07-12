# Product Scope

## Purpose

TRACE IAM Evidence helps IAM and access-support operators turn incomplete, redacted evidence into a defensible troubleshooting record.

It structures evidence, evaluates explicit deterministic rules, identifies supported and unsupported conclusions, recommends safe verification steps, and generates reviewable investigation reports.

## Target users

- IAM support analysts
- Identity operations analysts
- Microsoft 365 support engineers
- Service desk escalation engineers
- Junior IAM engineers practising evidence-based troubleshooting

## Core workflow

1. Create an investigation.
2. Select a supported scenario family.
3. Enter or import redacted evidence.
4. Validate evidence structure.
5. Review normalized evidence.
6. Run deterministic evaluation.
7. Review findings, contradictions, and missing evidence.
8. Review safe next checks and explicit non-actions.
9. Export Markdown and JSON reports.
10. Reopen the investigation from local history.

## First vertical slice

Conditional Access evidence investigation:

- structured manual sign-in evidence;
- one documented redacted Entra sign-in CSV format;
- evidence validation and normalization;
- deterministic Conditional Access rules;
- explicit confidence reasoning;
- supporting, contradicting, and missing evidence;
- Markdown and JSON report export;
- local investigation history.

## Non-goals for the first release

- Microsoft Graph or live tenant connection
- credential storage
- automated remediation
- access or policy changes
- generic infrastructure diagnostics
- DNS or endpoint readiness checks
- ticket-system integration
- multi-user accounts
- cloud deployment
- compliance certification claims
- AI-generated root-cause conclusions

## Product safety boundary

TRACE must remain read-only by default. It must not recommend broad policy weakening, privilege escalation, license churn, guest conversion, or other production changes when evidence is incomplete.

Every finding must expose:

- rule identifier and version;
- supporting evidence;
- contradicting evidence;
- missing evidence;
- confidence and its basis;
- limitations;
- safe next checks;
- actions not justified by the available evidence.
