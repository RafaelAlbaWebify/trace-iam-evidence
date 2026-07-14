import { useEffect, useState } from "react";

import "./RunComparisonWorkspace.css";

type ActiveCase = { investigation_id: string; analysis_run_count: number };
type RunSummary = { run_number: number; created_at: string; ruleset_version: string; finding_count: number };
type Finding = Record<string, unknown>;
type FindingChange = { identity: string; before: Finding; after: Finding; changed_fields: string[] };
type Comparison = {
  base_run_number: number;
  target_run_number: number;
  base_ruleset_version: string;
  target_ruleset_version: string;
  ruleset_changed: boolean;
  added_findings: Finding[];
  resolved_findings: Finding[];
  changed_findings: FindingChange[];
  added_evidence_ids: string[];
  removed_evidence_ids: string[];
  unchanged_finding_count: number;
};

type Props = { activeCase: ActiveCase | null; unavailable: boolean; onError: (message: string) => void };

async function request<T>(path: string): Promise<T> {
  const response = await fetch(path);
  const payload = await response.json();
  if (!response.ok) throw new Error(typeof payload?.detail === "string" ? payload.detail : `Comparison request failed with HTTP ${response.status}.`);
  return payload as T;
}

function findingLabel(finding: Finding): string {
  for (const key of ["title", "finding_id", "rule_id"]) {
    const value = finding[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return "Unnamed finding";
}

export function RunComparisonWorkspace({ activeCase, unavailable, onError }: Props) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [baseRun, setBaseRun] = useState(1);
  const [targetRun, setTargetRun] = useState(2);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setComparison(null);
    if (!activeCase) { setRuns([]); return; }
    request<RunSummary[]>(`/api/investigations/${activeCase.investigation_id}/runs`)
      .then((items) => {
        setRuns(items);
        if (items.length >= 2) {
          setBaseRun(items[items.length - 2].run_number);
          setTargetRun(items[items.length - 1].run_number);
        }
      })
      .catch((caught) => onError(caught instanceof Error ? caught.message : "Analysis runs failed to load"));
  }, [activeCase?.investigation_id, activeCase?.analysis_run_count]);

  async function compare() {
    if (!activeCase) return;
    setLoading(true); onError("");
    try {
      setComparison(await request<Comparison>(`/api/investigations/${activeCase.investigation_id}/compare-runs?base_run=${baseRun}&target_run=${targetRun}`));
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Run comparison failed");
    } finally { setLoading(false); }
  }

  const exportPayload = comparison ? JSON.stringify(comparison, null, 2) : "";
  const exportHref = comparison ? `data:application/json;charset=utf-8,${encodeURIComponent(exportPayload)}` : "#";

  return <section id="run-comparison" className="comparison-workspace" aria-labelledby="comparison-title">
    <div className="section-heading"><span>Immutable run progression</span><h2 id="comparison-title">Analysis run comparison</h2></div>
    {!activeCase ? <p className="empty-state">Create or open an investigation to compare its analysis runs.</p> : runs.length < 2 ? <div className="empty-state"><strong>Two immutable runs are required.</strong><span>Execute another evidence analysis to compare progression.</span></div> : <>
      <div className="comparison-controls">
        <label>Base run<select value={baseRun} onChange={(event) => setBaseRun(Number(event.target.value))}>{runs.map((run) => <option value={run.run_number} key={run.run_number}>Run {run.run_number} · {run.ruleset_version}</option>)}</select></label>
        <label>Target run<select value={targetRun} onChange={(event) => setTargetRun(Number(event.target.value))}>{runs.map((run) => <option value={run.run_number} key={run.run_number}>Run {run.run_number} · {run.ruleset_version}</option>)}</select></label>
        <button type="button" disabled={unavailable || loading || baseRun === targetRun} onClick={compare}>{loading ? "Comparing…" : "Compare immutable runs"}</button>
      </div>
      {comparison && <div className="comparison-result" role="region" aria-label="Run comparison result">
        <div className="result-summary"><article><span>Added findings</span><strong>{comparison.added_findings.length}</strong></article><article><span>Resolved findings</span><strong>{comparison.resolved_findings.length}</strong></article><article><span>Changed findings</span><strong>{comparison.changed_findings.length}</strong></article><article><span>Unchanged findings</span><strong>{comparison.unchanged_finding_count}</strong></article></div>
        <p><strong>Ruleset:</strong> {comparison.base_ruleset_version} → {comparison.target_ruleset_version}{comparison.ruleset_changed ? " (changed)" : " (unchanged)"}</p>
        <div className="comparison-grid">
          <section><h3>Added findings</h3>{comparison.added_findings.length ? <ul>{comparison.added_findings.map((finding, index) => <li key={index}>{findingLabel(finding)}</li>)}</ul> : <p>None.</p>}</section>
          <section><h3>Resolved findings</h3>{comparison.resolved_findings.length ? <ul>{comparison.resolved_findings.map((finding, index) => <li key={index}>{findingLabel(finding)}</li>)}</ul> : <p>None.</p>}</section>
          <section><h3>Changed findings</h3>{comparison.changed_findings.length ? <ul>{comparison.changed_findings.map((change) => <li key={change.identity}><strong>{change.identity}</strong><span>{change.changed_fields.join(", ")}</span></li>)}</ul> : <p>None.</p>}</section>
          <section><h3>Evidence changes</h3><p><strong>Added:</strong> {comparison.added_evidence_ids.join(", ") || "None"}</p><p><strong>Removed:</strong> {comparison.removed_evidence_ids.join(", ") || "None"}</p></section>
        </div>
        <a className="comparison-export" download={`trace-${activeCase.investigation_id}-runs-${comparison.base_run_number}-${comparison.target_run_number}.json`} href={exportHref}>Export comparison JSON</a>
      </div>}
    </>}
  </section>;
}
