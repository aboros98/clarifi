"use client";

import "./globals.css";
import Sidebar from "@/components/Sidebar";
import OnboardingOverlay from "@/components/OnboardingOverlay";
import { Menu } from "lucide-react";
import { useState, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { supabase } from "@/lib/supabase";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [userInfo, setUserInfo] = useState<{
    name: string;
    company: string;
    email: string;
  } | null>(null);
  const [companies, setCompanies] = useState<
    { id: string; name: string; active: boolean }[]
  >([]);
  const pathname = usePathname();
  const router = useRouter();

  const isPublicPage =
    pathname?.startsWith("/auth") || pathname === "/landing";

  useEffect(() => {
    if (isPublicPage) {
      setAuthenticated(null);
      return;
    }

    async function checkAuth() {
      if (!supabase) {
        // No Supabase — dev mode, skip auth
        setAuthenticated(true);
        checkOnboarding();
        return;
      }

      const { data } = await supabase.auth.getSession();
      if (data.session) {
        localStorage.setItem("clarifi_authenticated", "true");
        setAuthenticated(true);
        setUserInfo((prev) => ({
          ...prev,
          name: prev?.name || "",
          company: prev?.company || "",
          email: data.session.user.email || "",
        }));
        checkOnboarding();
        return;
      }

      // No session — check if we just came from OAuth (brief race)
      const wasAuthenticated = localStorage.getItem("clarifi_authenticated");
      if (wasAuthenticated) {
        // Give Supabase a moment to restore the session
        await new Promise((r) => setTimeout(r, 1000));
        const retry = await supabase.auth.getSession();
        if (retry.data.session) {
          setAuthenticated(true);
          setUserInfo({
            name: "",
            company: "",
            email: retry.data.session.user.email || "",
          });
          checkOnboarding();
          return;
        }
      }

      // Truly not logged in
      localStorage.removeItem("clarifi_authenticated");
      router.replace("/landing");
    }

    async function checkOnboarding() {
      try {
        const status = await api.getOnboardingStatus();
        if (!status.onboarded) {
          setShowOnboarding(true);
        } else {
          setUserInfo((prev) => ({
            email: prev?.email || "",
            name: status.user_name || "",
            company: status.company_name || "",
          }));
          if (status.companies?.length > 0) {
            setCompanies(status.companies);
          }
        }
      } catch {
        // API not reachable — don't block
      }
    }

    checkAuth();

    // Listen for auth changes (logout, token refresh)
    if (supabase) {
      const { data: listener } = supabase.auth.onAuthStateChange(
        (event) => {
          if (event === "SIGNED_OUT") {
            localStorage.removeItem("clarifi_authenticated");
            setAuthenticated(false);
            router.replace("/landing");
          }
        }
      );
      return () => listener.subscription.unsubscribe();
    }
  }, [isPublicPage, router]);

  return (
    <html lang="ro">
      <body className="bg-gray-50 text-gray-900 antialiased">
        {isPublicPage ? (
          <>{children}</>
        ) : authenticated === null ? (
          <div className="flex items-center justify-center h-screen">
            <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="flex h-screen overflow-hidden">
            <Sidebar
              open={sidebarOpen}
              onClose={() => setSidebarOpen(false)}
              userInfo={userInfo}
              companies={companies}
              onSwitchCompany={async (id) => {
                try {
                  await api.switchCompany(id);
                  window.location.reload();
                } catch {
                  // Silently fail — user can try from settings
                }
              }}
            />

            <div className="flex-1 flex flex-col overflow-hidden">
              <div className="lg:hidden flex items-center h-14 px-4 border-b bg-white">
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="p-2 -ml-2 rounded-lg hover:bg-gray-100"
                >
                  <Menu size={20} />
                </button>
                <span className="ml-3 font-semibold">Clarifi</span>
              </div>

              <main className="flex-1 overflow-y-auto">{children}</main>
            </div>

            {showOnboarding && (
              <OnboardingOverlay
                onComplete={() => {
                  setShowOnboarding(false);
                  window.location.reload();
                }}
              />
            )}
          </div>
        )}
      </body>
    </html>
  );
}
