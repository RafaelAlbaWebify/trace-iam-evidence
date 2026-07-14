import { FormEvent, useEffect, useState } from "react";

import "./App.css";
import { EvidenceWorkspace } from "./EvidenceWorkspace";

const SAMPLE_CSV = `Sign-in ID,Conditional Access Status,Failure Reason,Conditional Access Policy
signin-001,failure,Device is not compliant,Require compliant device`;

type ScenarioType = "conditional_access" | "resource_assignment" | "guest_b2b";
type CasePriority = "low" | "normal" | "high" | "critical";
type InvestigationStatus = "draft" | "evidence_validated" | "analyzed" | "reviewed" | "exported" | "archived";
type AnalysisResponse = { investigation_id: string; run_number: number; finding_count: number; evaluated_rule_ids: string[]; markdown_report: string; json_report: Record<string, unknown> };
type InvestigationSummary = { investigation_id: string; title: string; scenario_type: ScenarioType; status: InvestigationStatus; priority: CasePriority; external_reference: string | null; summary: string | null; created_at: string; archived_at: string | null; analysis_run_count: number };
type InvestigationDetail = { investigation_id: string; title: string; scenario_type: ScenarioType; status: InvestigationStatus; priority: CasePriority; external_reference: string | null; summary: string | null; created_at: string; evidence_item_count: number; analysis_run_count: number };
type AnalysisRun = { run_number: number; created_at: string; ruleset_version: string; finding_count: number };
type ApiErrorItem = { loc?: Array<string | number>; msg?: string };

function errorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") return fallback;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item: ApiErrorItem) => {
      const field = item.loc?.filter((part) => part !== "body").join(" → ");
      return item.msg ? `${field ? `${field}: ` : ""}${item.msg}` : "";
    }).filter(Boolean);
    if (messages.length) return messages.join("; ");
  }
  return fallback;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try { response = await fetch(path, init); }
  catch { throw new Error("TRACE could not reach the local API. Confirm that the backend is running on port 8000."); }
  let payload: unknown = null;
  try { payload = await response.json(); }
  catch { if (!response.ok) throw new Error(`The local API returned HTTP ${response.status} without a readable error body.`); }
  if (!response.ok) throw new Error(errorMessage(payload, `Request failed with HTTP ${response.status}.`));
  return payload as T;
}

const priorityLabel = (priority: CasePriority) => priority.charAt(0).toUpperCase() + priority.slice(1);
function nextLifecycleAction(status: InvestigationStatus): { status: InvestigationStatus; label: string } | null {
  if (status === "analyzed") return { status: "reviewed", label: "Mark reviewed" };
  if (status === "reviewed") return { status: "exported", label: "Mark exported" };
  return null;
}

export function App() {
  const [caseTitle, setCaseTitle] = useState("Access investigation");
  const [caseScenario, setCaseScenario] = useState<ScenarioType>("conditional_access");
  const [casePriority, setCasePriority] = useState<CasePriority>("normal");
  const [caseReference, setCaseReference] = useState("INC-REDACTED-001");
  const [caseSummary, setCaseSummary] = useState("Redacted IAM access issue requiring evidence review.");
  const [activeCase, setActiveCase] = useState<InvestigationDetail | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editPriority, setEditPriority] = useState<CasePriority>("normal");
  const [editReference, setEditReference] = useState("");
  const [editSummary, setEditSummary] = useState("");
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
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);

  function loadEditor(detail: InvestigationDetail) {
    setEditTitle(detail.title); setEditPriority(detail.priority); setEditReference(detail.external_reference ?? ""); setEditSummary(detail.summary ?? "");
  }
  async function refreshHistory(showArchived = includeArchived) {
    setInvestigations(await api<InvestigationSummary[]>(`/api/investigations${showArchived ? "?include_archived=true" : ""}`));
  }
  async function reloadActiveCase() {
    if (!activeCase) return;
    const detail = await api<InvestigationDetail>(`/api/investigations/${activeCase.investigation_id}`);
    setActiveCase(detail); loadEditor(detail); await refreshHistory();
  }

  useEffect(() => { refreshHistory().catch((caught) => setError(caught instanceof Error ? caught.message : "History failed to load")).finally(() => setHistoryLoading(false)); }, []);

  async function createCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setError(""); setNotice(""); setResult(null);
    try {
      const created = await api<InvestigationDetail>("/api/investigations", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: caseTitle, scenario_type: caseScenario, priority: casePriority, external_reference: caseReference || null, summary: caseSummary || null }) });
      setActiveCase(created); loadEditor(created); setSelectedId(created.investigation_id); setRuns([]); setNotice(`Investigation ${created.investigation_id} created and selected.`); await refreshHistory();
      document.getElementById("active-case-control")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Case creation failed"); }
    finally { setLoading(false); }
  }

  async function activateCase(item: InvestigationSummary) {
    setError(""); setNotice("");
    try {
      const detail = await api<InvestigationDetail>(`/api/investigations/${item.investigation_id}`);
      setActiveCase(detail); loadEditor(detail); setSelectedId(detail.investigation_id); setRuns(await api<AnalysisRun[]>(`/api/investigations/${detail.investigation_id}/runs`)); setNotice(`Investigation ${detail.investigation_id} is now active.`);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Investigation failed to load"); }
  }

  async function updateCaseMetadata(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!activeCase) return; setLoading(true); setError(""); setNotice("");
    try {
      const updated = await api<InvestigationDetail>(`/api/investigations/${activeCase.investigation_id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: editTitle, priority: editPriority, external_reference: editReference || null, summary: editSummary || null }) });
      setActiveCase(updated); loadEditor(updated); setNotice("Case metadata saved without changing immutable analysis runs."); await refreshHistory();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Case metadata update failed"); }
    finally { setLoading(false); }
  }

  async function transitionCase(target: InvestigationStatus) {
    if (!activeCase) return; setLoading(true); setError(""); setNotice("");
    try {
      const updated = await api<InvestigationDetail>(`/api/investigations/${activeCase.investigation_id}/transition`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: target }) });
      setActiveCase(updated); loadEditor(updated); setNotice(`Lifecycle moved to ${updated.status}.`); await refreshHistory();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Lifecycle transition failed"); }
    finally { setLoading(false); }
  }

  async function completeAnalysis(payload: AnalysisResponse) {
    setResult(payload); setSelectedId(payload.investigation_id); await refreshHistory(); setRuns(await api<AnalysisRun[]>(`/api/investigations/${payload.investigation_id}/runs`));
    const detail = await api<InvestigationDetail>(`/api/investigations/${payload.investigation_id}`); setActiveCase(detail); loadEditor(detail);
    document.getElementById("analysis-result")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  async function runAnalysis(path: string, body: Record<string, unknown>) {
    if (!activeCase) return; setLoading(true); setError(""); setNotice(""); setResult(null);
    try { await completeAnalysis(await api<AnalysisResponse>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Analysis failed"); }
    finally { setLoading(false); }
  }
  async function submitConditionalAccess(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (activeCase) await runAnalysis("/api/investigations/analyze-conditional-access-csv", { investigation_id: activeCase.investigation_id, title: activeCase.title, source: "public-safe operator evidence", csv_text: csvText }); }
  async function submitResourceAssignment(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (activeCase) await runAnalysis("/api/investigations/analyze-resource-assignment", { investigation_id: activeCase.investigation_id, title: activeCase.title, evidence_id: `${activeCase.investigation_id}-ra-${activeCase.analysis_run_count + 1}`, source: "public-safe operator evidence", subject: assignmentSubject, resource: assignmentResource, access_failed: true, assignment_required: true, assignment_present: assignmentPresent, assignment_name: assignmentName || null, redacted: true }); }
  async function submitGuestB2B(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (activeCase) await runAnalysis("/api/investigations/analyze-guest-b2b", { investigation_id: activeCase.investigation_id, title: activeCase.title, evidence_id: `${activeCase.investigation_id}-gb-${activeCase.analysis_run_count + 1}`, source: "public-safe operator evidence", guest_subject: guestSubject, resource: guestResource, invitation_sent: invitationSent, invitation_redeemed: invitationRedeemed, tenant_restriction_observed: tenantRestrictionObserved, resource_assignment_present: guestAssignmentPresent, restriction_detail: restrictionDetail || null, redacted: true }); }

  async function loadHistory(investigationId: string) { setError(""); setSelectedId(investigationId); try { setRuns(await api<AnalysisRun[]>(`/api/investigations/${investigationId}/runs`)); } catch (caught) { setError(caught instanceof Error ? caught.message : "History failed to load"); } }
  async function changeArchiveState(investigationId: string, action: "archive" | "reopen") {
    setError(""); setNotice("");
    try {
      const updated = await api<InvestigationDetail>(`/api/investigations/${investigationId}/${action}`, { method: "POST" }); await refreshHistory();
      if (activeCase?.investigation_id === investigationId) { if (action === "archive") setActiveCase(null); else { setActiveCase(updated); loadEditor(updated); } }
      if (!includeArchived && action === "archive") { setSelectedId(""); setRuns([]); }
      setNotice(action === "archive" ? "Investigation archived." : "Investigation reopened.");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "History update failed"); }
  }
  async function toggleArchived() { const next = !includeArchived; setIncludeArchived(next); setSelectedId(""); setRuns([]); setHistoryLoading(true); try { await refreshHistory(next); } catch (caught) { setError(caught instanceof Error ? caught.message : "History failed to load"); } finally { setHistoryLoading(false); } }

  const unavailable = loading || historyLoading;
  const scenarioReady = (scenario: ScenarioType) => activeCase?.scenario_type === scenario && activeCase.status !== "archived";
  const lifecycleAction = activeCase ? nextLifecycleAction(activeCase.status) : null;

  return <main className="app-shell" aria-busy={unavailable}>
    <header className="hero"><p className="eyebrow">Local-first IAM investigation workbench</p><h1>TRACE IAM Evidence</h1><p>Create operational cases, preserve redacted evidence provenance, execute deterministic rules, and retain immutable history.</p></header>
    <nav className="scenario-nav" aria-label="Evidence scenarios"><a href="#case-workspace">New case<span>Identity and triage</span></a><a href="#active-case-control">Active case<span>Metadata and lifecycle</span></a><a href="#evidence-workspace">Evidence<span>Inventory and validation</span></a><a href="#conditional_access">Conditional Access<span>CSV sign-in evidence</span></a><a href="#resource_assignment">Resource assignment<span>Entitlement evidence</span></a><a href="#guest_b2b">Guest / B2B<span>Lifecycle evidence</span></a><a href="#history">History<span>Cases, runs and exports</span></a></nav>
    <aside className="privacy-note" aria-label="Evidence safety guidance"><strong>Use redacted evidence and metadata only.</strong> Replace real names, email addresses, tenant IDs, object IDs, tokens, confidential resource names, and sensitive ticket content before entry.</aside>
    {error && <p className="alert" role="alert"><strong>TRACE could not complete the request.</strong><span>{error}</span></p>}{notice && <p className="status" role="status">{notice}</p>}

    <section id="case-workspace" className="case-workspace" aria-labelledby="case-title"><div className="section-heading"><span>Investigation intake</span><h2 id="case-title">Create a persisted operational case</h2></div><form onSubmit={createCase} className="case-form case-intake-grid"><div><label htmlFor="case-name">Case title</label><input id="case-name" value={caseTitle} onChange={(e) => setCaseTitle(e.target.value)} minLength={3} required /></div><div><label htmlFor="case-scenario">Scenario</label><select id="case-scenario" value={caseScenario} onChange={(e) => setCaseScenario(e.target.value as ScenarioType)}><option value="conditional_access">Conditional Access</option><option value="resource_assignment">Resource assignment</option><option value="guest_b2b">Guest / B2B lifecycle</option></select></div><div><label htmlFor="case-priority">Priority</label><select id="case-priority" value={casePriority} onChange={(e) => setCasePriority(e.target.value as CasePriority)}><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="critical">Critical</option></select></div><div><label htmlFor="case-reference">Redacted external reference</label><input id="case-reference" value={caseReference} onChange={(e) => setCaseReference(e.target.value)} /></div><div className="wide-field"><label htmlFor="case-summary">Redacted case summary</label><textarea id="case-summary" rows={3} value={caseSummary} onChange={(e) => setCaseSummary(e.target.value)} /></div><button type="submit" disabled={unavailable}>{loading ? "Creating case…" : "Create investigation"}</button></form></section>

    <section id="active-case-control" className="case-control" aria-labelledby="active-case-title"><div className="section-heading"><span>Operational control</span><h2 id="active-case-title">Active investigation</h2></div>{activeCase ? <><div className={`active-case priority-${activeCase.priority}`} role="status"><span>Active investigation</span><strong>{activeCase.title}</strong><code>{activeCase.investigation_id}</code><small>{activeCase.scenario_type} · {activeCase.status} · {activeCase.evidence_item_count} evidence item(s) · {activeCase.analysis_run_count} run(s)</small><div className="case-badges"><b>{priorityLabel(activeCase.priority)} priority</b>{activeCase.external_reference && <b>{activeCase.external_reference}</b>}</div>{activeCase.summary && <p>{activeCase.summary}</p>}</div><form onSubmit={updateCaseMetadata} className="metadata-form"><div><label htmlFor="edit-title">Case title</label><input id="edit-title" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} required /></div><div><label htmlFor="edit-priority">Priority</label><select id="edit-priority" value={editPriority} onChange={(e) => setEditPriority(e.target.value as CasePriority)}><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="critical">Critical</option></select></div><div><label htmlFor="edit-reference">Redacted external reference</label><input id="edit-reference" value={editReference} onChange={(e) => setEditReference(e.target.value)} /></div><div className="wide-field"><label htmlFor="edit-summary">Redacted case summary</label><textarea id="edit-summary" value={editSummary} onChange={(e) => setEditSummary(e.target.value)} /></div><div className="case-actions"><button type="submit" disabled={unavailable}>Save case metadata</button>{lifecycleAction && <button type="button" className="secondary" disabled={unavailable} onClick={() => transitionCase(lifecycleAction.status)}>{lifecycleAction.label}</button>}</div></form></> : <p className="empty-state">No active investigation. Create a case above or open one from history.</p>}</section>

    <EvidenceWorkspace activeCase={activeCase} unavailable={unavailable} onCaseChanged={reloadActiveCase} onError={setError} onNotice={setNotice} />

    <section id="conditional_access" className="workflow-card" aria-labelledby="workflow-title"><div className="section-heading"><span>Scenario 01</span><h2 id="workflow-title">Conditional Access evidence review</h2></div><p>Paste redacted CSV evidence with the documented four-column contract.</p><form onSubmit={submitConditionalAccess}><label htmlFor="csv-evidence">Redacted Entra sign-in CSV</label><textarea id="csv-evidence" rows={8} value={csvText} onChange={(e) => setCsvText(e.target.value)} required /><button type="submit" disabled={unavailable || !scenarioReady("conditional_access")}>{scenarioReady("conditional_access") ? "Analyze evidence" : "Select a Conditional Access case"}</button></form></section>
    <section id="resource_assignment" className="workflow-card" aria-labelledby="assignment-workflow-title"><div className="section-heading"><span>Scenario 02</span><h2 id="assignment-workflow-title">Resource assignment evidence review</h2></div><form onSubmit={submitResourceAssignment}><label htmlFor="assignment-subject">Redacted subject</label><input id="assignment-subject" value={assignmentSubject} onChange={(e) => setAssignmentSubject(e.target.value)} /><label htmlFor="assignment-resource">Resource</label><input id="assignment-resource" value={assignmentResource} onChange={(e) => setAssignmentResource(e.target.value)} /><label htmlFor="assignment-name">Expected assignment</label><input id="assignment-name" value={assignmentName} onChange={(e) => setAssignmentName(e.target.value)} /><label className="check-row"><input type="checkbox" checked={assignmentPresent} onChange={(e) => setAssignmentPresent(e.target.checked)} />Assignment is present in supplied evidence</label><button type="submit" disabled={unavailable || !scenarioReady("resource_assignment")}>{scenarioReady("resource_assignment") ? "Analyze resource assignment" : "Select a resource-assignment case"}</button></form></section>
    <section id="guest_b2b" className="workflow-card" aria-labelledby="guest-workflow-title"><div className="section-heading"><span>Scenario 03</span><h2 id="guest-workflow-title">Guest B2B lifecycle evidence review</h2></div><form onSubmit={submitGuestB2B}><label htmlFor="guest-subject">Redacted guest subject</label><input id="guest-subject" value={guestSubject} onChange={(e) => setGuestSubject(e.target.value)} /><label htmlFor="guest-resource">Guest resource</label><input id="guest-resource" value={guestResource} onChange={(e) => setGuestResource(e.target.value)} /><div className="check-grid"><label><input type="checkbox" checked={invitationSent} onChange={(e) => setInvitationSent(e.target.checked)} />Invitation was sent</label><label><input type="checkbox" checked={invitationRedeemed} onChange={(e) => setInvitationRedeemed(e.target.checked)} />Invitation was redeemed</label><label><input type="checkbox" checked={tenantRestrictionObserved} onChange={(e) => setTenantRestrictionObserved(e.target.checked)} />Tenant restriction observed</label><label><input type="checkbox" checked={guestAssignmentPresent} onChange={(e) => setGuestAssignmentPresent(e.target.checked)} />Resource assignment present</label></div><label htmlFor="restriction-detail">Redacted restriction detail</label><input id="restriction-detail" value={restrictionDetail} onChange={(e) => setRestrictionDetail(e.target.value)} /><button type="submit" disabled={unavailable || !scenarioReady("guest_b2b")}>{scenarioReady("guest_b2b") ? "Analyze Guest B2B evidence" : "Select a Guest/B2B case"}</button></form></section>

    {result && <section id="analysis-result" className="result-panel" aria-labelledby="result-title"><div className="section-heading"><span>Evidence outcome</span><h2 id="result-title">Analysis result</h2></div><div className="result-summary"><article><span>Run</span><strong>{result.run_number}</strong></article><article><span>Findings</span><strong>{result.finding_count}</strong></article><article><span>Rules evaluated</span><strong>{result.evaluated_rule_ids.join(", ")}</strong></article></div><details open><summary>Evidence report and safe next checks</summary><pre data-testid="markdown-report">{result.markdown_report}</pre></details></section>}

    <section id="history" className="history-panel" aria-labelledby="history-title"><div className="section-heading"><span>Case register</span><h2 id="history-title">Investigation history</h2></div><label className="check-row"><input type="checkbox" checked={includeArchived} onChange={toggleArchived} />Show archived investigations</label>{historyLoading ? <p className="status" role="status">Loading local investigation history…</p> : investigations.length === 0 ? <div className="empty-state"><strong>No persisted investigations yet.</strong><span>Create the first case in the investigation workspace.</span></div> : <ul className="history-list">{investigations.map((item) => <li key={item.investigation_id} className={activeCase?.investigation_id === item.investigation_id ? "is-active" : ""}><button type="button" onClick={() => activateCase(item)}>{item.title}</button><div className="history-meta"><span>{item.status} · {item.analysis_run_count} run(s)</span><small>{item.scenario_type} · {priorityLabel(item.priority)} priority</small>{item.external_reference && <small>{item.external_reference}</small>}{item.summary && <small>{item.summary}</small>}</div><button type="button" className="secondary" onClick={() => loadHistory(item.investigation_id)}>Runs</button><button type="button" className="secondary" onClick={() => changeArchiveState(item.investigation_id, item.status === "archived" ? "reopen" : "archive")}>{item.status === "archived" ? "Reopen" : "Archive"}</button></li>)}</ul>}{selectedId && <section className="runs-panel"><h3>Analysis runs for {selectedId}</h3>{runs.length === 0 ? <p>No analysis runs yet. This case is ready for evidence.</p> : <ul>{runs.map((run) => <li key={run.run_number}><strong>Run {run.run_number}</strong> — {run.ruleset_version}, {run.finding_count} finding(s) <a href={`/api/investigations/${selectedId}/runs/${run.run_number}/report.json`}>Export JSON</a> · <a href={`/api/investigations/${selectedId}/runs/${run.run_number}/report.md`}>Export Markdown</a></li>)}</ul>}</section>}</section>
  </main>;
}
