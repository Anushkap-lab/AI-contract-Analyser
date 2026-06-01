import ClauseList from "./clauses";
import MetricGrid from "./metrics";
import { AlertTriangle } from "lucide-react";

function getRiskTone(text) {
  const lower = String(text).toLowerCase();
  if (lower.includes("high risk")) return "high";
  if (lower.includes("medium risk")) return "medium";
  return "low";
}

function riskScoreFromTone(tone) {
  if (tone === "high") return 8.2;
  if (tone === "medium") return 6.2;
  return 2.4;
}

export default function ResultsDashboard({ result }) {
  const analysis = Array.isArray(result?.analysis) ? result.analysis : [];
  const fullText = analysis.join("\n\n");
  const riskTone = getRiskTone(fullText);
  const structuredClauses = result?.clauses || analysis
    .filter((item) => typeof item !== "string")
    .map((item, index) => ({
    name: typeof item === "string" ? `Clause ${index + 1}` : item?.name,
    description: typeof item === "string" ? item : item?.description,
    risk: typeof item === "string" ? riskTone : item?.risk,
  }));
  const displayItems = result?.clauses || analysis;

  const dashboardResult = {
    riskScore: result?.riskScore ?? riskScoreFromTone(riskTone),
    clauses: structuredClauses.length > 0 ? structuredClauses : [{ risk: riskTone }],
    contractType: result?.contractType || result?.filename || "Contract",
    pageCount: result?.pageCount || result?.pagesAnalysed || "-",
  };

  return (
    <section className="results mt-6 space-y-4 text-left">
      <MetricGrid result={dashboardResult} />

      <div>
        <h2 className="sec-title mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">
          <AlertTriangle size={18} strokeWidth={1.8} />
          Analysis summary
        </h2>
        <ClauseList clauses={displayItems} />
      </div>
    </section>
  );
}
