import { AlertTriangle, Edit, Download, GitCompare } from "lucide-react";
import MetricGrid from "./metrics";
import ClauseList from "./clauses";
import AskPanel from "./Panel";

function parseSummaryPoints(text) {
  if (!text) return [];
 
  // Strip all **bold** markers
  const clean = text.replace(/\*\*(.*?)\*\*/g, "$1");
 
  // Split on numbered list items: "1. ", "2. " etc
  const points = clean
    .split(/(?<!\d)\d+\.\s+/)
    .map(s => s.trim())
    .filter(Boolean);
 
  // If only one block (no numbered items), split by sentence instead
  if (points.length <= 1) {
    return clean
      .split(/(?<=[.!?])\s+/)
      .map(s => s.trim())
      .filter(s => s.length > 20); // skip tiny fragments
  }
 
  return points;
}
 
function SummaryBox({ summary }) {
  if (!summary) return null;
  const points = parseSummaryPoints(summary);
 
  return (
    <div className="summary-box">
      <div className="summary-label">AI Summary</div>
      <ul style={{
        listStyle: "none",
        margin: "8px 0 0",
        padding: 0,
        display: "flex",
        flexDirection: "column",
        gap: "10px",
      }}>
        {points.map((point, i) => (
          <li key={i} style={{
            display: "flex",
            gap: "10px",
            alignItems: "flex-start",
            fontSize: "13px",
            color: "var(--text2)",
            lineHeight: 1.65,
          }}>
            <span style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: "var(--warn-dot)",
              flexShrink: 0,
              marginTop: "0.45em",
            }} />
            {point}
          </li>
        ))}
      </ul>
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
