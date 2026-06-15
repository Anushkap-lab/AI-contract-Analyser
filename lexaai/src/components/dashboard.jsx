import { AlertTriangle, Edit, Download, GitCompare } from "lucide-react";
import MetricGrid from "./metrics";
import ClauseList from "./clauses";
import AskPanel from "./Panel";
// ── Action buttons ─────────────────────────────────────────────────────────────


// ── Summary box ────────────────────────────────────────────────────────────────

function SummaryBox({ summary }) {
  if (!summary) return null;
  return (
    <div className="summary-box">
      <div className="summary-label">AI Summary</div>
      <div className="summary-text">{summary}</div>
    </div>
  );
}

// ── Main dashboard ─────────────────────────────────────────────────────────────

export default function ResultsDashboard({ result }) {
  if (!result) return null;

  const riskScore = result.riskScore ?? 5;
  const clauses   = result.clauses   ?? [];
  const summary   = result.summary   ?? "";

  const metricResult = {
    riskScore,
    clauses,
    contractType: result.contractType ?? result.filename ?? "Contract",
    pageCount:    result.pageCount    ?? "—",
  };

  return (
    <div className="results">
      {/* Metric cards: risk score, clause count, contract type, pages */}
      <MetricGrid result={metricResult} />

      {/* Clause-by-clause breakdown */}
      <h2 className="sec-title">
        <AlertTriangle size={18} strokeWidth={1.8} />
        Key clauses
      </h2>
      <ClauseList clauses={clauses} />

      {/* AI plain-English summary */}
      <SummaryBox summary={summary} />
      {/* Ask AI about this contract */}
      <AskPanel contractId={result.contractId} />
    </div>
  );
}
