"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"login" | "signup">("login");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!supabase) {
      setError("Supabase nu este configurat. Setează NEXT_PUBLIC_SUPABASE_URL și NEXT_PUBLIC_SUPABASE_ANON_KEY.");
      return;
    }
    setLoading(true);
    setError(null);

    try {
      if (mode === "signup") {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        setError("Verifică-ți email-ul pentru link-ul de confirmare.");
        return;
      }

      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      window.location.href = "/";
    } catch (e: any) {
      setError(e.message || "Eroare la autentificare");
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleLogin() {
    if (!supabase) {
      setError("Supabase nu este configurat.");
      return;
    }
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
    if (error) setError(error.message);
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Clarifi</h1>
          <p className="text-sm text-gray-500 mt-2">Asistent financiar AI</p>
        </div>

        <div className="bg-white rounded-2xl border p-6 shadow-sm">
          <h2 className="text-lg font-semibold mb-4">
            {mode === "login" ? "Autentificare" : "Cont nou"}
          </h2>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl border bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="email@companie.ro"
                required
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Parolă</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl border bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="••••••••"
                required
                minLength={6}
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {loading ? "Se procesează..." : mode === "login" ? "Intră" : "Creează cont"}
            </button>
          </form>

          <div className="my-4 flex items-center gap-3">
            <div className="flex-1 border-t" />
            <span className="text-xs text-gray-400">sau</span>
            <div className="flex-1 border-t" />
          </div>

          <button
            onClick={handleGoogleLogin}
            className="w-full py-2.5 bg-white border rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
          >
            <svg width="16" height="16" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Continuă cu Google
          </button>

          <p className="text-center text-xs text-gray-400 mt-4">
            {mode === "login" ? (
              <>
                Nu ai cont?{" "}
                <button onClick={() => setMode("signup")} className="text-indigo-600 hover:underline">
                  Creează unul
                </button>
              </>
            ) : (
              <>
                Ai deja cont?{" "}
                <button onClick={() => setMode("login")} className="text-indigo-600 hover:underline">
                  Autentifică-te
                </button>
              </>
            )}
          </p>
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">
          Clarifi v0.1.0
        </p>
      </div>
    </div>
  );
}
