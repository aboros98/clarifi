"use client";

import { useEffect } from "react";
import { supabase } from "@/lib/supabase";

export default function AuthCallbackPage() {
  useEffect(() => {
    // Supabase handles the OAuth callback automatically via the URL hash
    // Just redirect to home after a brief pause
    const timer = setTimeout(() => {
      window.location.href = "/";
    }, 1000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h2 className="text-lg font-semibold text-gray-700">Se autentifică...</h2>
        <p className="text-sm text-gray-400 mt-2">Vei fi redirecționat.</p>
      </div>
    </div>
  );
}
