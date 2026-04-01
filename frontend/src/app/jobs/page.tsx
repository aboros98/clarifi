"use client";

import { useEffect, useState } from "react";
import { Clock, Play, Trash2, CheckCircle, XCircle, Pause } from "lucide-react";
import { api } from "@/lib/api";

export default function JobsPage() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [taskData, runData] = await Promise.all([
          api.getTasks(),
          api.getRuns(20),
        ]);
        setTasks(taskData.tasks || []);
        setRuns(runData.runs || []);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleDelete(id: string) {
    try {
      await api.deleteTask(id);
      setTasks((prev) => prev.filter((t) => t.id !== id));
    } catch (e: any) {
      setError(`Nu am putut șterge: ${e.message}`);
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">Jobs & Scheduler</h1>
      <p className="text-sm text-gray-500 mb-6">
        Task-uri programate si istoricul executiilor
      </p>

      {error && <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>}

      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <Clock size={20} /> Task-uri Programate
        </h2>
        <div className="bg-white rounded-xl border overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Titlu</th>
                <th className="px-4 py-3 text-left">Tip</th>
                <th className="px-4 py-3 text-left">Cron</th>
                <th className="px-4 py-3 text-left">Urmatoarea executie</th>
                <th className="px-4 py-3 text-left">Executii</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {tasks.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{t.title}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full text-xs bg-gray-100">
                      {t.schedule_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">
                    {t.cron_expression || "-"}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {t.next_run_at
                      ? new Date(t.next_run_at).toLocaleString("ro-RO")
                      : "-"}
                  </td>
                  <td className="px-4 py-3">{t.run_count}</td>
                  <td className="px-4 py-3">
                    {t.is_active ? (
                      <span className="flex items-center gap-1 text-green-600 text-xs">
                        <Play size={12} /> Activ
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-gray-400 text-xs">
                        <Pause size={12} /> Inactiv
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {t.is_active && (
                      <button
                        onClick={() => handleDelete(t.id)}
                        className="text-red-400 hover:text-red-600"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {tasks.length === 0 && !loading && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                    Niciun task programat
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Run History */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Istoric Executii</h2>
        <div className="bg-white rounded-xl border overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Data</th>
                <th className="px-4 py-3 text-left">Task</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Durata</th>
                <th className="px-4 py-3 text-left">Eroare</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {runs.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-xs">
                    {new Date(r.started_at).toLocaleString("ro-RO")}
                  </td>
                  <td className="px-4 py-3">{r.task_id.slice(0, 8)}...</td>
                  <td className="px-4 py-3">
                    {r.status === "success" ? (
                      <CheckCircle size={16} className="text-green-500" />
                    ) : r.status === "failed" ? (
                      <XCircle size={16} className="text-red-500" />
                    ) : (
                      <Clock size={16} className="text-yellow-500" />
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {r.duration_ms ? `${r.duration_ms}ms` : "-"}
                  </td>
                  <td className="px-4 py-3 text-xs text-red-500 truncate max-w-xs">
                    {r.error_message || "-"}
                  </td>
                </tr>
              ))}
              {runs.length === 0 && !loading && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                    Nicio executie inregistrata
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
