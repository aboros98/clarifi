"use client";

import { useEffect, useState } from "react";
import { Clock, Bell, Trash2, CheckCircle, XCircle, CalendarDays } from "lucide-react";
import { api } from "@/lib/api";

const TYPE_LABELS: Record<string, string> = {
  alert_eval: "Verificare alerte",
  digest: "Raport periodic",
  reminder: "Reminder",
  follow_up: "Urmarire",
  recurring: "Recurent",
  one_shot: "O singura data",
};

function friendlyType(raw: string): string {
  return TYPE_LABELS[raw] || raw.replace(/_/g, " ");
}

function friendlyDate(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleDateString("ro-RO", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function RemindersPage() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [taskData, runData] = await Promise.all([
          api.getTasks(),
          api.getRuns(10),
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
      setError(`Nu am putut sterge: ${e.message}`);
    }
  }

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Bell size={24} /> Remindere
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Remindere si verificari automate create de agent
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Active reminders */}
      <div className="space-y-3">
        {tasks.map((t) => (
          <div
            key={t.id}
            className="bg-white rounded-xl border p-4 flex items-start gap-4"
          >
            <div
              className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                t.is_active ? "bg-indigo-100" : "bg-gray-100"
              }`}
            >
              <Clock
                size={20}
                className={t.is_active ? "text-indigo-600" : "text-gray-400"}
              />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-sm">{t.title}</h3>
              <div className="flex flex-wrap items-center gap-2 mt-1">
                <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                  {friendlyType(t.task_type || t.schedule_type)}
                </span>
                {t.is_active ? (
                  <span className="text-xs text-green-600">Activ</span>
                ) : (
                  <span className="text-xs text-gray-400">Inactiv</span>
                )}
              </div>
              {t.next_run_at && (
                <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                  <CalendarDays size={12} />
                  Urmatoarea: {friendlyDate(t.next_run_at)}
                </p>
              )}
              {t.run_count > 0 && (
                <p className="text-xs text-gray-400">
                  Executat de {t.run_count} ori
                </p>
              )}
            </div>
            {t.is_active && (
              <button
                onClick={() => handleDelete(t.id)}
                className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg shrink-0"
                title="Sterge reminder"
              >
                <Trash2 size={16} />
              </button>
            )}
          </div>
        ))}
        {tasks.length === 0 && !loading && (
          <div className="bg-white rounded-xl border p-8 text-center text-gray-400 text-sm">
            Niciun reminder activ. Agentul va crea remindere automat cand
            gaseste deadline-uri in documente.
          </div>
        )}
      </div>

      {/* Recent activity */}
      {runs.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-3">
            Executii recente
          </h2>
          <div className="bg-white rounded-xl border divide-y">
            {runs.map((r) => (
              <div key={r.id} className="px-4 py-3">
                <div className="flex items-center gap-3">
                  {r.status === "success" ? (
                    <CheckCircle size={16} className="text-green-500 shrink-0" />
                  ) : (
                    <XCircle size={16} className="text-red-500 shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {r.task_title || "Agent"}
                    </p>
                    <p className="text-xs text-gray-400">
                      {friendlyDate(r.started_at)}
                      {r.duration_ms ? ` (${(r.duration_ms / 1000).toFixed(1)}s)` : ""}
                    </p>
                  </div>
                  {r.error_message && (
                    <span className="text-xs text-red-400 truncate max-w-[200px]">
                      {r.error_message}
                    </span>
                  )}
                </div>
                {r.output && (
                  <p className="text-xs text-gray-500 mt-1 pl-7 line-clamp-2">
                    {r.output}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
