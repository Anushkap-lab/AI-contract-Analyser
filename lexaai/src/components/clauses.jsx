
const RISK_CONFIG = {
  high:   { dot: "d-risk", badge: "b-risk", label: "High Risk" },
  medium: { dot: "d-warn", badge: "b-warn", label: "Caution"   },
  low:    { dot: "d-ok",   badge: "b-ok",   label: "Clear"     },
};

export default function ClauseList({ clauses = [] }) {
  if (clauses.length === 0) {
    return (
      <p style={{ fontSize: 13, color: "var(--text3)", marginBottom: "1.25rem" }}>
        No clauses were identified.
      </p>
    );
  }

  return (
    <div className="clause-list">
      {clauses.map((clause, i) => {
        // Backend may send a plain string or a proper object
        const isText    = typeof clause === "string";
        const name      = isText ? `Finding ${i + 1}` : (clause?.name        || `Finding ${i + 1}`);
        const desc      = isText ? clause              : (clause?.description || clause?.text || "No details provided.");
        const risk      = isText ? "low"               : (clause?.risk        || "low");
        const cfg       = RISK_CONFIG[risk] ?? RISK_CONFIG.low;

        return (
          <div key={i} className="clause-item">
            <span className={`clause-dot ${cfg.dot}`} />
            <div className="clause-body">
              <p className="clause-name">{name}</p>
              <p className="clause-desc">{desc}</p>
            </div>
            <span className={`clause-badge ${cfg.badge}`}>{cfg.label}</span>
          </div>
        );
      })}
    </div>
  );
}

