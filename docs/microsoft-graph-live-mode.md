# Microsoft Graph live mode

TRACE includes a deterministic offline Modern Workplace demo and an optional live, read-only Microsoft Graph acquisition path.

## App registration

Register a Microsoft Entra **public client** for local interactive use. Configure the desktop redirect URI `http://localhost`. TRACE uses MSAL delegated authentication and does not require or accept a client secret for this mode.

Configure these delegated Microsoft Graph permissions:

- `AuditLog.Read.All` — sign-in evidence;
- `Policy.Read.ConditionalAccess` — Conditional Access policy context;
- `DeviceManagementManagedDevices.Read.All` — Intune managed-device state.

Consent and the signed-in operator's Entra role still determine what Graph returns. Intune Graph endpoints also require an active Intune licence in the tenant.

## Local configuration

Set environment variables outside the repository:

```powershell
$env:TRACE_GRAPH_CLIENT_ID = "<app-registration-client-id>"
$env:TRACE_GRAPH_TENANT_ID = "<tenant-id>"
```

Do not commit either identifier with customer or production context. Do not place access tokens, client secrets, passwords, exported tenant data, or unredacted identifiers in TRACE files.

## Authentication behavior

TRACE first asks MSAL for a cached delegated token. If none is available, MSAL opens interactive browser authentication. The public-client interactive flow uses PKCE. TRACE never asks for the user's password.

## Collection boundary

The live collector performs GET requests only against:

- `/auditLogs/signIns`;
- `/identity/conditionalAccess/policies`;
- `/deviceManagement/managedDevices`.

The operator supplies filters for sign-ins and managed devices. TRACE does not perform tenant-wide discovery as part of the portfolio workflow. Graph responses are normalized into redacted evidence facts; raw access tokens and raw Graph payloads are not persisted in investigation reports.

HTTP 401, 403 and 429 are treated separately. Pagination follows `@odata.nextLink`, and throttling respects `Retry-After` within a bounded retry budget.

## Interpretation boundary

A failed Conditional Access result plus a noncompliant Intune state is **correlation**, not proof that Intune caused the access failure. TRACE requires review of the matching device identity, applied policy/grant controls and compliance evaluation before remediation. It never disables Conditional Access, changes compliance, wipes/retires devices, grants access or writes to Microsoft Graph.
