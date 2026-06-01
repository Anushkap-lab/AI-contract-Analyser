const RISK_CONFIG = {
  high:   { dot: "bg-red-500",    badge: "bg-red-50 text-red-700",    label: "High Risk" },
  medium: { dot: "bg-amber-500",  badge: "bg-amber-50 text-amber-700", label: "Caution" },
  low:    { dot: "bg-emerald-500",badge: "bg-emerald-50 text-emerald-700", label: "Clear" },
};

export default function ClauseList({ clauses = [] }) {
  return (
    <div className="flex flex-col gap-2">
      {clauses.map((clause, i) => {
        const cfg = RISK_CONFIG[clause.risk] || RISK_CONFIG.low;
        return (
          <div key={i} className="flex items-start gap-3 border border-gray-100 dark:border-gray-700 rounded-xl p-3 bg-white dark:bg-gray-900">
            <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${cfg.dot}`} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">{clause.name}</p>
              <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{clause.description}</p>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-md shrink-0 ${cfg.badge}`}>
              {cfg.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}