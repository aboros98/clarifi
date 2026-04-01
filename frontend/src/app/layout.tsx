"use client";

import "./globals.css";
import Sidebar from "@/components/Sidebar";
import { Menu } from "lucide-react";
import { useState } from "react";
import { usePathname } from "next/navigation";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();
  const isAuthPage = pathname?.startsWith("/auth");

  return (
    <html lang="ro">
      <body className="bg-gray-50 text-gray-900 antialiased">
        {isAuthPage ? (
          // Auth pages render without sidebar
          <>{children}</>
        ) : (
          <div className="flex h-screen overflow-hidden">
            <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

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
          </div>
        )}
      </body>
    </html>
  );
}
