"use client";

import { useEffect, useState } from "react";
import {
  Settings,
  Building2,
  User,
  Plus,
  Trash2,
  Check,
  Loader2,
  Star,
} from "lucide-react";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Profile editing
  const [editName, setEditName] = useState("");
  const [editRole, setEditRole] = useState("");
  const [saving, setSaving] = useState(false);

  // Add company
  const [showAddCompany, setShowAddCompany] = useState(false);
  const [newCompany, setNewCompany] = useState({
    company_name: "",
    tax_id: "",
    registration_number: "",
    city: "",
  });

  useEffect(() => {
    loadStatus();
  }, []);

  async function loadStatus() {
    try {
      const data = await api.getOnboardingStatus();
      setStatus(data);
      setEditName(data.user_name || "");
      setEditRole(data.user_role || "owner");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function flash(msg: string) {
    setSuccess(msg);
    setTimeout(() => setSuccess(null), 3000);
  }

  async function handleSaveProfile() {
    setSaving(true);
    try {
      await api.updateProfile({
        user_name: editName,
        user_role: editRole,
      });
      flash("Profil actualizat");
      loadStatus();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleAddCompany() {
    if (!newCompany.company_name.trim()) return;
    setSaving(true);
    try {
      await api.addCompany(newCompany);
      setNewCompany({ company_name: "", tax_id: "", registration_number: "", city: "" });
      setShowAddCompany(false);
      flash("Companie adaugata");
      loadStatus();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleRemoveCompany(id: string) {
    try {
      await api.removeCompany(id);
      flash("Companie stearsa");
      loadStatus();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleSwitchCompany(id: string) {
    try {
      await api.switchCompany(id);
      flash("Companie activa schimbata");
      loadStatus();
    } catch (e: any) {
      setError(e.message);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Se incarca...</div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings size={24} /> Setari
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Profilul tau si companiile gestionate
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-400">
            x
          </button>
        </div>
      )}
      {success && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-xl text-green-700 text-sm flex items-center gap-2">
          <Check size={16} /> {success}
        </div>
      )}

      {/* Profile */}
      <div className="bg-white rounded-xl border p-5 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center">
            <User size={20} className="text-indigo-600" />
          </div>
          <div>
            <h2 className="font-semibold text-sm">Profilul tau</h2>
            <p className="text-xs text-gray-500">
              Aceste informatii sunt transmise agentului AI
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Nume
            </label>
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Rol
            </label>
            <select
              value={editRole}
              onChange={(e) => setEditRole(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="owner">Proprietar / Administrator</option>
              <option value="accountant">Contabil</option>
              <option value="manager">Manager</option>
              <option value="employee">Angajat</option>
            </select>
          </div>
        </div>
        <button
          onClick={handleSaveProfile}
          disabled={saving}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 inline-flex items-center gap-2"
        >
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
          Salveaza
        </button>
      </div>

      {/* Companies */}
      <div className="bg-white rounded-xl border p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-yellow-100 flex items-center justify-center">
              <Building2 size={20} className="text-yellow-600" />
            </div>
            <div>
              <h2 className="font-semibold text-sm">Companiile tale</h2>
              <p className="text-xs text-gray-500">
                Agentul vede datele companiei active
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowAddCompany(!showAddCompany)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50"
          >
            <Plus size={14} /> Adauga
          </button>
        </div>

        {/* Add company form */}
        {showAddCompany && (
          <div className="border rounded-xl p-4 space-y-3 bg-gray-50">
            <h3 className="text-sm font-semibold text-gray-600">
              Companie noua
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="sm:col-span-2">
                <label className="block text-xs text-gray-500 mb-1">
                  Denumire *
                </label>
                <input
                  type="text"
                  value={newCompany.company_name}
                  onChange={(e) =>
                    setNewCompany({ ...newCompany, company_name: e.target.value })
                  }
                  placeholder="SC Exemplu SRL"
                  className="w-full px-3 py-2 rounded-lg border text-sm bg-white"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  CUI / CIF
                </label>
                <input
                  type="text"
                  value={newCompany.tax_id}
                  onChange={(e) =>
                    setNewCompany({ ...newCompany, tax_id: e.target.value })
                  }
                  placeholder="RO12345678"
                  className="w-full px-3 py-2 rounded-lg border text-sm bg-white"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Nr. Reg. Com.
                </label>
                <input
                  type="text"
                  value={newCompany.registration_number}
                  onChange={(e) =>
                    setNewCompany({
                      ...newCompany,
                      registration_number: e.target.value,
                    })
                  }
                  placeholder="J40/1234/2020"
                  className="w-full px-3 py-2 rounded-lg border text-sm bg-white"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Oras</label>
                <input
                  type="text"
                  value={newCompany.city}
                  onChange={(e) =>
                    setNewCompany({ ...newCompany, city: e.target.value })
                  }
                  placeholder="Bucuresti"
                  className="w-full px-3 py-2 rounded-lg border text-sm bg-white"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleAddCompany}
                disabled={saving || !newCompany.company_name.trim()}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
              >
                Adauga companie
              </button>
              <button
                onClick={() => setShowAddCompany(false)}
                className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
              >
                Anuleaza
              </button>
            </div>
          </div>
        )}

        {/* Company list */}
        <div className="space-y-2">
          {status?.companies?.map((c: any) => (
            <div
              key={c.id}
              className={`border rounded-xl p-4 flex items-center gap-3 ${
                c.active ? "border-indigo-200 bg-indigo-50/50" : ""
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium">{c.name}</p>
                  {c.active && (
                    <span className="text-xs px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded">
                      Activa
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-0.5">
                  {c.tax_id && (
                    <span className="text-xs text-gray-400">
                      CUI: {c.tax_id}
                    </span>
                  )}
                  {c.trade_name && c.trade_name !== c.name && (
                    <span className="text-xs text-gray-400">
                      {c.trade_name}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {!c.active && (
                  <button
                    onClick={() => handleSwitchCompany(c.id)}
                    className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg"
                    title="Seteaza ca activa"
                  >
                    <Star size={16} />
                  </button>
                )}
                <button
                  onClick={() => handleRemoveCompany(c.id)}
                  className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg"
                  title="Sterge"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
          {(!status?.companies || status.companies.length === 0) && (
            <p className="text-sm text-gray-400 text-center py-4">
              Nicio companie configurata
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
