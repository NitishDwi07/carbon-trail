import { useState, useEffect } from "react";
import { useApp } from "../App";

export default function Batches() {
  const { apiFetch } = useApp();
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/batches/")
      .then((r) => r.json())
      .then((d) => setBatches(d.results || d))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-stone-500 text-sm">loading...</p>;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-stone-200 font-bold text-lg">Ingestion Batches</h2>
        <p className="text-stone-500 text-xs">{batches.length} batches</p>
      </div>

      <div className="bg-stone-900 border border-stone-800 rounded-lg overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-stone-800 text-stone-500">
              {["Filename", "Source", "Uploaded", "Rows", "Errors", "Status"].map((h) => (
                <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {batches.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-stone-600">No batches yet</td></tr>
            ) : (
              batches.map((b) => (
                <tr key={b.id} className="border-b border-stone-800/50">
                  <td className="px-4 py-3 text-stone-300 max-w-xs truncate">{b.original_filename || "—"}</td>
                  <td className="px-4 py-3 text-stone-400">{b.source_type_display}</td>
                  <td className="px-4 py-3 text-stone-500">{b.uploaded_at?.slice(0, 16)}</td>
                  <td className="px-4 py-3 text-stone-300">{b.row_count}</td>
                  <td className={`px-4 py-3 ${b.error_count > 0 ? "text-red-400" : "text-stone-600"}`}>
                    {b.error_count}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded border text-xs ${
                      b.status === "done" ? "bg-emerald-400/10 text-emerald-400 border-emerald-400/20" :
                      b.status === "failed" ? "bg-red-400/10 text-red-400 border-red-400/20" :
                      "bg-yellow-400/10 text-yellow-400 border-yellow-400/20"
                    }`}>
                      {b.status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
