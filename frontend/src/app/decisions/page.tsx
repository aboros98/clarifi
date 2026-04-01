"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  Search,
  FileText,
  Calculator,
  Bell,
  Database,
  ChevronDown,
  ChevronUp,
  Clock,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";
import { api } from "@/lib/api";

const TOOL_ICONS: Record<string, typeof Search> = {
  query_cashflow: Calculator,
  query_receivables: Calculator,
  query_profitability: Calculator,
  query_invoices: FileText,
  query_contracts: FileText,
  query_milestones: Clock,
  query_alerts: Bell,
  query_transactions: Database,
  extract_fields: FileText,
  calculate: Calculator,
  save_extracted_data: Database,
  ingest_document: FileText,
  score_client_risk: AlertTriangle,
  detect_unissued_invoices: Search,
  create_reminder: Clock,
  confirm_data: CheckCircle,
};

const TOOL_LABELS: Record<string, string> = {
  query_cashflow: "A verificat cashflow-ul",
  query_receivables: "A verificat creantele",
  query_profitability: "A verificat profitabilitatea",
  query_invoices: "A cautat facturi",
  query_contracts: "A verificat contracte",
  query_milestones: "A verificat milestone-uri",
  query_alerts: "A verificat alerte",
  query_transactions: "A cautat tranzactii bancare",
  extract_fields: "A extras date din document",
  save_extracted_data: "A salvat date extrase",
  ingest_document: "A procesat un document",
  calculate: "A facut un calcul",
  score_client_risk: "A evaluat riscul unui client",
  detect_unissued_invoices: "A cautat facturi neemise",
  project_cashflow_daily: "A proiectat cashflow zilnic",
  create_reminder: "A creat un reminder",
  confirm_data: "A confirmat date",
  correct_data: "A corectat date",
  mark_invoice_paid: "A marcat factura ca platita",
  run_payment_matching: "A potrivit plati cu facturi",
  list_reminders: "A verificat reminderele",
  cancel_reminder: "A anulat un reminder",
  read_document_content: "A citit un document",
  create_folder: "A creat un folder",
  move_file: "A mutat un fisier",
  write_trace: "A scris o analiza pe folder",
};

function friendlyAction(toolName: string): string {
  return TOOL_LABELS[toolName] || toolName.replace(/_/g, " ");
}

function summarizeOutput(output: any): string | null {
  if (!output || typeof output !== "object") return null;

  // Cashflow
  if (output.actual?.cash_in_bank != null) {
    const cash = Number(output.actual.cash_in_bank).toLocaleString("ro-RO");
    const recv = output.expected?.total_receivable_30d;
    let s = `Sold: ${cash} lei`;
    if (recv) s += ` | De incasat: ${Number(recv).toLocaleString("ro-RO")} lei`;
    return s;
  }
  // Calculator
  if (output.expression && output.result != null) {
    return `${output.expression} = ${output.result}`;
  }
  // Alerts
  if (output.total != null && output.alerts) {
    return `${output.total} alerte (${output.critical || 0} critice)`;
  }
  // Extraction
  if (output._meta?.avg_confidence != null) {
    const type = output._meta.document_type || "document";
    return `${type} extras cu ${Math.round(output._meta.avg_confidence * 100)}% incredere`;
  }
  // Receivables
  if (output.total_outstanding != null) {
    return `Total restant: ${Number(output.total_outstanding).toLocaleString("ro-RO")} lei`;
  }
  // Error
  if (output.error) {
    return `Eroare: ${output.error}`;
  }
  // Status messages
  if (output.status) {
    return output.message || output.status;
  }
  return null;
}

function groupBySession(decisions: any[]): { date: string; items: any[] }[] {
  const groups: { date: string; items: any[] }[] = [];
  let current: { date: string; items: any[] } | null = null;

  for (const d of decisions) {
    const date = new Date(d.timestamp).toLocaleDateString("ro-RO", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
    if (!current || current.date !== date) {
      current = { date, items: [] };
      groups.push(current);
    }
    current.items.push(d);
  }

  return groups;
}

export default function ActivityPage() {
  const [decisions, setDecisions] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Only show decisions that affect data — not internal lookups
  const DECISION_TOOLS = new Set([
    "save_extracted_data", "ingest_document", "extract_fields",
    "confirm_data", "correct_data", "mark_invoice_paid",
    "create_reminder", "cancel_reminder", "mark_stale",
    "create_folder", "move_file", "write_trace",
    "run_payment_matching", "confirm_match",
    "calculate",
  ]);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getDecisions(200, 0);
        const all = data.decisions || [];
        const filtered = all.filter(
          (d: any) => DECISION_TOOLS.has(d.tool_name),
        );
        setDecisions(filtered);
        setTotal(filtered.length);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const groups = groupBySession(decisions);

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Activity size={24} /> Activitate Agent
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Istoricul actiunilor agentului — {total} actiuni
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      {groups.map((group) => (
        <div key={group.date}>
          <h2 className="text-xs font-semibold text-gray-400 uppercase mb-2 px-1">
            {group.date}
          </h2>
          <div className="space-y-1.5">
            {group.items.map((d) => {
              const Icon = TOOL_ICONS[d.tool_name] || Search;
              const summary = summarizeOutput(d.tool_output);
              const isExpanded = expanded === d.id;

              return (
                <div key={d.id} className="bg-white rounded-xl border">
                  <div
                    className="px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-gray-50 transition-colors"
                    onClick={() => setExpanded(isExpanded ? null : d.id)}
                  >
                    <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center shrink-0">
                      <Icon size={16} className="text-indigo-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">
                        {friendlyAction(d.tool_name || d.decision_type)}
                      </p>
                      {summary && (
                        <p className="text-xs text-gray-500 truncate mt-0.5">
                          {summary}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {d.duration_ms != null && (
                        <span className="text-xs text-gray-400">
                          {d.duration_ms < 1000
                            ? `${d.duration_ms}ms`
                            : `${(d.duration_ms / 1000).toFixed(1)}s`}
                        </span>
                      )}
                      <span className="text-xs text-gray-400">
                        {new Date(d.timestamp).toLocaleTimeString("ro-RO", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                      {isExpanded ? (
                        <ChevronUp size={14} className="text-gray-400" />
                      ) : (
                        <ChevronDown size={14} className="text-gray-400" />
                      )}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="px-4 py-3 border-t bg-gray-50 text-xs space-y-2">
                      {d.tool_input &&
                        Object.keys(d.tool_input).length > 0 && (
                          <div>
                            <span className="font-semibold text-gray-500">
                              Parametri:
                            </span>
                            <div className="mt-1 p-2 bg-white rounded-lg border text-gray-600">
                              {Object.entries(d.tool_input).map(
                                ([k, v]) => (
                                  <div key={k}>
                                    <span className="text-gray-400">{k}:</span>{" "}
                                    {String(v)}
                                  </div>
                                )
                              )}
                            </div>
                          </div>
                        )}
                      {summary && (
                        <div>
                          <span className="font-semibold text-gray-500">
                            Rezultat:
                          </span>
                          <p className="mt-1 text-gray-600">{summary}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {decisions.length === 0 && !loading && (
        <div className="bg-white rounded-xl border p-12 text-center">
          <Activity size={32} className="text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-400">
            Nicio activitate inca. Incepe o conversatie cu agentul sau incarca
            un document.
          </p>
        </div>
      )}
    </div>
  );
}
