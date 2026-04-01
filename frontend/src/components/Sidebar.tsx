"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  Clock,
  FolderOpen,
  Bell,
  ScrollText,
  Settings,
  X,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Agent Chat", icon: MessageSquare },
  { href: "/jobs", label: "Jobs", icon: Clock },
  { href: "/folders", label: "Folders", icon: FolderOpen },
  { href: "/alerts", label: "Alerte", icon: Bell },
  { href: "/decisions", label: "Decision Log", icon: ScrollText },
  { href: "/settings", label: "Setări", icon: Settings },
];

export default function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();

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
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-800 lg:hidden">
            <X size={18} />
          </button>
        </div>

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

        <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-500">
          Clarifi v0.1.0
        </div>
      </aside>
    </>
  );
}
