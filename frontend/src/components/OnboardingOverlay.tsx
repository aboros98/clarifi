"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Building2, Plus, Trash2, Loader2, ArrowRight } from "lucide-react";

interface CompanyForm {
  company_name: string;
  trade_name: string;
  tax_id: string;
  registration_number: string;
  city: string;
  bank_accounts: { iban: string; bank_name: string; currency: string }[];
}

function emptyCompany(): CompanyForm {
  return {
    company_name: "",
    trade_name: "",
    tax_id: "",
    registration_number: "",
    city: "",
    bank_accounts: [{ iban: "", bank_name: "", currency: "RON" }],
  };
}

export default function OnboardingOverlay({
  onComplete,
}: {
  onComplete: () => void;
}) {
  const [step, setStep] = useState(0); // 0=welcome, 1=user, 2=companies, 3=done
  const [userName, setUserName] = useState("");
  const [userRole, setUserRole] = useState("owner");
  const [companies, setCompanies] = useState<CompanyForm[]>([emptyCompany()]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateCompany(idx: number, field: string, value: string) {
    setCompanies((prev) =>
      prev.map((c, i) => (i === idx ? { ...c, [field]: value } : c))
    );
  }

  function updateBankAccount(
    compIdx: number,
    field: string,
    value: string
  ) {
    setCompanies((prev) =>
      prev.map((c, i) => {
        if (i !== compIdx) return c;
        const accounts = [...c.bank_accounts];
        accounts[0] = { ...accounts[0], [field]: value };
        return { ...c, bank_accounts: accounts };
      })
    );
  }

  function addCompany() {
    setCompanies((prev) => [...prev, emptyCompany()]);
  }

  function removeCompany(idx: number) {
    if (companies.length <= 1) return;
    setCompanies((prev) => prev.filter((_, i) => i !== idx));
  }

  async function handleSubmit() {
    setError(null);
    setLoading(true);
    try {
      const cleaned = companies
        .filter((c) => c.company_name.trim())
        .map((c) => ({
          ...c,
          bank_accounts: c.bank_accounts.filter((ba) => ba.iban.trim()),
        }));

      if (cleaned.length === 0) {
        setError("Adauga cel putin o companie.");
        setLoading(false);
        return;
      }

      await api.onboard({
        companies: cleaned,
        user_name: userName.trim(),
        user_role: userRole,
      });
      setStep(3);
      setTimeout(onComplete, 1500);
    } catch (e: any) {
      setError(e.message || "Eroare la salvare");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Step 0: Welcome */}
        {step === 0 && (
          <div className="p-8 text-center space-y-6">
            <div className="w-16 h-16 mx-auto bg-indigo-100 rounded-2xl flex items-center justify-center">
              <Building2 size={32} className="text-indigo-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Bine ai venit in Clarifi!
              </h1>
              <p className="text-gray-500 mt-2">
                Asistentul tau financiar AI. Hai sa configuram contul in
                cateva secunde.
              </p>
            </div>
            <button
              onClick={() => setStep(1)}
              className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors inline-flex items-center gap-2"
            >
              Sa incepem <ArrowRight size={18} />
            </button>
          </div>
        )}

        {/* Step 1: User info */}
        {step === 1 && (
          <div className="p-8 space-y-6">
            <div>
              <h2 className="text-xl font-bold text-gray-900">Despre tine</h2>
              <p className="text-sm text-gray-500 mt-1">
                Cum sa te stim?
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Numele tau *
                </label>
                <input
                  type="text"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  placeholder="ex: Ion Popescu"
                  className="w-full px-4 py-2.5 rounded-xl border text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Rolul tau
                </label>
                <select
                  value={userRole}
                  onChange={(e) => setUserRole(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                >
                  <option value="owner">Proprietar / Administrator</option>
                  <option value="accountant">Contabil</option>
                  <option value="manager">Manager</option>
                  <option value="employee">Angajat</option>
                </select>
              </div>
            </div>

            <div className="flex justify-between pt-2">
              <button
                onClick={() => setStep(0)}
                className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
              >
                Inapoi
              </button>
              <button
                onClick={() => setStep(2)}
                disabled={!userName.trim()}
                className="px-6 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 inline-flex items-center gap-2"
              >
                Continua <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Companies */}
        {step === 2 && (
          <div className="p-8 space-y-6">
            <div>
              <h2 className="text-xl font-bold text-gray-900">
                Companiile tale
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                Poti adauga una sau mai multe companii.
              </p>
            </div>

            <div className="space-y-6">
              {companies.map((comp, idx) => (
                <div
                  key={idx}
                  className="border rounded-xl p-4 space-y-3 relative"
                >
                  {companies.length > 1 && (
                    <button
                      onClick={() => removeCompany(idx)}
                      className="absolute top-3 right-3 p-1.5 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50"
                    >
                      <Trash2 size={16} />
                    </button>
                  )}

                  <h3 className="text-sm font-semibold text-gray-600">
                    Compania {companies.length > 1 ? idx + 1 : ""}
                  </h3>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="sm:col-span-2">
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        Denumire oficiala *
                      </label>
                      <input
                        type="text"
                        value={comp.company_name}
                        onChange={(e) =>
                          updateCompany(idx, "company_name", e.target.value)
                        }
                        placeholder="SC Exemplu SRL"
                        className="w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        CUI / CIF
                      </label>
                      <input
                        type="text"
                        value={comp.tax_id}
                        onChange={(e) =>
                          updateCompany(idx, "tax_id", e.target.value)
                        }
                        placeholder="RO12345678"
                        className="w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        Nr. Reg. Com.
                      </label>
                      <input
                        type="text"
                        value={comp.registration_number}
                        onChange={(e) =>
                          updateCompany(
                            idx,
                            "registration_number",
                            e.target.value
                          )
                        }
                        placeholder="J40/1234/2020"
                        className="w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        Oras
                      </label>
                      <input
                        type="text"
                        value={comp.city}
                        onChange={(e) =>
                          updateCompany(idx, "city", e.target.value)
                        }
                        placeholder="București"
                        className="w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        IBAN
                      </label>
                      <input
                        type="text"
                        value={comp.bank_accounts[0]?.iban || ""}
                        onChange={(e) =>
                          updateBankAccount(idx, "iban", e.target.value)
                        }
                        placeholder="RO49AAAA1B31007593840000"
                        className="w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={addCompany}
              className="flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-800 font-medium"
            >
              <Plus size={16} /> Adauga alta companie
            </button>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
                {error}
              </div>
            )}

            <div className="flex justify-between pt-2">
              <button
                onClick={() => setStep(1)}
                className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
              >
                Inapoi
              </button>
              <button
                onClick={handleSubmit}
                disabled={loading || !companies.some((c) => c.company_name.trim())}
                className="px-6 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 inline-flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Se salveaza...
                  </>
                ) : (
                  "Finalizeaza"
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Done */}
        {step === 3 && (
          <div className="p-8 text-center space-y-4">
            <div className="text-4xl">🎉</div>
            <h2 className="text-xl font-bold text-gray-900">Gata!</h2>
            <p className="text-gray-500">
              Contul tau e configurat. Te redirectionam la dashboard...
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
