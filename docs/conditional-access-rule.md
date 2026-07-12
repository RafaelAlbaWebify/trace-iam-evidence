# Conditional Access Rule CA-001

Milestone 2 adds TRACE's first implemented analysis rule.

## Rule contract

`CA-001` matches only when all of the following are true:

- the investigation scenario is `conditional_access`;
- at least one normalized `conditional_access_failed` fact has the value `true`.

The rule does not parse logs, call Microsoft Graph, connect to a tenant, or perform remediation.

## Finding behaviour

A supported failure produces:

- a versioned rule and finding identifier;
- high severity;
- high confidence when no contradictory success fact exists;
- medium confidence when both failure and success facts exist;
- explicit missing policy-name evidence when that fact was not supplied;
- one low-risk verification check;
- an explicit non-action against disabling Conditional Access globally.

## Determinism

The application service orders rules by:

1. descending priority;
2. rule identifier;
3. rule version.

Rule evaluation order therefore does not depend on collection insertion order.

## Automatic proof

CI tests prove:

- supported failure evidence creates the expected finding;
- contradictory success evidence remains visible and reduces confidence;
- incomplete evidence does not create a finding;
- the rule cannot cross into another scenario;
- Linux and Windows checks remain green.
