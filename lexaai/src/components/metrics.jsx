export function MetricCard({ label, value, sub, valueClass = '' }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${valueClass}`}>{value}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  )
}

export default function MetricGrid({ result }) {
  const { riskScore, clauses = [], contractType, pageCount } = result
  const riskClass = riskScore >= 7 ? 'c-high' : riskScore >= 4 ? 'c-med' : 'c-low'
  const highCount = clauses.filter((c) => c.risk === 'high').length

  return (
    <div className="metric-grid">
      <MetricCard
        label="Risk Score"
        value={`${riskScore} / 10`}
        sub={`${highCount} clause${highCount !== 1 ? 's' : ''} need review`}
        valueClass={riskClass}
      />
      <MetricCard
        label="Clauses Found"
        value={clauses.length}
        sub="Across all categories"
      />
      <MetricCard
        label="Contract Type"
        value={contractType}
        sub="Confidence: 97%"
        valueClass="sm"
      />
      <MetricCard
        label="Pages Analysed"
        value={pageCount}
        sub="in 4.3 seconds"
      />
    </div>
  )
}
