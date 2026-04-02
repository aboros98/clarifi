"use client";

import {
  Wallet,
  ArrowDownLeft,
  ArrowUpRight,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";

interface KPICardsProps {
  cashflow: any;
  receivables: any;
  alerts: any;
}

function fmt(n: number | null | undefined): string {
  if (n == null) return "--";
  return new Intl.NumberFormat("ro-RO", { maximumFractionDigits: 0 }).format(n);
}

export default function KPICards({
  cashflow,
  receivables,
  alerts,
}: KPICardsProps) {
  const actual = cashflow?.actual;
  const expected = cashflow?.expected;

  return (
    <div className="grid grid-cols-2 xl:grid-cols-5 gap-3 sm:gap-4">
      {/* Cash in cont */}
      <div className="rounded-xl border bg-white p-4 sm:p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-100 flex items-center justify-center">
            <Wallet size={18} className="text-emerald-600" />
          </div>
          {actual?.bank_data_age_days > 3 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">
              {actual.bank_data_age_days}z vechi
            </span>
          )}
        </div>
        <p className="text-2xl sm:text-3xl font-bold text-gray-900">
          {fmt(actual?.cash_in_bank)}
          <span className="text-sm font-normal text-gray-400 ml-1">lei</span>
        </p>
        <p className="text-xs text-gray-500 mt-1">Bani in cont</p>
        {actual?.runway_days != null && (
          <p className="text-xs text-gray-400 mt-0.5">
            ~{actual.runway_days} zile
          </p>
        )}
      </div>

      {/* De incasat */}
      <div className="rounded-xl border bg-white p-4 sm:p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="w-9 h-9 rounded-lg bg-blue-100 flex items-center justify-center">
            <ArrowDownLeft size={18} className="text-blue-600" />
          </div>
          {receivables?.count_overdue > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-100 text-red-700">
              {receivables.count_overdue} restante
            </span>
          )}
        </div>
        <p className="text-2xl sm:text-3xl font-bold text-gray-900">
          {fmt(receivables?.total_receivable)}
          <span className="text-sm font-normal text-gray-400 ml-1">lei</span>
        </p>
        <p className="text-xs text-gray-500 mt-1">De incasat</p>
        {receivables?.count > 0 && (
          <p className="text-xs text-gray-400 mt-0.5">
            {receivables.count} facturi
          </p>
        )}
      </div>

      {/* De platit */}
      <div className="rounded-xl border bg-white p-4 sm:p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="w-9 h-9 rounded-lg bg-orange-100 flex items-center justify-center">
            <ArrowUpRight size={18} className="text-orange-600" />
          </div>
        </div>
        <p className="text-2xl sm:text-3xl font-bold text-gray-900">
          {fmt(expected?.outflows_30d)}
          <span className="text-sm font-normal text-gray-400 ml-1">lei</span>
        </p>
        <p className="text-xs text-gray-500 mt-1">De platit (30 zile)</p>
        {actual?.monthly_burn_rate > 0 && (
          <p className="text-xs text-gray-400 mt-0.5">
            ~{fmt(actual.monthly_burn_rate)} lei/luna
          </p>
        )}
      </div>

      {/* Estimare 30 zile */}
      <div
        className={`rounded-xl border p-4 sm:p-5 ${
          expected?.net_30d < 0 ? "bg-red-50 border-red-200" : "bg-white"
        }`}
      >
        <div className="flex items-center justify-between mb-3">
          <div
            className={`w-9 h-9 rounded-lg flex items-center justify-center ${
              expected?.net_30d < 0 ? "bg-red-100" : "bg-indigo-100"
            }`}
          >
            <TrendingUp
              size={18}
              className={expected?.net_30d < 0 ? "text-red-600" : "text-indigo-600"}
            />
          </div>
        </div>
        <p
          className={`text-2xl sm:text-3xl font-bold ${
            expected?.net_30d < 0 ? "text-red-700" : "text-gray-900"
          }`}
        >
          {expected?.net_30d < 0 ? "-" : "+"}
          {fmt(Math.abs(expected?.net_30d || 0))}
          <span className="text-sm font-normal text-gray-400 ml-1">lei</span>
        </p>
        <p className="text-xs text-gray-500 mt-1">Estimare 30 zile</p>
      </div>

      {/* Alerte */}
      <div
        className={`rounded-xl border p-4 sm:p-5 ${
          alerts?.critical > 0 ? "bg-red-50 border-red-200" : "bg-white"
        }`}
      >
        <div className="flex items-center justify-between mb-3">
          <div
            className={`w-9 h-9 rounded-lg flex items-center justify-center ${
              alerts?.critical > 0 ? "bg-red-100" : "bg-gray-100"
            }`}
          >
            <AlertTriangle
              size={18}
              className={alerts?.critical > 0 ? "text-red-600" : "text-gray-400"}
            />
          </div>
        </div>
        <p className="text-2xl sm:text-3xl font-bold text-gray-900">
          {alerts?.count ?? "--"}
        </p>
        <p className="text-xs text-gray-500 mt-1">
          {alerts?.critical > 0
            ? `${alerts.critical} urgente`
            : "Alerte"}
        </p>
      </div>
    </div>
  );
}
