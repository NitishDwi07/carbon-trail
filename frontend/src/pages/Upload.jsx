import { useState, useRef } from "react";
import { useApp } from "../App";

const SOURCE_INFO = {
  sap: {
    label: "SAP Fuel & Procurement",
    scope: "Scope 1",
    hint: "MB51 / ME2M flat CSV export. Expects columns: Posting Date, Material, Quantity, Unit, Plant, Material Group.",
    sample: "Buchungsdatum,Kurztext,Menge,ME,Werk,Warengruppe,Bewegungsart,MBlNr\n05.01.2024,HSD Diesel,2500,L,1000,BF01,261,4900123456\n18.01.2024,HSD Diesel,3100,L,1000,BF01,261,4900123789",
  },
  utility: {
    label: "Utility / Electricity",
    scope: "Scope 2",
    hint: "Portal CSV export. Expects: Meter ID, Period Start, Period End, Units Consumed, Unit (kWh/MWh), Facility.",
    sample: "Meter ID,Facility,Period Start,Period End,Units Consumed,Unit,Tariff\nMTR-1001,Mumbai Plant,01/01/2024,31/01/2024,185000,kWh,HT Industrial\nDLW-2002,Delhi Warehouse,01/01/2024,31/01/2024,42000,kWh,LT Commercial",
  },
  travel: {
    label: "Corporate Travel",
    scope: "Scope 3",
    hint: "Concur / Navan CSV export. Expects: Travel Date, Category, Origin, Destination, Distance, Cabin, Employee, Nights.",
    sample: "Trip ID,Travel Date,Employee,Category,Origin,Destination,Distance,Distance Unit,Cabin,Nights\nTRP-001,2024-01-10,Ananya Sharma,Air,BOM,DEL,1148,km,Economy,\nTRP-002,2024-01-15,Rohan Mehta,Air,DEL,LHR,6730,km,Business,\nTRP-003,2024-01-20,Rohan Mehta,Hotel,,London,,,, 2",
  },
};

export default function Upload({ onDone }) {
  const { apiFetch } = useApp();
  const [sourceType, setSourceType] = useState("sap");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showSample, setShowSample] = useState(false);
  const fileRef = useRef();

  async function upload() {
    if (!file) { setError("Pick a file first"); return; }
    setLoading(true);
    setError("");
    setResult(null);

    const form = new FormData();
    form.append("source_type", sourceType);
    form.append("file", file);

    try {
      const res = await apiFetch("/upload/", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Upload failed");
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function downloadSample() {
    const info = SOURCE_INFO[sourceType];
    const blob = new Blob([info.sample], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `sample_${sourceType}.csv`;
    a.click();
  }

  const info = SOURCE_INFO[sourceType];

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-stone-200 font-bold text-lg">Upload Data</h2>
        <p className="text-stone-500 text-xs mt-0.5">Ingest from SAP, utility portal, or corporate travel platform</p>
      </div>

      {/* Source selector */}
      <div className="grid grid-cols-3 gap-2">
        {Object.entries(SOURCE_INFO).map(([key, val]) => (
          <button
            key={key}
            onClick={() => { setSourceType(key); setFile(null); setResult(null); setError(""); }}
            className={`p-3 rounded-lg border text-left transition-colors ${
              sourceType === key
                ? "bg-emerald-400/5 border-emerald-400/30 text-emerald-400"
                : "bg-stone-900 border-stone-800 text-stone-400 hover:border-stone-600"
            }`}
          >
            <p className="text-xs font-medium">{val.label}</p>
            <p className={`text-xs mt-0.5 ${sourceType === key ? "text-emerald-600" : "text-stone-600"}`}>
              {val.scope}
            </p>
          </button>
        ))}
      </div>

      {/* Format hint */}
      <div className="bg-stone-900 border border-stone-800 rounded-lg p-4 text-xs">
        <div className="flex items-start justify-between gap-2">
          <p className="text-stone-400 leading-relaxed">{info.hint}</p>
          <button
            onClick={downloadSample}
            className="shrink-0 text-emerald-500 hover:text-emerald-400 text-xs underline"
          >
            sample CSV
          </button>
        </div>
        <button
          onClick={() => setShowSample(!showSample)}
          className="text-stone-600 mt-2 hover:text-stone-400"
        >
          {showSample ? "hide" : "show"} sample format
        </button>
        {showSample && (
          <pre className="mt-2 bg-stone-950 rounded p-3 text-stone-500 overflow-x-auto text-xs leading-relaxed whitespace-pre-wrap">
            {info.sample}
          </pre>
        )}
      </div>

      {/* File input */}
      <div
        onClick={() => fileRef.current.click()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          file ? "border-emerald-500/50 bg-emerald-500/5" : "border-stone-700 hover:border-stone-500"
        }`}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".csv,.txt"
          className="hidden"
          onChange={(e) => { setFile(e.target.files[0]); setResult(null); }}
        />
        {file ? (
          <div>
            <p className="text-emerald-400 text-sm">{file.name}</p>
            <p className="text-stone-500 text-xs mt-1">{(file.size / 1024).toFixed(1)} KB</p>
          </div>
        ) : (
          <div>
            <p className="text-stone-500 text-sm">click to pick a CSV file</p>
            <p className="text-stone-700 text-xs mt-1">or drag & drop</p>
          </div>
        )}
      </div>

      {error && (
        <p className="text-red-400 text-xs bg-red-400/10 border border-red-400/20 rounded px-3 py-2">
          {error}
        </p>
      )}

      {/* Result */}
      {result && (
        <div className="bg-emerald-400/5 border border-emerald-400/20 rounded-lg p-4 text-xs space-y-2">
          <p className="text-emerald-400 font-medium">Upload complete</p>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <p className="text-stone-600">Parsed</p>
              <p className="text-stone-200 text-lg font-bold">{result.parsed}</p>
            </div>
            <div>
              <p className="text-stone-600">Errors</p>
              <p className={`text-lg font-bold ${result.errors > 0 ? "text-red-400" : "text-stone-400"}`}>
                {result.errors}
              </p>
            </div>
            <div>
              <p className="text-stone-600">Batch ID</p>
              <p className="text-stone-400 font-mono text-xs">{result.batch_id?.slice(0, 8)}...</p>
            </div>
          </div>
          {result.error_details?.length > 0 && (
            <div>
              <p className="text-stone-500 mb-1">Parse errors (first 10):</p>
              {result.error_details.map(([row, msg], i) => (
                <p key={i} className="text-red-400">row {row}: {msg}</p>
              ))}
            </div>
          )}
          <button
            onClick={onDone}
            className="mt-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded text-xs hover:bg-emerald-500/20 transition-colors"
          >
            View in Review Table →
          </button>
        </div>
      )}

      <button
        onClick={upload}
        disabled={!file || loading}
        className="px-6 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-stone-950 font-bold text-sm rounded transition-colors"
      >
        {loading ? "Uploading..." : "Upload & Ingest"}
      </button>
    </div>
  );
}
