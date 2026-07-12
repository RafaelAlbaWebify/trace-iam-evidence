import { FormEvent, useState } from "react";

const SAMPLE_CSV = `Sign-in ID,Conditional Access Status,Failure Reason,Conditional Access Policy
signin-001,failure,Device is not compliant,Require compliant device`;

type AnalysisResponse = {
  finding_count: number;
  evaluated_rule_ids: string[];
  markdown_report: string;
  json_report: Record<string, unknown>;
};

export function App() {
  const [csvText, setCsvText] = useState(SAMPLE_CSV);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("/api/investigations/analyze-conditional-access-csv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          investigation_id: "browser-ca-001",
          title: "Conditional Access sign-in review",
          source: "public-safe browser sample",
          csv_text: csvText
        })
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Analysis failed");
      }
      setResult(payload as AnalysisResponse);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <p>Local-first IAM evidence investigation workbench</p>
      <h1>TRACE IAM Evidence</h1>
      <section aria-labelledby="workflow-title">
        <h2 id="workflow-title">Conditional Access evidence review</h2>
        <p>Paste only redacted CSV evidence matching the documented four-column contract.</p>
        <form onSubmit={submit}>
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

      {error && <p role="alert">{error}</p>}
      {result && (
        <section aria-labelledby="result-title">
          <h2 id="result-title">Analysis result</h2>
          <p><strong>Findings:</strong> {result.finding_count}</p>
          <p><strong>Rules evaluated:</strong> {result.evaluated_rule_ids.join(", ")}</p>
          <pre data-testid="markdown-report">{result.markdown_report}</pre>
        </section>
      )}
    </main>
  );
}
