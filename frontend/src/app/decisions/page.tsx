"use client";

import { useEffect, useState } from "react";
import { ScrollText, ChevronDown, ChevronUp } from "lucide-react";
import { api } from "@/lib/api";

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getDecisions(50, 0);
        setDecisions(data.decisions || []);
        setTotal(data.total || 0);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-1 flex items-center gap-2">
        <ScrollText size={24} /> Decision Log
      </h1>
      <p className="text-sm text-gray-500 mb-6">
        Toate deciziile si actiunile agentului ({total} total)
      </p>

      {error && <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">Eroare: {error}</div>}

      <div className="bg-white rounded-xl border divide-y overflow-x-auto">
        {decisions.map((d) => (
          <div key={d.id}>
            <div
              className="px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-gray-50"
              onClick={() => setExpanded(expanded === d.id ? null : d.id)}
            >
              <span
                className={`w-2 h-2 rounded-full shrink-0 ${
                  d.decision_type === "tool_call"
                    ? "bg-indigo-500"
                    : d.decision_type === "alert_generated"
                    ? "bg-yellow-500"
                    : d.decision_type === "data_saved"
                    ? "bg-green-500"
                    : "bg-gray-400"
                }`}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">
                    {d.tool_name || d.decision_type}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                    {d.decision_type}
                  </span>
                </div>
                {d.reasoning && (
                  <p className="text-xs text-gray-500 truncate">{d.reasoning}</p>
                )}
              </div>
              <span className="text-xs text-gray-400 shrink-0">
                {new Date(d.timestamp).toLocaleString("ro-RO")}
              </span>
              {expanded === d.id ? (
                <ChevronUp size={16} className="text-gray-400" />
              ) : (
                <ChevronDown size={16} className="text-gray-400" />
              )}
            </div>
            {expanded === d.id && (
              <div className="px-4 py-3 bg-gray-50 text-xs">
                {d.tool_input && (
                  <div className="mb-2">
                    <span className="font-semibold">Input:</span>
                    <pre className="mt-1 p-2 bg-white rounded border overflow-x-auto">
                      {JSON.stringify(d.tool_input, null, 2)}
                    </pre>
                  </div>
                )}
                {d.tool_output && (
                  <div>
                    <span className="font-semibold">Output:</span>
                    <pre className="mt-1 p-2 bg-white rounded border overflow-x-auto max-h-60 overflow-y-auto">
                      {JSON.stringify(d.tool_output, null, 2)}
                    </pre>
                  </div>
                )}
                {d.duration_ms && (
                  <div className="mt-2 text-gray-400">
                    Durata: {d.duration_ms}ms
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {decisions.length === 0 && !loading && (
          <div className="px-4 py-8 text-center text-gray-400">
            Nicio decizie inregistrata inca
          </div>
        )}
      </div>
    </div>
  );
}
