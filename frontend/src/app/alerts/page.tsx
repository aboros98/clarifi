"use client";

import { useEffect, useState } from "react";
import { Bell, CheckCircle, XCircle, AlertTriangle, Info } from "lucide-react";
import { api } from "@/lib/api";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getAlerts();
        setAlerts(data.alerts || []);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const critical = alerts.filter((a) => a.severity === "critical");
  const warnings = alerts.filter((a) => a.severity === "warning");
  const info = alerts.filter((a) => a.severity === "info");

  function AlertGroup({ title, items, color }: { title: string; items: any[]; color: string }) {
    if (items.length === 0) return null;
    return (
      <div className="mb-6">
        <h2 className={`text-sm font-semibold mb-2 ${color}`}>{title} ({items.length})</h2>
        <div className="bg-white rounded-xl border divide-y">
          {items.map((alert, i) => (
            <div key={i} className="px-4 py-3 flex items-start gap-3">
              {alert.severity === "critical" ? <XCircle size={18} className="text-red-500 shrink-0 mt-0.5" /> :
               alert.severity === "warning" ? <AlertTriangle size={18} className="text-yellow-500 shrink-0 mt-0.5" /> :
               <Info size={18} className="text-blue-500 shrink-0 mt-0.5" />}
              <div className="flex-1">
                <p className="text-sm">{alert.message}</p>
                <span className="text-xs text-gray-400">
                  {{"invoice_overdue": "Factura restanta", "milestone_overdue": "Termen depasit", "contract_expiring": "Contract expira", "cashflow_risk": "Risc cashflow", "payment_mismatch": "Plata nepotrivita"}[alert.type as string] || (alert.type || "").replace(/_/g, " ")}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-2 mb-6">
        <Bell size={24} />
        <div>
          <h1 className="text-2xl font-bold">Centru Alerte</h1>
          <p className="text-sm text-gray-500">{alerts.length} alerte active</p>
        </div>
      </div>

      {loading && <div className="text-center text-gray-400 py-8">Se încarcă...</div>}
      {error && <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">Eroare: {error}</div>}
      <AlertGroup title="Critice" items={critical} color="text-red-600" />
      <AlertGroup title="Avertismente" items={warnings} color="text-yellow-600" />
      <AlertGroup title="Informative" items={info} color="text-blue-600" />

      {!loading && alerts.length === 0 && (
        <div className="text-center py-12">
          <CheckCircle size={48} className="text-green-400 mx-auto mb-3" />
          <p className="text-gray-500">Totul e in ordine</p>
        </div>
      )}
    </div>
  );
}
