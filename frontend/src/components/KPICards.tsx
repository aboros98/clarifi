"use client";

import { Wallet, TrendingUp, AlertTriangle, Receipt } from "lucide-react";

interface KPICardsProps {
  cashflow: any;
  receivables: any;
  alerts: any;
}

function fmt(n: number): string {
  return new Intl.NumberFormat("ro-RO", { maximumFractionDigits: 0 }).format(n);
}

export default function KPICards({ cashflow, receivables, alerts }: KPICardsProps) {
  const actual = cashflow?.actual;
  const expected = cashflow?.expected;

  const cards = [
    {
      title: "Bani in cont",
      value: actual ? `${fmt(actual.cash_in_bank)} lei` : "--",
      subtitle: actual?.runway_days
        ? `Ajung pentru ~${actual.runway_days} zile`
        : null,
      badge:
        actual?.bank_data_age_days && actual.bank_data_age_days > 3
          ? `Date vechi de ${actual.bank_data_age_days} zile`
          : null,
      icon: Wallet,
      bg: "bg-emerald-50 border-emerald-200",
      text: "text-emerald-800",
      iconColor: "text-emerald-600",
    },
    {
      title: "De incasat",
      value: receivables ? `${fmt(receivables.total_receivable)} lei` : "--",
      subtitle: receivables
        ? `${receivables.count} facturi${receivables.count_overdue > 0 ? ` (${receivables.count_overdue} restante)` : ""}`
        : null,
      badge:
        receivables?.count_overdue > 0
          ? `${receivables.count_overdue} facturi restante!`
          : null,
      icon: Receipt,
      bg: "bg-blue-50 border-blue-200",
      text: "text-blue-800",
      iconColor: "text-blue-600",
    },
    {
      title: "Estimare 30 zile",
      value: expected ? `${fmt(expected.net_30d)} lei` : "--",
      subtitle: actual
        ? `Cheltuieli lunare: ~${fmt(actual.monthly_burn_rate)} lei`
        : null,
      badge: null,
      icon: TrendingUp,
      bg:
        expected?.net_30d < 0
          ? "bg-red-50 border-red-200"
          : "bg-indigo-50 border-indigo-200",
      text: expected?.net_30d < 0 ? "text-red-800" : "text-indigo-800",
      iconColor: expected?.net_30d < 0 ? "text-red-600" : "text-indigo-600",
    },
    {
      title: "Alerte",
      value: alerts ? String(alerts.count) : "--",
      subtitle: alerts
        ? alerts.critical > 0
          ? `${alerts.critical} urgente`
          : "Totul e in ordine"
        : null,
      badge: alerts?.critical > 0 ? "Necesita atentie!" : null,
      icon: AlertTriangle,
      bg:
        alerts?.critical > 0
          ? "bg-red-50 border-red-200"
          : "bg-amber-50 border-amber-200",
      text: alerts?.critical > 0 ? "text-red-800" : "text-amber-800",
      iconColor: alerts?.critical > 0 ? "text-red-600" : "text-amber-600",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div key={card.title} className={`rounded-xl border p-4 sm:p-5 ${card.bg}`}>
          <div className="flex items-center justify-between mb-2">
            <span
              className={`text-xs font-medium uppercase tracking-wide ${card.text} opacity-70`}
            >
              {card.title}
            </span>
            <card.icon size={18} className={card.iconColor} />
          </div>
          <div className={`text-xl sm:text-2xl font-bold ${card.text}`}>
            {card.value}
          </div>
          {card.subtitle && (
            <div className={`text-xs mt-1 ${card.text} opacity-60`}>
              {card.subtitle}
            </div>
          )}
          {card.badge && (
            <div className="mt-2">
              <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700">
                {card.badge}
              </span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
