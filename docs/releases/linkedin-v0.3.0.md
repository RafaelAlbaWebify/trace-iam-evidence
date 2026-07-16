# LinkedIn post — TRACE v0.3.0

A troubleshooting tool is not useful just because it produces an answer.

It should also show:

- what evidence supports that answer;
- what contradicts it;
- what is still missing;
- what should be checked next;
- and what should not be changed yet.

That is the principle behind TRACE.

Three weeks ago, I shared the earlier public prototype. Since then, I have developed it into a structured, local-first IAM evidence investigation workbench.

TRACE now supports three public-safe investigation workflows:

- Conditional Access evidence review;
- resource-assignment investigation;
- Guest / B2B lifecycle investigation.

The project now includes persisted cases, evidence provenance and reliability, structured findings, immutable analysis runs, an append-only timeline, run comparison, investigation history and Markdown/JSON reports.

I also rebuilt the interface around the way support work is actually performed: case context first, evidence before conclusions, uncertainty kept visible, and safe escalation-ready outputs.

The final release was validated across Ubuntu and Windows, including backend and frontend tests, runtime lifecycle proof, portable review integrity, and Chromium browser acceptance for the supported workflows and responsive interface.

TRACE remains deliberately read-only. It does not connect to a live tenant, change access, weaken controls or automate remediation.

For me, this project is less about building another admin tool and more about demonstrating how I approach Application Support and IAM investigations: gather reliable evidence, separate facts from assumptions, document limitations, and make the next action safe and explainable.

Current repository in the first comment.

#ApplicationSupport #IAM #EntraID #TechnicalSupport #Troubleshooting #PortfolioProject

---

## First comment

GitHub repository for the current maintained TRACE project:
https://github.com/RafaelAlbaWebify/trace-iam-evidence

The earlier `trace-ops` prototype is now archived and redirects to this repository.

---

## Suggested image order

1. Desktop operational dashboard.
2. Evidence inventory and case context.
3. Structured findings showing supporting, contradicting and missing evidence.
4. Timeline or run comparison.

## Alternative text

### Image 1

TRACE desktop operational dashboard with a persistent dark navigation sidebar, case-status summary cards, filters and a searchable investigation register.

### Image 2

TRACE evidence workspace showing active-case context, evidence provenance, reliability and validation state in a dense operational layout.

### Image 3

TRACE structured findings view separating supporting evidence, contradicting evidence and missing evidence, followed by safe checks, explicit non-actions and limitations.

### Image 4

TRACE investigation timeline or run-comparison view showing immutable analysis history and changes between evidence-backed findings.