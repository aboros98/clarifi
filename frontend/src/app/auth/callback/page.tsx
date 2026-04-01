"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export default function AuthCallbackPage() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!supabase) {
      window.location.href = "/";
      return;
    }

    const sb = supabase!;

    async function handleOAuth() {
      const params = new URLSearchParams(window.location.search);
      const code = params.get("code");

      if (code) {
        const { error } = await sb.auth.exchangeCodeForSession(code);
        if (error) {
          setError(error.message);
          return;
        }
        localStorage.setItem("clarifi_authenticated", "true");
        window.location.href = "/";
        return;
      }

      // Hash-based flow — poll for the session
      for (let i = 0; i < 20; i++) {
        const { data } = await sb.auth.getSession();
        if (data.session) {
          localStorage.setItem("clarifi_authenticated", "true");
          window.location.href = "/";
          return;
        }
        await new Promise((r) => setTimeout(r, 500));
      }

      setError("Nu s-a putut finaliza autentificarea. Incearca din nou.");
    }

    handleOAuth();
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        {error ? (
          <>
            <p className="text-red-600 font-medium">{error}</p>
            <a
              href="/auth/login"
              className="text-sm text-indigo-600 hover:underline mt-3 inline-block"
            >
              Inapoi la login
            </a>
          </>
        ) : (
          <>
            <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-gray-700">
              Se autentifica...
            </h2>
          </>
        )}
      </div>
    </div>
  );
}
