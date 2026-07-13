import { FormEvent, useEffect, useState } from "react";

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

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail ?? "Request failed");
  }
  return payload as T;
}

export function App() {
  const [csvText, setCsvText] = useState(SAMPLE_CSV);
  const [assignmentSubject, setAssignmentSubject] = useState("redacted-user");
  const [assignmentResource, setAssignmentResource] = useState("Finance application");
  const [assignmentName, setAssignmentName] = useState("Finance App User");
  const [assignmentPresent, setAssignmentPresent] = useState(false);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [investigations, setInvestigations] = useState<InvestigationSummary[]>([]);
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function refreshHistory(showArchived = includeArchived) {
    const query = showArchived ? "?include_archived=true" : "";
    const items = await api<InvestigationSummary[]>(`/api/investigations${query}`);
    setInvestigations(items);
  }

  useEffect(() => {
    refreshHistory().catch((caught) => {
      setError(caught instanceof Error ? caught.message : "History failed to load");
    });
  }, []);

  async function completeAnalysis(payload: AnalysisResponse) {
    setResult(payload);
    setSelectedId(payload.investigation_id);
    await refreshHistory();
    setRuns(await api<AnalysisRun[]>(`/api/investigations/${payload.investigation_id}/runs`));
  }

  async function submitConditionalAccess(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const payload = await api<AnalysisResponse>(
        "/api/investigations/analyze-conditional-access-csv",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            investigation_id: "browser-ca-001",
            title: "Conditional Access sign-in review",
            source: "public-safe browser sample",
            csv_text: csvText
          })
        }
      );
      await completeAnalysis(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  async function submitResourceAssignment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const payload = await api<AnalysisResponse>(
        "/api/investigations/analyze-resource-assignment",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            investigation_id: "browser-ra-001",
            title: "Resource assignment review",
            evidence_id: "browser-ra-evidence-001",
            source: "public-safe browser sample",
            subject: assignmentSubject,
            resource: assignmentResource,
            access_failed: true,
            assignment_required: true,
            assignment_present: assignmentPresent,
            assignment_name: assignmentName || null,
            redacted: true
          })
        }
      );
      await completeAnalysis(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  async function loadHistory(investigationId: string) {
    setError("");
    setSelectedId(investigationId);
    try {
      setRuns(await api<AnalysisRun[]>(`/api/investigations/${investigationId}/runs`));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "History failed to load");
    }
  }

  async function changeArchiveState(investigationId: string, action: "archive" | "reopen") {
    setError("");
    try {
      await api(`/api/investigations/${investigationId}/${action}`, { method: "POST" });
      await refreshHistory();
      if (!includeArchived && action === "archive") {
        setSelectedId("");
        setRuns([]);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "History update failed");
    }
  }

  async function toggleArchived() {
    const next = !includeArchived;
    setIncludeArchived(next);
    setSelectedId("");
    setRuns([]);
    try {
      await refreshHistory(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "History failed to load");
    }
  }

  return (
    <main>
      <p>Local-first IAM evidence investigation workbench</p>
      <h1>TRACE IAM Evidence</h1>

      <section aria-labelledby="workflow-title">
        <h2 id="workflow-title">Conditional Access evidence review</h2>
        <p>Paste only redacted CSV evidence matching the documented four-column contract.</p>
        <form onSubmit={submitConditionalAccess}>
          <label htmlFor="csv-evidence">Redacted Entra sign-in CSV</label>
          <textarea
            id="csv-evidence"
            rows={8}
            value={csvText}
            onChange={(event) => setCsvText(event.target.value)}
          />
          <button type="submit" disabled={loading}>
            {loading ? "Analyzing…" : "Analyze evidence"}
          </button>
        </form>
      </section>

      <section aria-labelledby="assignment-workflow-title">
        <h2 id="assignment-workflow-title">Resource assignment evidence review</h2>
        <p>Record redacted evidence about a failed access attempt and the expected assignment.</p>
        <form onSubmit={submitResourceAssignment}>
          <label htmlFor="assignment-subject">Redacted subject</label>
          <input
            id="assignment-subject"
            value={assignmentSubject}
            onChange={(event) => setAssignmentSubject(event.target.value)}
            required
          />
          <label htmlFor="assignment-resource">Resource</label>
          <input
            id="assignment-resource"
            value={assignmentResource}
            onChange={(event) => setAssignmentResource(event.target.value)}
            required
          />
          <label htmlFor="assignment-name">Expected assignment</label>
          <input
            id="assignment-name"
            value={assignmentName}
            onChange={(event) => setAssignmentName(event.target.value)}
          />
          <label>
            <input
              type="checkbox"
              checked={assignmentPresent}
              onChange={(event) => setAssignmentPresent(event.target.checked)}
            />
            Assignment is present in supplied evidence
          </label>
          <button type="submit" disabled={loading}>
            {loading ? "Analyzing…" : "Analyze resource assignment"}
          </button>
        </form>
      </section>

      {error && <p role="alert">{error}</p>}
      {result && (
        <section aria-labelledby="result-title">
          <h2 id="result-title">Analysis result</h2>
          <p><strong>Run:</strong> {result.run_number}</p>
          <p><strong>Findings:</strong> {result.finding_count}</p>
          <p><strong>Rules evaluated:</strong> {result.evaluated_rule_ids.join(", ")}</p>
          <pre data-testid="markdown-report">{result.markdown_report}</pre>
        </section>
      )}

      <section aria-labelledby="history-title">
        <h2 id="history-title">Investigation history</h2>
        <label>
          <input type="checkbox" checked={includeArchived} onChange={toggleArchived} />
          Show archived investigations
        </label>
        {investigations.length === 0 ? (
          <p>No persisted investigations yet.</p>
        ) : (
          <ul>
            {investigations.map((item) => (
              <li key={item.investigation_id}>
                <button type="button" onClick={() => loadHistory(item.investigation_id)}>
                  {item.title}
                </button>
                <span> — {item.status}, {item.analysis_run_count} run(s)</span>
                <small> ({item.scenario_type})</small>
                <button
                  type="button"
                  onClick={() => changeArchiveState(
                    item.investigation_id,
                    item.status === "archived" ? "reopen" : "archive"
                  )}
                >
                  {item.status === "archived" ? "Reopen" : "Archive"}
                </button>
              </li>
            ))}
          </ul>
        )}

        {selectedId && (
          <section aria-labelledby="runs-title">
            <h3 id="runs-title">Analysis runs for {selectedId}</h3>
            <ul>
              {runs.map((run) => (
                <li key={run.run_number}>
                  <strong>Run {run.run_number}</strong> — {run.ruleset_version}, {run.finding_count} finding(s)
                  {" "}
                  <a href={`/api/investigations/${selectedId}/runs/${run.run_number}/report.json`}>
                    Export JSON
                  </a>
                  {" · "}
                  <a href={`/api/investigations/${selectedId}/runs/${run.run_number}/report.md`}>
                    Export Markdown
                  </a>
                </li>
              ))}
            </ul>
          </section>
        )}
      </section>
    </main>
  );
}
