"use client";

import { useEffect, useState } from "react";
import KPICards from "@/components/KPICards";
import { api } from "@/lib/api";
import {
  ArrowRight,
  Clock,
  MessageSquare,
  Upload,
  Bell,
} from "lucide-react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";

export default function DashboardPage() {
  const [kpis, setKpis] = useState<any>(null);
  const [alerts, setAlerts] = useState<any>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [userName, setUserName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [kpiData, alertData, taskData, status] = await Promise.all([
          api.getKPIs(),
          api.getAlerts(),
          api.getTasks(true).catch(() => ({ tasks: [] })),
          api.getOnboardingStatus().catch(() => ({})),
        ]);
        setKpis(kpiData);
        setAlerts(alertData);
        setTasks(taskData.tasks?.slice(0, 5) || []);
        setUserName(status.user_name || "");
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? "Buna dimineata" : hour < 18 ? "Buna ziua" : "Buna seara";

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {greeting}
          {userName ? `, ${userName.split(" ")[0]}` : ""}
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Iata cum stai cu finanțele azi
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* KPI Cards */}
      <KPICards
        cashflow={kpis?.cashflow || null}
        receivables={kpis?.receivables || null}
        alerts={alerts || null}
      />

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-2">
        <Link
          href="/chat"
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <MessageSquare size={16} /> Intreaba agentul
        </Link>
        <Link
          href="/folders"
          className="flex items-center gap-2 px-4 py-2.5 bg-white border text-gray-700 rounded-xl text-sm hover:bg-gray-50 transition-colors"
        >
          <Upload size={16} /> Incarca documente
        </Link>
        <Link
          href="/alerts"
          className="flex items-center gap-2 px-4 py-2.5 bg-white border text-gray-700 rounded-xl text-sm hover:bg-gray-50 transition-colors"
        >
          <Bell size={16} /> Vezi alerte
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Alerts */}
        <div className="bg-white rounded-xl border">
          <div className="flex items-center justify-between px-5 py-4 border-b">
            <h2 className="font-semibold text-sm">Alerte</h2>
            <Link
              href="/alerts"
              className="text-xs text-indigo-600 hover:underline flex items-center gap-1"
            >
              Vezi tot <ArrowRight size={12} />
            </Link>
          </div>
          {alerts?.alerts?.length > 0 ? (
            <div className="divide-y">
              {alerts.alerts.slice(0, 5).map((alert: any, i: number) => (
                <div key={i} className="px-5 py-3 flex items-start gap-3">
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 mt-1.5 ${
                      alert.severity === "critical"
                        ? "bg-red-500"
                        : alert.severity === "warning"
                          ? "bg-yellow-500"
                          : "bg-blue-500"
                    }`}
                  />
                  <span className="text-sm text-gray-700">{alert.message}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="px-5 py-8 text-center text-sm text-gray-400">
              Nicio alerta activa
            </div>
          )}
        </div>

        {/* Reminders */}
        <div className="bg-white rounded-xl border">
          <div className="flex items-center justify-between px-5 py-4 border-b">
            <h2 className="font-semibold text-sm">Remindere</h2>
            <Link
              href="/jobs"
              className="text-xs text-indigo-600 hover:underline flex items-center gap-1"
            >
              Vezi tot <ArrowRight size={12} />
            </Link>
          </div>
          {tasks.length > 0 ? (
            <div className="divide-y">
              {tasks.map((t: any) => (
                <div key={t.id} className="px-5 py-3 flex items-center gap-3">
                  <Clock size={14} className="text-gray-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{t.title}</p>
                    <p className="text-xs text-gray-400">
                      {t.next_run_at
                        ? new Date(t.next_run_at).toLocaleDateString("ro-RO", {
                            day: "numeric",
                            month: "short",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "--"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="px-5 py-8 text-center text-sm text-gray-400">
              Niciun reminder
            </div>
          )}
        </div>
      </div>

      {/* Agent Activity */}
      {kpis?.recent_activity?.length > 0 && (
        <div className="bg-white rounded-xl border">
          <div className="px-5 py-4 border-b">
            <h2 className="font-semibold text-sm">Ce a facut agentul</h2>
          </div>
          <div className="divide-y">
            {kpis.recent_activity.map((a: any, i: number) => (
              <div key={i} className="px-5 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      a.status === "success" ? "bg-green-500" : "bg-red-500"
                    }`}
                  />
                  <span className="text-sm font-medium">{a.title}</span>
                  <span className="text-xs text-gray-400">
                    {new Date(a.timestamp).toLocaleDateString("ro-RO", {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
                <div className="text-sm text-gray-600 pl-4 prose prose-sm prose-gray max-w-none">
                  <ReactMarkdown>{a.summary}</ReactMarkdown>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
