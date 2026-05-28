import { useState, useEffect, useCallback } from "react";
import { useApp } from "../App";

const SCOPE_COLORS = {
  "1": "text-orange-400",
  "2": "text-blue-400",
  "3": "text-purple-400",
};

const STATUS_STYLES = {
  pending: "bg-yellow-400/10 text-yellow-400 border-yellow-400/20",
  approved: "bg-emerald-400/10 text-emerald-400 border-emerald-400/20",
  flagged: "bg-red-400/10 text-red-400 border-red-400/20",
  rejected: "bg-stone-400/10 text-stone-400 border-stone-400/20",
};

function ReviewModal({ record, onClose, onUpdate }) {
  const { apiFetch } = useApp();
  const [action, setAction] = useState("approve");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [auditLog, setAuditLog] = useState([]);

  useEffect(() => {
    apiFetch(`/records/${record.id}/audit_trail/`)
      .then((r) => r.json())
      .then(setAuditLog)
      .catch(() => {});
  }, [record.id]);

  async function submit() {
    setLoading(true);
    const res = await apiFetch(`/records/${record.id}/review/`, {
      method: "POST",
      body: JSON.stringify({ action, note }),
    });
    const data = await res.json();
    if (res.ok) {
      onUpdate(data);
      onClose();
    }
    setLoading(false);
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-stone-900 border border-stone-700 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-5 border-b border-stone-800 flex items-center justify-between">
          <div>
            <h3 className="text-stone-100 font-medium text-sm">{record.description}</h3>
            <p className="text-stone-500 text-xs mt-0.5">{record.activity_date}</p>
          </div>
          <button onClick={onClose} className="text-stone-600 hover:text-stone-400 text-lg">✕</button>
        </div>

        <div className="p-5 space-y-5">
          {/* Record details */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            {[
              ["Scope", `Scope ${record.scope} — ${record.scope_display}`],
              ["Category", record.category_display],
              ["Quantity", `${record.quantity} ${record.original_unit}`],
              ["Normalised", `${record.normalised_quantity} ${record.normalised_unit}`],
              ["CO2e", record.co2e_kg ? `${parseFloat(record.co2e_kg).toFixed(2)} kg` : "—"],
              ["Source row", record.source_row_id || "—"],
              ["Plant / site", record.source_plant_code || record.source_meter_id || "—"],
              ["Status", record.status_display],
            ].map(([k, v]) => (
              <div key={k}>
                <p className="text-stone-600">{k}</p>
                <p className="text-stone-300">{v}</p>
              </div>
            ))}
          </div>

          {/* Suspicious flag */}
          {record.is_suspicious && (
            <div className="bg-red-400/5 border border-red-400/20 rounded p-3 text-xs">
              <p className="text-red-400 font-medium mb-1">⚠ Suspicious row</p>
              <p className="text-stone-400">{record.suspicion_reason}</p>
            </div>
          )}

          {/* Raw data peek */}
          {record.raw_data && Object.keys(record.raw_data).length > 0 && (
            <details className="text-xs">
              <summary className="text-stone-500 cursor-pointer hover:text-stone-300">
                Raw source data
              </summary>
              <pre className="mt-2 bg-stone-950 rounded p-3 text-stone-400 overflow-x-auto text-xs leading-relaxed">
                {JSON.stringify(record.raw_data, null, 2)}
              </pre>
            </details>
          )}

          {/* Audit log */}
          {auditLog.length > 0 && (
            <div>
              <p className="text-stone-500 text-xs mb-2">Audit trail</p>
              <div className="space-y-1">
                {auditLog.map((log) => (
                  <div key={log.id} className="text-xs text-stone-500 flex gap-2">
                    <span className="text-stone-600">{log.changed_at?.slice(0, 16)}</span>
                    <span>{log.changed_by_name}</span>
                    <span className="text-stone-600">{log.action}</span>
                    <span>{log.before?.status} → {log.after?.status}</span>
                    {log.note && <span className="text-stone-400">"{log.note}"</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action */}
          {!record.locked && (
            <div className="border-t border-stone-800 pt-4 space-y-3">
              <div className="flex gap-2">
                {[
                  { val: "approve", label: "Approve", cls: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20" },
                  { val: "flag", label: "Flag", cls: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30 hover:bg-yellow-500/20" },
                  { val: "reject", label: "Reject", cls: "bg-red-500/10 text-red-400 border-red-500/30 hover:bg-red-500/20" },
                ].map((a) => (
                  <button
                    key={a.val}
                    onClick={() => setAction(a.val)}
                    className={`flex-1 py-2 rounded text-xs border transition-colors ${a.cls} ${action === a.val ? "ring-1 ring-current" : ""}`}
                  >
                    {a.label}
                  </button>
                ))}
              </div>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Optional note..."
                rows={2}
                className="w-full bg-stone-950 border border-stone-700 rounded px-3 py-2 text-xs text-stone-300 placeholder-stone-600 focus:outline-none focus:border-stone-500 resize-none"
              />
              <button
                onClick={submit}
                disabled={loading}
                className="w-full bg-stone-700 hover:bg-stone-600 disabled:opacity-50 text-stone-100 text-xs py-2 rounded transition-colors"
              >
                {loading ? "Saving..." : `Submit ${action}`}
              </button>
            </div>
          )}
          {record.locked && (
            <p className="text-stone-500 text-xs text-center border border-stone-800 rounded py-2">
              Locked — sent to auditors
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ReviewTable() {
  const { apiFetch } = useApp();
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [filters, setFilters] = useState({ status: "", scope: "", suspicious: "" });
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams({ page });
    if (filters.status) params.set("status", filters.status);
    if (filters.scope) params.set("scope", filters.scope);
    if (filters.suspicious) params.set("suspicious", "true");
    const res = await apiFetch(`/records/?${params}`);
    const data = await res.json();
    setRecords(data.results || data);
    setTotal(data.count || (data.results || data).length);
    setLoading(false);
  }, [filters, page]);

  useEffect(() => { load(); }, [load]);

  function updateRecord(updated) {
    setRecords((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-stone-200 font-bold text-lg">Review Records</h2>
          <p className="text-stone-500 text-xs">{total} records</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {[
          { key: "status", opts: [["", "All status"], ["pending", "Pending"], ["flagged", "Flagged"], ["approved", "Approved"], ["rejected", "Rejected"]] },
          { key: "scope", opts: [["", "All scopes"], ["1", "Scope 1"], ["2", "Scope 2"], ["3", "Scope 3"]] },
        ].map(({ key, opts }) => (
          <select
            key={key}
            value={filters[key]}
            onChange={(e) => { setFilters((f) => ({ ...f, [key]: e.target.value })); setPage(1); }}
            className="bg-stone-900 border border-stone-700 rounded px-2 py-1.5 text-xs text-stone-300 focus:outline-none focus:border-stone-500"
          >
            {opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        ))}
        <button
          onClick={() => { setFilters((f) => ({ ...f, suspicious: f.suspicious ? "" : "true" })); setPage(1); }}
          className={`px-3 py-1.5 rounded text-xs border transition-colors ${
            filters.suspicious
              ? "bg-red-400/10 text-red-400 border-red-400/30"
              : "bg-stone-900 text-stone-400 border-stone-700 hover:border-stone-500"
          }`}
        >
          ⚠ Suspicious only
        </button>
      </div>

      {/* Table */}
      <div className="bg-stone-900 border border-stone-800 rounded-lg overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-stone-800 text-stone-500">
              {["Date", "Description", "Scope", "Quantity", "CO2e (kg)", "Status", ""].map((h) => (
                <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-stone-600">loading...</td></tr>
            ) : records.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-stone-600">No records match your filters</td></tr>
            ) : (
              records.map((r) => (
                <tr
                  key={r.id}
                  className="border-b border-stone-800/50 hover:bg-stone-800/30 transition-colors cursor-pointer"
                  onClick={() => setSelected(r)}
                >
                  <td className="px-4 py-3 text-stone-400">{r.activity_date}</td>
                  <td className="px-4 py-3 text-stone-200 max-w-xs truncate">
                    {r.is_suspicious && <span className="text-red-400 mr-1">⚠</span>}
                    {r.description}
                  </td>
                  <td className={`px-4 py-3 font-medium ${SCOPE_COLORS[r.scope]}`}>
                    S{r.scope}
                  </td>
                  <td className="px-4 py-3 text-stone-400">
                    {parseFloat(r.normalised_quantity).toFixed(1)} {r.normalised_unit}
                  </td>
                  <td className="px-4 py-3 text-stone-300">
                    {r.co2e_kg ? parseFloat(r.co2e_kg).toFixed(1) : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded border text-xs ${STATUS_STYLES[r.status]}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-stone-600">→</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > 50 && (
        <div className="flex items-center gap-2 justify-end text-xs">
          <button
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
            className="px-3 py-1.5 bg-stone-900 border border-stone-700 rounded text-stone-400 disabled:opacity-40 hover:border-stone-500"
          >
            ← prev
          </button>
          <span className="text-stone-500">page {page}</span>
          <button
            disabled={page * 50 >= total}
            onClick={() => setPage((p) => p + 1)}
            className="px-3 py-1.5 bg-stone-900 border border-stone-700 rounded text-stone-400 disabled:opacity-40 hover:border-stone-500"
          >
            next →
          </button>
        </div>
      )}

      {selected && (
        <ReviewModal
          record={selected}
          onClose={() => setSelected(null)}
          onUpdate={updateRecord}
        />
      )}
    </div>
  );
}
