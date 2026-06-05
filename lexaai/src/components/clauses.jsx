const RISK_CONFIG = {
  high:   { dot: "bg-red-500",    badge: "bg-red-50 text-red-700",    label: "High Risk" },
  medium: { dot: "bg-amber-500",  badge: "bg-amber-50 text-amber-700", label: "Caution" },
  low:    { dot: "bg-emerald-500",badge: "bg-emerald-50 text-emerald-700", label: "Clear" },
};

export default function ClauseList({ clauses = [] }) {
  return (
    <div className="clause-list">
      {clauses.map((clause, i) => {
        const isText = typeof clause === "string";
        const name = isText ? `Finding ${i + 1}` : clause?.name || `Finding ${i + 1}`;
        const description = isText ? clause : clause?.description || clause?.text || "No details provided.";
        const risk = isText ? "low" : clause?.risk;
        const cfg = RISK_CONFIG[risk] || RISK_CONFIG.low;

        return (
          <div key={i} className="clause-item">
            <span className={`clause-dot ${cfg.dot}`} />
            <div className="clause-body">
              <p className="clause-name">{name}</p>
              <p className="clause-desc">{description}</p>
            </div>
            <span className={`clause-badge ${cfg.badge}`}>
              {cfg.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
