import { useMemo, useState } from "react";

import "./FindingsWorkspace.css";

type Severity = "info" | "low" | "medium" | "high";
type Confidence = "low" | "medium" | "high";

type RecommendedCheck = {
  description: string;
  purpose: string;
  risk: Severity;
};

type NonAction = {
  description: string;
  reason: string;
};

type Finding = {
  finding_id: string;
  rule_id: string;
  rule_version: string;
  title: string;
  severity: Severity;
  confidence: Confidence;
  supporting_fact_types: string[];
  contradicting_fact_types: string[];
  missing_fact_types: string[];
  limitations: string[];
  recommended_checks: RecommendedCheck[];
  non_actions: NonAction[];
};

type AnalysisResult = {
  run_number: number;
  finding_count: number;
  evaluated_rule_ids: string[];
  markdown_report: string;
  json_report: Record<string, unknown>;
};

type Props = {
  result: AnalysisResult;
};

const severityOrder: Record<Severity, number> = { high: 4, medium: 3, low: 2, info: 1 };

function isFinding(value: unknown): value is Finding {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<Finding>;
  return typeof candidate.finding_id === "string"
    && typeof candidate.rule_id === "string"
    && typeof candidate.rule_version === "string"
    && typeof candidate.title === "string"
    && ["info", "low", "medium", "high"].includes(candidate.severity ?? "")
    && ["low", "medium", "high"].includes(candidate.confidence ?? "")
    && Array.isArray(candidate.supporting_fact_types)
    && Array.isArray(candidate.contradicting_fact_types)
    && Array.isArray(candidate.missing_fact_types)
    && Array.isArray(candidate.limitations)
    && Array.isArray(candidate.recommended_checks)
    && Array.isArray(candidate.non_actions);
}

function FactList({ title, values, empty }: { title: string; values: string[]; empty: string }) {
  return <section className="finding-facts">
    <h4>{title}</h4>
    {values.length ? <ul>{values.map((value) => <li key={value}>{value}</li>)}</ul> : <p>{empty}</p>}
  </section>;
}

export function FindingsWorkspace({ result }: Props) {
  const [severity, setSeverity] = useState<"all" | Severity>("all");
  const [confidence, setConfidence] = useState<"all" | Confidence>("all");
  const findings = useMemo(() => {
    const raw = result.json_report.findings;
    if (!Array.isArray(raw)) return [];
    return raw.filter(isFinding).sort((left, right) => severityOrder[right.severity] - severityOrder[left.severity]);
  }, [result.json_report]);
  const visible = findings.filter((finding) =>
    (severity === "all" || finding.severity === severity)
    && (confidence === "all" || finding.confidence === confidence));

  return <section id="analysis-result" className="findings-workspace" aria-labelledby="findings-title">
    <div className="section-heading"><span>Structured findings workspace</span><h2 id="findings-title">Analysis result</h2></div>
    <div className="result-summary">
      <article><span>Run</span><strong>{result.run_number}</strong></article>
      <article><span>Findings</span><strong>{result.finding_count}</strong></article>
      <article><span>Rules evaluated</span><strong>{result.evaluated_rule_ids.join(", ") || "None"}</strong></article>
    </div>
    <div className="finding-filters" aria-label="Finding filters">
      <label>Severity<select value={severity} onChange={(event) => setSeverity(event.target.value as "all" | Severity)}><option value="all">All severities</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option><option value="info">Info</option></select></label>
      <label>Confidence<select value={confidence} onChange={(event) => setConfidence(event.target.value as "all" | Confidence)}><option value="all">All confidence levels</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
      <span>{visible.length} of {findings.length} finding(s)</span>
    </div>
    {findings.length === 0 ? <div className="empty-state"><strong>No supported finding was produced.</strong><span>Review the supplied evidence, missing facts, and the raw report before taking action.</span></div> : visible.length === 0 ? <p className="empty-state">No findings match the selected filters.</p> : <div className="finding-grid">{visible.map((finding) => <article className={`finding-card severity-${finding.severity}`} key={finding.finding_id}>
      <header><div><span>{finding.rule_id} · version {finding.rule_version}</span><h3>{finding.title}</h3></div><div className="finding-badges"><b>{finding.severity} severity</b><b>{finding.confidence} confidence</b></div></header>
      <div className="fact-columns">
        <FactList title="Supporting evidence" values={finding.supporting_fact_types} empty="No supporting facts recorded." />
        <FactList title="Contradicting evidence" values={finding.contradicting_fact_types} empty="No contradicting facts recorded." />
        <FactList title="Missing evidence" values={finding.missing_fact_types} empty="No missing facts identified." />
      </div>
      <section className="safe-checks"><h4>Safe next checks</h4>{finding.recommended_checks.length ? <ul>{finding.recommended_checks.map((check) => <li key={`${check.description}-${check.purpose}`}><strong>{check.description}</strong><span>{check.purpose}</span><small>{check.risk} risk</small></li>)}</ul> : <p>No additional checks were generated.</p>}</section>
      <section className="non-actions"><h4>Do not change yet</h4>{finding.non_actions.length ? <ul>{finding.non_actions.map((item) => <li key={`${item.description}-${item.reason}`}><strong>{item.description}</strong><span>{item.reason}</span></li>)}</ul> : <p>No explicit non-actions were generated.</p>}</section>
      {finding.limitations.length > 0 && <section className="limitations"><h4>Limitations</h4><ul>{finding.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>}
    </article>)}</div>}
    <details><summary>Raw Markdown report</summary><pre data-testid="markdown-report">{result.markdown_report}</pre></details>
    <details><summary>Raw JSON report</summary><pre data-testid="json-report">{JSON.stringify(result.json_report, null, 2)}</pre></details>
  </section>;
}
