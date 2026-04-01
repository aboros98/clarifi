"use client";

import Link from "next/link";
import { BarChart3, FileText, Shield, MessageSquare } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 max-w-5xl mx-auto">
        <h1 className="text-xl font-bold text-gray-900">Clarifi</h1>
        <Link
          href="/auth/login"
          className="px-5 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          Intra in cont
        </Link>
      </header>

      {/* Hero */}
      <section className="text-center px-6 pt-16 pb-12 max-w-3xl mx-auto">
        <h2 className="text-4xl sm:text-5xl font-bold text-gray-900 leading-tight">
          Asistentul tau financiar
          <span className="text-indigo-600"> AI</span>
        </h2>
        <p className="text-lg text-gray-500 mt-4 max-w-xl mx-auto">
          Clarifi iti analizeaza facturile, contractele si extrasele bancare.
          Iti arata exact unde esti financiar si ce trebuie sa faci.
        </p>
        <div className="mt-8 flex gap-3 justify-center">
          <Link
            href="/auth/login"
            className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors"
          >
            Incepe gratuit
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-12 max-w-4xl mx-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="bg-white rounded-2xl border p-6">
            <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center mb-4">
              <FileText size={20} className="text-indigo-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-1">
              Extragere automata
            </h3>
            <p className="text-sm text-gray-500">
              Incarci facturi, contracte sau extrase bancare. AI-ul extrage
              datele automat si le organizeaza.
            </p>
          </div>

          <div className="bg-white rounded-2xl border p-6">
            <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center mb-4">
              <BarChart3 size={20} className="text-green-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-1">
              Cashflow in timp real
            </h3>
            <p className="text-sm text-gray-500">
              Vezi cat ai in cont, cat ai de incasat, cat ai de platit.
              Proiectii pe 30/60/90 zile.
            </p>
          </div>

          <div className="bg-white rounded-2xl border p-6">
            <div className="w-10 h-10 bg-yellow-100 rounded-xl flex items-center justify-center mb-4">
              <Shield size={20} className="text-yellow-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-1">
              Alerte si riscuri
            </h3>
            <p className="text-sm text-gray-500">
              Facturi restante, milestone-uri depasiste, contracte care expira.
              Le vezi inainte sa devina probleme.
            </p>
          </div>

          <div className="bg-white rounded-2xl border p-6">
            <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center mb-4">
              <MessageSquare size={20} className="text-purple-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-1">
              Chat natural in romana
            </h3>
            <p className="text-sm text-gray-500">
              Intrebi &quot;Cati bani am?&quot; si primesti raspuns cu date reale.
              Ca un coleg care se pricepe la finante.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="text-center py-8 text-xs text-gray-400">
        Clarifi v0.1.0
      </footer>
    </div>
  );
}
