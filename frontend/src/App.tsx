import { FormEvent, useEffect, useState } from "react";

import "./App.css";

const SAMPLE_CSV = `Sign-in ID,Conditional Access Status,Failure Reason,Conditional Access Policy
signin-001,failure,Device is not compliant,Require compliant device`;

type AnalysisResponse = {
  investigation_id: string;
  run_number: number;
  finding_count: number;
  evaluated_rule_ids: string[];
  markdown_report: string;
  json_report: Record<string, unknown>;
};

type InvestigationSummary = {
  investigation_id: string;
  title: string;
  scenario_type: string;
  status: string;
  created_at: string;
  archived_at: string | null;
  analysis_run_count: number;
};

type AnalysisRun = {
  run_number: number;
  created_at: string;
  ruleset_version: string;
  finding_count: number;
};

type ApiErrorItem = {
  loc?: Array<string | number>;
  msg?: string;
};

function errorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") return fallback;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item: ApiErrorItem) => {
        const field = item.loc?.filter((part) => part !== "body").join(" → ");
        return item.msg ? `${field ? `${field}: ` : ""}${item.msg}` : "";
      })
      .filter(Boolean);
    if (messages.length > 0) return messages.join("; ");
  }
  return fallback;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new Error("TRACE could not reach the local API. Confirm that the backend is running on port 8000.");
  }

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    if (!response.ok) throw new Error(`The local API returned HTTP ${response.status} without a readable error body.`);
  }
  if (!response.ok) throw new Error(errorMessage(payload, `Request failed with HTTP ${response.status}.`));
  return payload as T;
}

export function App() {
  const [csvText, setCsvText] = useState(SAMPLE_CSV);
  const [assignmentSubject, setAssignmentSubject] = useState("redacted-user");
  const [assignmentResource, setAssignmentResource] = useState("Finance application");
  const [assignmentName, setAssignmentName] = useState("Finance App User");
  const [assignmentPresent, setAssignmentPresent] = useState(false);
  const [guestSubject, setGuestSubject] = useState("redacted-guest");
  const [guestResource, setGuestResource] = useState("Partner portal");
  const [invitationSent, setInvitationSent] = useState(true);
  const [invitationRedeemed, setInvitationRedeemed] = useState(false);
  const [tenantRestrictionObserved, setTenantRestrictionObserved] = useState(false);
  const [guestAssignmentPresent, setGuestAssignmentPresent] = useState(false);
  const [restrictionDetail, setRestrictionDetail] = useState("");
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [investigations, setInvestigations] = useState<InvestigationSummary[]>([]);
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);

  async function refreshHistory(showArchived = includeArchived) {
    const query = showArchived ? "?include_archived=true" : "";
    setInvestigations(await api<InvestigationSummary[]>(`/api/investigations${query}`));
  }

  useEffect(() => {
    refreshHistory()
      .catch((caught) => setError(caught instanceof Error ? caught.message : "History failed to load"))
      .finally(() => setHistoryLoading(false));
  }, []);

  async function completeAnalysis(payload: AnalysisResponse) {
    setResult(payload);
    setSelectedId(payload.investigation_id);
    await refreshHistory();
    setRuns(await api<AnalysisRun[]>(`/api/investigations/${payload.investigation_id}/runs`));
    document.getElementById("analysis-result")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function runAnalysis(path: string, body: Record<string, unknown>) {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      await completeAnalysis(await api<AnalysisResponse>(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  async function submitConditionalAccess(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAnalysis("/api/investigations/analyze-conditional-access-csv", {
      investigation_id: "browser-ca-001", title: "Conditional Access sign-in review",
      source: "public-safe browser sample", csv_text: csvText
    });
  }

  async function submitResourceAssignment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAnalysis("/api/investigations/analyze-resource-assignment", {
      investigation_id: "browser-ra-001", title: "Resource assignment review",
      evidence_id: "browser-ra-evidence-001", source: "public-safe browser sample",
      subject: assignmentSubject, resource: assignmentResource, access_failed: true,
      assignment_required: true, assignment_present: assignmentPresent,
      assignment_name: assignmentName || null, redacted: true
    });
  }

  async function submitGuestB2B(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAnalysis("/api/investigations/analyze-guest-b2b", {
      investigation_id: "browser-gb-001", title: "Guest B2B lifecycle review",
      evidence_id: "browser-gb-evidence-001", source: "public-safe browser sample",
      guest_subject: guestSubject, resource: guestResource, invitation_sent: invitationSent,
      invitation_redeemed: invitationRedeemed, tenant_restriction_observed: tenantRestrictionObserved,
      resource_assignment_present: guestAssignmentPresent, restriction_detail: restrictionDetail || null,
      redacted: true
    });
  }

  async function loadHistory(investigationId: string) {
    setError(""); setSelectedId(investigationId);
    try { setRuns(await api<AnalysisRun[]>(`/api/investigations/${investigationId}/runs`)); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "History failed to load"); }
  }

  async function changeArchiveState(investigationId: string, action: "archive" | "reopen") {
    setError("");
    try {
      await api(`/api/investigations/${investigationId}/${action}`, { method: "POST" });
      await refreshHistory();
      if (!includeArchived && action === "archive") { setSelectedId(""); setRuns([]); }
    } catch (caught) { setError(caught instanceof Error ? caught.message : "History update failed"); }
  }

  async function toggleArchived() {
    const next = !includeArchived; setIncludeArchived(next); setSelectedId(""); setRuns([]); setHistoryLoading(true);
    try { await refreshHistory(next); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "History failed to load"); }
    finally { setHistoryLoading(false); }
  }

  return (
    <main className="app-shell" aria-busy={loading}>
      <header className="hero">
        <p className="eyebrow">Local-first IAM evidence investigation workbench</p>
        <h1>TRACE IAM Evidence</h1>
        <p>Choose a supported evidence workflow, run deterministic rules, and retain a reviewable local history.</p>
      </header>

      <nav className="scenario-nav" aria-label="Evidence scenarios">
        <a href="#conditional-access">Conditional Access<span>CSV sign-in evidence</span></a>
        <a href="#resource-assignment">Resource assignment<span>Entitlement evidence</span></a>
        <a href="#guest-b2b">Guest / B2B<span>Lifecycle evidence</span></a>
        <a href="#history">History<span>Runs and exports</span></a>
      </nav>

      <aside className="privacy-note" aria-label="Evidence safety guidance">
        <strong>Use redacted evidence only.</strong> Replace real names, email addresses, tenant IDs, object IDs, tokens, and confidential resource names before analysis. TRACE never connects to a live tenant or changes access.
      </aside>

      <section id="conditional-access" className="workflow-card" aria-labelledby="workflow-title">
        <div className="section-heading"><span>Scenario 01</span><h2 id="workflow-title">Conditional Access evidence review</h2></div>
        <p>Paste redacted CSV evidence with exactly these headers: Sign-in ID, Conditional Access Status, Failure Reason, and Conditional Access Policy.</p>
        <form onSubmit={submitConditionalAccess}>
          <label htmlFor="csv-evidence">Redacted Entra sign-in CSV</label>
          <textarea id="csv-evidence" aria-describedby="csv-guidance" rows={8} value={csvText} onChange={(event) => setCsvText(event.target.value)} required />
          <small id="csv-guidance" className="field-guidance">Keep one sign-in record per row. Do not paste access tokens, full user identities, or unrestricted tenant exports.</small>
          <button type="submit" disabled={loading}>{loading ? "Analyzing evidence…" : "Analyze evidence"}</button>
        </form>
      </section>

      <section id="resource-assignment" className="workflow-card" aria-labelledby="assignment-workflow-title">
        <div className="section-heading"><span>Scenario 02</span><h2 id="assignment-workflow-title">Resource assignment evidence review</h2></div>
        <p>Describe one failed access attempt and the assignment expected for that specific resource.</p>
        <form onSubmit={submitResourceAssignment}>
          <label htmlFor="assignment-subject">Redacted subject</label>
          <input id="assignment-subject" aria-describedby="assignment-guidance" value={assignmentSubject} onChange={(event) => setAssignmentSubject(event.target.value)} required />
          <label htmlFor="assignment-resource">Resource</label>
          <input id="assignment-resource" value={assignmentResource} onChange={(event) => setAssignmentResource(event.target.value)} required />
          <label htmlFor="assignment-name">Expected assignment</label>
          <input id="assignment-name" value={assignmentName} onChange={(event) => setAssignmentName(event.target.value)} />
          <small id="assignment-guidance" className="field-guidance">Use placeholders for the subject and resource. Mark assignment present only when the supplied evidence supports it.</small>
          <label className="check-row"><input type="checkbox" checked={assignmentPresent} onChange={(event) => setAssignmentPresent(event.target.checked)} />Assignment is present in supplied evidence</label>
          <button type="submit" disabled={loading}>{loading ? "Analyzing assignment…" : "Analyze resource assignment"}</button>
        </form>
      </section>

      <section id="guest-b2b" className="workflow-card" aria-labelledby="guest-workflow-title">
        <div className="section-heading"><span>Scenario 03</span><h2 id="guest-workflow-title">Guest B2B lifecycle evidence review</h2></div>
        <p>Record invitation, redemption, tenant restriction, and resource assignment as separate evidence states.</p>
        <form onSubmit={submitGuestB2B}>
          <label htmlFor="guest-subject">Redacted guest subject</label>
          <input id="guest-subject" aria-describedby="guest-guidance" value={guestSubject} onChange={(event) => setGuestSubject(event.target.value)} required />
          <label htmlFor="guest-resource">Guest resource</label>
          <input id="guest-resource" value={guestResource} onChange={(event) => setGuestResource(event.target.value)} required />
          <div className="check-grid">
            <label><input type="checkbox" checked={invitationSent} onChange={(event) => setInvitationSent(event.target.checked)} />Invitation was sent</label>
            <label><input type="checkbox" checked={invitationRedeemed} onChange={(event) => setInvitationRedeemed(event.target.checked)} />Invitation was redeemed</label>
            <label><input type="checkbox" checked={tenantRestrictionObserved} onChange={(event) => setTenantRestrictionObserved(event.target.checked)} />Tenant restriction was observed</label>
            <label><input type="checkbox" checked={guestAssignmentPresent} onChange={(event) => setGuestAssignmentPresent(event.target.checked)} />Resource assignment is present</label>
          </div>
          <label htmlFor="restriction-detail">Redacted restriction detail</label>
          <input id="restriction-detail" value={restrictionDetail} onChange={(event) => setRestrictionDetail(event.target.value)} />
          <small id="guest-guidance" className="field-guidance">Do not infer redemption, assignment, or cross-tenant restrictions from one another. Record only what the supplied evidence directly supports.</small>
          <button type="submit" disabled={loading}>{loading ? "Analyzing guest evidence…" : "Analyze Guest B2B evidence"}</button>
        </form>
      </section>

      {loading && <p className="status" role="status">TRACE is evaluating the supplied redacted evidence and saving an immutable analysis run.</p>}
      {error && <p className="alert" role="alert"><strong>TRACE could not complete the request.</strong><span>{error}</span></p>}
      {result && (
        <section id="analysis-result" className="result-panel" aria-labelledby="result-title">
          <div className="section-heading"><span>Evidence outcome</span><h2 id="result-title">Analysis result</h2></div>
          <div className="result-summary" aria-label="Analysis summary">
            <article><span>Run</span><strong>{result.run_number}</strong></article>
            <article><span>Findings</span><strong>{result.finding_count}</strong></article>
            <article><span>Rules evaluated</span><strong>{result.evaluated_rule_ids.join(", ")}</strong></article>
          </div>
          <details open>
            <summary>Evidence report and safe next checks</summary>
            <pre data-testid="markdown-report">{result.markdown_report}</pre>
          </details>
        </section>
      )}

      <section id="history" className="history-panel" aria-labelledby="history-title">
        <div className="section-heading"><span>Local evidence record</span><h2 id="history-title">Investigation history</h2></div>
        <p>History is stored only in the local SQLite database. Select an investigation to inspect immutable runs and export its stored reports.</p>
        <label className="check-row"><input type="checkbox" checked={includeArchived} onChange={toggleArchived} />Show archived investigations</label>
        {historyLoading ? <p className="status" role="status">Loading local investigation history…</p> : investigations.length === 0 ? (
          <div className="empty-state"><strong>No persisted investigations yet.</strong><span>Run any scenario above to create the first immutable analysis record.</span></div>
        ) : (
          <ul className="history-list">{investigations.map((item) => (
            <li key={item.investigation_id}>
              <button type="button" onClick={() => loadHistory(item.investigation_id)}>{item.title}</button>
              <span>{item.status} · {item.analysis_run_count} run(s)</span><small>{item.scenario_type}</small>
              <button type="button" className="secondary" onClick={() => changeArchiveState(item.investigation_id, item.status === "archived" ? "reopen" : "archive")}>{item.status === "archived" ? "Reopen" : "Archive"}</button>
            </li>
          ))}</ul>
        )}
        {selectedId && (
          <section className="runs-panel" aria-labelledby="runs-title">
            <h3 id="runs-title">Analysis runs for {selectedId}</h3>
            <ul>{runs.map((run) => (
              <li key={run.run_number}><strong>Run {run.run_number}</strong> — {run.ruleset_version}, {run.finding_count} finding(s){" "}
                <a href={`/api/investigations/${selectedId}/runs/${run.run_number}/report.json`}>Export JSON</a>{" · "}
                <a href={`/api/investigations/${selectedId}/runs/${run.run_number}/report.md`}>Export Markdown</a>
              </li>
            ))}</ul>
          </section>
        )}
      </section>
    </main>
  );
}
