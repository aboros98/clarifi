"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { supabase } from "@/lib/supabase";
import {
  LayoutDashboard,
  MessageSquare,
  Clock,
  FolderOpen,
  Bell,
  Activity,
  Settings,
  X,
  LogOut,
  User,
  ChevronDown,
  Building2,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/folders", label: "Documente", icon: FolderOpen },
  { href: "/alerts", label: "Alerte", icon: Bell },
  { href: "/jobs", label: "Remindere", icon: Clock },
  { href: "/decisions", label: "Activitate", icon: Activity },
  { href: "/settings", label: "Setari", icon: Settings },
];

export default function Sidebar({
  open,
  onClose,
  userInfo,
  companies,
  onSwitchCompany,
}: {
  open: boolean;
  onClose: () => void;
  userInfo?: { name: string; company: string; email: string } | null;
  companies?: { id: string; name: string; active: boolean }[];
  onSwitchCompany?: (id: string) => void;
}) {
  const pathname = usePathname();
  const [showCompanies, setShowCompanies] = useState(false);

  async function handleLogout() {
    if (supabase) {
      await supabase.auth.signOut();
    }
    localStorage.removeItem("clarifi_authenticated");
    window.location.href = "/landing";
  }

  return (
    <>
      {/* Overlay on mobile */}
      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-60 bg-gray-900 text-white flex flex-col
          transition-transform duration-200
          ${open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
      >
        <div className="flex items-center justify-between px-4 h-14 border-b border-gray-800">
          <span className="text-lg font-bold tracking-tight">Clarifi</span>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-800 lg:hidden"
          >
            <X size={18} />
          </button>
        </div>

        {/* Company switcher */}
        {companies && companies.length > 1 && (
          <div className="px-2 pt-3">
            <button
              onClick={() => setShowCompanies(!showCompanies)}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-300 hover:bg-gray-800 transition-colors"
            >
              <Building2 size={16} className="shrink-0" />
              <span className="flex-1 text-left truncate text-xs">
                {companies.find((c) => c.active)?.name || "Selecteaza"}
              </span>
              <ChevronDown
                size={14}
                className={`shrink-0 transition-transform ${showCompanies ? "rotate-180" : ""}`}
              />
            </button>
            {showCompanies && (
              <div className="mt-1 space-y-0.5">
                {companies.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => {
                      if (!c.active && onSwitchCompany) {
                        onSwitchCompany(c.id);
                      }
                      setShowCompanies(false);
                    }}
                    className={`w-full text-left px-3 py-1.5 rounded-lg text-xs transition-colors ${
                      c.active
                        ? "bg-indigo-600/20 text-indigo-300"
                        : "text-gray-400 hover:bg-gray-800 hover:text-white"
                    }`}
                  >
                    {c.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <nav className="flex-1 py-4 space-y-1 px-2">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={onClose}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  active
                    ? "bg-indigo-600 text-white"
                    : "text-gray-400 hover:bg-gray-800 hover:text-white"
                }`}
              >
                <Icon size={20} />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>

        {/* User profile + logout */}
        <div className="border-t border-gray-800 p-3">
          {userInfo?.name || userInfo?.email ? (
            <div className="flex items-center gap-3 px-2 py-2">
              <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center shrink-0 text-xs font-bold">
                {(userInfo.name || userInfo.email || "?")[0].toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                {userInfo.name && (
                  <p className="text-sm font-medium truncate">
                    {userInfo.name}
                  </p>
                )}
                {userInfo.company && (
                  <p className="text-xs text-gray-400 truncate">
                    {userInfo.company}
                  </p>
                )}
                {!userInfo.name && userInfo.email && (
                  <p className="text-xs text-gray-400 truncate">
                    {userInfo.email}
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3 px-2 py-2">
              <User size={16} className="text-gray-500" />
              <span className="text-xs text-gray-500">Neconectat</span>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-white w-full transition-colors mt-1"
          >
            <LogOut size={18} />
            <span>Deconectare</span>
          </button>
        </div>
      </aside>
    </>
  );
}
