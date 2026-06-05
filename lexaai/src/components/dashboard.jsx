import MetricGrid from "./metrics";
import {
  AlertTriangle,
  FileText,
  ListX,
  ShieldAlert,
  ShieldQuestion,
  Gauge,
} from "lucide-react";

const REPORT_SECTIONS = [
  {
    key: "summary",
    title: "Plain English risk summary",
    icon: FileText,
    fallback: "No plain English summary was returned.",
  },
  {
    key: "unfair",
    title: "Unfair clauses",
    icon: ListX,
    fallback: "No unfair clauses were identified.",
  },
  {
    key: "missing",
    title: "Missing terms",
    icon: ShieldQuestion,
    fallback: "No missing terms were identified.",
  },
  {
    key: "liability",
    title: "Liability traps",
    icon: ShieldAlert,
    fallback: "No liability traps were identified.",
  },
  {
    key: "risk",
    title: "Overall risk score",
    icon: Gauge,
    fallback: "No overall risk score was returned.",
  },
];


function riskScoreFromTone(tone) {
  if (tone === "high") return 8.2;
  if (tone === "medium") return 6.2;
  return 2.4;
}

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function parseReportSections(text) {
  const matches = REPORT_SECTIONS
    .map((section, index) => {
      const pattern = new RegExp(
        `(^|\\n)\\s*(?:${index + 1}\\s*[.)-]?\\s*)?(?:\\*\\*)?${escapeRegExp(section.title)}(?:\\*\\*)?\\s*:?`,
        "i",
      );
      const match = pattern.exec(text);
      return match
        ? {
            key: section.key,
            index: match.index,
            contentStart: match.index + match[0].length,
          }
        : null;
    })
    .filter(Boolean)
    .sort((a, b) => a.index - b.index);

  if (matches.length === 0) {
    return { summary: text };
  }

  return matches.reduce((sections, match, index) => {
    const next = matches[index + 1];
    sections[match.key] = text
      .slice(match.contentStart, next ? next.index : text.length)
      .trim()
      .replace(/^[-:]\s*/, "");
    return sections;
  }, {});
}

function formatSectionText(text) {
  const lines = String(text)
    .split(/\n+/)
    .map((line) => line.trim().replace(/^[-*•]\s*/, ""))
    .filter(Boolean);

  return lines.length > 0 ? lines : [String(text).trim()].filter(Boolean);
}

function ReportSectionCard({ section, content, riskTone }) {
  const Icon = section.icon;
  const lines = formatSectionText(content || section.fallback);
  const isRisk = section.key === "risk";

  return (
    <article className={`report-section ${isRisk ? `risk-${riskTone}` : ""}`}>
      <div className="report-section-head">
        <div className="report-section-icon">
          <Icon size={18} strokeWidth={1.8} />
        </div>
        <h3>{section.title}</h3>
      </div>

      <div className="report-section-body">
        {isRisk && (
          <span className={`risk-pill risk-${riskTone}`}>
            {riskTone === "high" ? "High Risk" : riskTone === "medium" ? "Medium Risk" : "Low Risk"}
          </span>
        )}
        {lines.map((line, index) => (
          <p key={index}>{line}</p>
        ))}
      </div>
    </article>
  );
}

export default function ResultsDashboard({ result }) {
  const analysis = Array.isArray(result?.analysis) ? result.analysis : [];
  const fullText = analysis.join("\n\n");
  const riskTone = getRiskTone(fullText);
  const reportSections = parseReportSections(fullText);
  const structuredClauses = result?.clauses || analysis
    .filter((item) => typeof item !== "string")
    .map((item, index) => ({
    name: typeof item === "string" ? `Clause ${index + 1}` : item?.name,
    }))
    return(
      <>
        <h2 className="sec-title mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">
          <AlertTriangle size={18} strokeWidth={1.8} />
            Contract analysis report
        </h2>
        <div className="report-section-grid">
          {REPORT_SECTIONS.map((section) => (
            <ReportSectionCard
              key={section.key}
              section={section}
              content={reportSections[section.key]}
              riskTone={riskTone} 
            />
          ))}
        </div></>
    );

  const dashboardResult = {
       riskScore: result?.riskScore ?? riskScoreFromTone(riskTone),
  };
}