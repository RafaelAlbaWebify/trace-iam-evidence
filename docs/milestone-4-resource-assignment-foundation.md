# Milestone 4 — Resource assignment foundation

This slice proves that TRACE can support a second IAM investigation scenario through the existing domain and rule contracts.

## Structured evidence contract

The public-safe manual adapter accepts:

- a redacted subject;
- a specific resource;
- whether access failed;
- whether an assignment is required;
- whether the assignment is present;
- an optional expected assignment name.

It normalizes the input into ordinary `EvidenceItem` and `EvidenceFact` values. It performs no directory, application, or tenant query.

## Rule RA-001

`RA-001` matches only for a `resource_assignment` investigation when supplied evidence states:

- resource access failed;
- an assignment is required;
- the assignment is not present.

The finding recommends verifying direct and group-derived assignment to the specific resource. It explicitly records that broad or tenant-wide privileges must not be granted from this evidence.

Evidence showing that the assignment is present prevents the missing-assignment finding. Evidence evaluated under another scenario also produces no finding.

## Architecture boundary

- the adapter is isolated in `evidence/manual_resource_assignment.py`;
- the rule is isolated in `rules/resource_assignment.py`;
- both use the existing domain contracts and `Rule` interface;
- Conditional Access adapter, rule, API, persistence, and browser workflow remain unchanged.

## Automatic proof

CI must prove:

- a supported missing assignment triggers `RA-001`;
- an existing assignment does not trigger it;
- the rule does not run under Conditional Access;
- unredacted structured evidence is rejected;
- all existing Conditional Access, persistence, history, and browser tests remain green on Ubuntu and Windows.
