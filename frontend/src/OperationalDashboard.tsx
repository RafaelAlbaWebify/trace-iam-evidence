import { FormEvent, useEffect, useState } from "react";

import "./OperationalDashboard.css";

type ScenarioType = "conditional_access" | "resource_assignment" | "guest_b2b";
type CasePriority = "low" | "normal" | "high" | "critical";
type InvestigationStatus = "draft" | "evidence_validated" | "analyzed" | "reviewed" | "exported" | "archived";

type OperationalCase = {
  investigation_id: string;
  title: string;
  scenario_type: ScenarioType;
  status: InvestigationStatus;
  priority: CasePriority;
  external_reference: string | null;
  summary: string | null;
  created_at: string;
  archived_at: string | null;
  last_activity_at: string;
  analysis_run_count: number;
};

type Dashboard = {
  total_cases: number;
  active_cases: number;
  waiting_for_evidence: number;
  ready_for_analysis: number;
  under_review: number;
  critical_active: number;
  archived_cases: number;
  filtered_case_count: number;
  cases: OperationalCase[];
};

type Props = {
  onOpenCase: (investigationId: string) => Promise<void>;
  onError: (message: string) => void;
};

const label = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());

export function OperationalDashboard({ onOpenCase, onError }: Props) {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [scenario, setScenario] = useState("");
  const [priority, setPriority] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    onError("");
    const parameters = new URLSearchParams();
    if (query.trim()) parameters.set("query", query.trim());
    if (status) parameters.set("status", status);
    if (scenario) parameters.set("scenario", scenario);
    if (priority) parameters.set("priority", priority);
    if (includeArchived) parameters.set("include_archived", "true");
    try {
      const response = await fetch(`/api/operations/dashboard?${parameters.toString()}`);
      if (!response.ok) throw new Error(`Operational dashboard failed with HTTP ${response.status}.`);
      setDashboard(await response.json() as Dashboard);
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Operational dashboard failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void load();
  }

  return <section id="operations-dashboard" className="operations-dashboard" aria-labelledby="operations-title">
    <div className="section-heading"><span>Operational overview</span><h2 id="operations-title">Case search and workload dashboard</h2></div>
    {dashboard && <div className="operations-metrics" aria-label="Operational workload summary">
      <article><span>Active</span><strong>{dashboard.active_cases}</strong></article>
      <article><span>Waiting for evidence</span><strong>{dashboard.waiting_for_evidence}</strong></article>
      <article><span>Ready for analysis</span><strong>{dashboard.ready_for_analysis}</strong></article>
      <article><span>Under review</span><strong>{dashboard.under_review}</strong></article>
      <article><span>Critical active</span><strong>{dashboard.critical_active}</strong></article>
      <article><span>Archived</span><strong>{dashboard.archived_cases}</strong></article>
    </div>}
    <form className="operations-filters" onSubmit={applyFilters}>
      <label>Search cases<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="ID, title, reference, or summary" /></label>
      <label>Status<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option><option value="draft">Draft</option><option value="evidence_validated">Evidence validated</option><option value="analyzed">Analyzed</option><option value="reviewed">Reviewed</option><option value="exported">Exported</option><option value="archived">Archived</option></select></label>
      <label>Scenario<select value={scenario} onChange={(event) => setScenario(event.target.value)}><option value="">All scenarios</option><option value="conditional_access">Conditional Access</option><option value="resource_assignment">Resource assignment</option><option value="guest_b2b">Guest / B2B</option></select></label>
      <label>Priority<select value={priority} onChange={(event) => setPriority(event.target.value)}><option value="">All priorities</option><option value="critical">Critical</option><option value="high">High</option><option value="normal">Normal</option><option value="low">Low</option></select></label>
      <label className="check-row"><input type="checkbox" checked={includeArchived} onChange={(event) => setIncludeArchived(event.target.checked)} />Include archived cases</label>
      <button type="submit" disabled={loading}>{loading ? "Refreshing…" : "Apply operational filters"}</button>
    </form>
    {loading && !dashboard ? <p className="status" role="status">Loading operational workload…</p> : dashboard?.cases.length === 0 ? <p className="empty-state">No investigations match the selected operational filters.</p> : dashboard && <>
      <p className="operations-count">Showing {dashboard.filtered_case_count} of {dashboard.total_cases} persisted case(s), ordered by latest immutable activity.</p>
      <ul className="operations-case-list">{dashboard.cases.map((item) => <li key={item.investigation_id} className={`priority-${item.priority}`}>
        <div><span>{label(item.scenario_type)} · {label(item.status)}</span><h3>{item.title}</h3><code>{item.investigation_id}</code></div>
        <div className="operations-case-meta"><b>{label(item.priority)} priority</b>{item.external_reference && <span>{item.external_reference}</span>}<span>{item.analysis_run_count} immutable run(s)</span><span>Last activity {new Date(item.last_activity_at).toLocaleString()}</span></div>
        {item.summary && <p>{item.summary}</p>}
        <button type="button" onClick={() => onOpenCase(item.investigation_id)}>Open investigation</button>
      </li>)}</ul>
    </>}
  </section>;
}
