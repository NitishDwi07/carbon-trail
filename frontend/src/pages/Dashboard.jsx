import { useState, useEffect } from "react";
import { useApp } from "../App";

function StatCard({ label, value, sub, color = "emerald" }) {
  const colors = {
    emerald: "text-emerald-400",
    yellow: "text-yellow-400",
    red: "text-red-400",
    stone: "text-stone-300",
    blue: "text-blue-400",
  };
  return (
    <div className="bg-stone-900 border border-stone-800 rounded-lg p-4">
      <p className="text-stone-500 text-xs mb-1">{label}</p>
      <p className={`text-2xl font-bold ${colors[color]}`}>{value}</p>
      {sub && <p className="text-stone-600 text-xs mt-1">{sub}</p>}
    </div>
  );
}

function ScopeBar({ byScope }) {
  const scopes = [
    { key: "1", label: "Scope 1", color: "bg-orange-500", desc: "Direct emissions" },
    { key: "2", label: "Scope 2", color: "bg-blue-500", desc: "Purchased electricity" },
    { key: "3", label: "Scope 3", color: "bg-purple-500", desc: "Value chain" },
  ];

  const totalCo2 = Object.values(byScope).reduce(
    (sum, v) => sum + parseFloat(v.co2e || 0), 0
  );

  if (totalCo2 === 0) return null;

  return (
    <div className="bg-stone-900 border border-stone-800 rounded-lg p-4">
      <p className="text-stone-400 text-xs mb-3 font-medium">CO2e by Scope</p>
      <div className="flex rounded overflow-hidden h-4 mb-3">
        {scopes.map((s) => {
          const pct = totalCo2 > 0
            ? (parseFloat(byScope[s.key]?.co2e || 0) / totalCo2) * 100
            : 0;
          return pct > 0 ? (
            <div key={s.key} style={{ width: `${pct}%` }} className={`${s.color}`} title={`${s.label}: ${pct.toFixed(1)}%`} />
          ) : null;
        })}
      </div>
      <div className="flex gap-4">
        {scopes.map((s) => {
          const co2 = parseFloat(byScope[s.key]?.co2e || 0);
          const pct = totalCo2 > 0 ? ((co2 / totalCo2) * 100).toFixed(1) : "0";
          return (
            <div key={s.key} className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${s.color}`} />
              <span className="text-stone-400 text-xs">{s.label}</span>
              <span className="text-stone-500 text-xs">{pct}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { apiFetch } = useApp();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/dashboard/").then((r) => r.json()).then(setStats).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-stone-500 text-sm">loading...</p>;
  if (!stats) return <p className="text-red-400 text-sm">Failed to load dashboard</p>;

  const co2Tonnes = (parseFloat(stats.total_co2e_kg) / 1000).toFixed(1);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-stone-200 font-bold text-lg">Dashboard</h2>
        <p className="text-stone-500 text-xs mt-0.5">Review status and emissions overview</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatCard label="Total records" value={stats.total_records} color="stone" />
        <StatCard label="Pending review" value={stats.pending} color="yellow" sub="needs attention" />
        <StatCard label="Approved" value={stats.approved} color="emerald" sub="locked for audit" />
        <StatCard label="Flagged" value={stats.flagged} color="red" sub="suspicious rows" />
        <StatCard label="Total CO2e" value={`${co2Tonnes}t`} color="blue" sub="kg CO2e across all records" />
      </div>

      {/* Scope breakdown */}
      {stats.by_scope && <ScopeBar byScope={stats.by_scope} />}

      {/* Category breakdown */}
      {stats.by_category && (
        <div className="bg-stone-900 border border-stone-800 rounded-lg p-4">
          <p className="text-stone-400 text-xs mb-3 font-medium">Records by Category</p>
          <div className="space-y-2">
            {Object.entries(stats.by_category).map(([cat, data]) => (
              <div key={cat} className="flex items-center justify-between text-xs">
                <span className="text-stone-300 capitalize">{cat.replace("_", " ")}</span>
                <div className="flex items-center gap-4">
                  <span className="text-stone-500">{data.count} records</span>
                  <span className="text-stone-400">{(parseFloat(data.co2e || 0) / 1000).toFixed(2)}t CO2e</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent batches */}
      {stats.recent_batches?.length > 0 && (
        <div className="bg-stone-900 border border-stone-800 rounded-lg p-4">
          <p className="text-stone-400 text-xs mb-3 font-medium">Recent Ingestion Batches</p>
          <div className="space-y-2">
            {stats.recent_batches.map((b) => (
              <div key={b.id} className="flex items-center justify-between text-xs border-b border-stone-800 pb-2 last:border-0 last:pb-0">
                <div>
                  <span className="text-stone-300">{b.original_filename || b.source_type_display}</span>
                  <span className="text-stone-600 ml-2">{b.source_type_display}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-stone-500">{b.row_count} rows</span>
                  {b.error_count > 0 && (
                    <span className="text-red-400">{b.error_count} errors</span>
                  )}
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    b.status === "done" ? "bg-emerald-400/10 text-emerald-400" :
                    b.status === "failed" ? "bg-red-400/10 text-red-400" :
                    "bg-yellow-400/10 text-yellow-400"
                  }`}>
                    {b.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
