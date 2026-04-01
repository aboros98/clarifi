"use client";

import { useEffect, useState } from "react";
import { Settings, FolderOpen, MessageCircle, Bot, Plug } from "lucide-react";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [config, setConfig] = useState<any>(null);

  useEffect(() => {
    api.getSettings?.()?.then(setConfig).catch(() => {});
  }, []);

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-2 mb-6">
        <Settings size={24} />
        <div>
          <h1 className="text-2xl font-bold">Setări</h1>
          <p className="text-sm text-gray-500">Configurare integrări și preferințe</p>
        </div>
      </div>

      <div className="space-y-4">
        {/* Google Drive */}
        <div className="bg-white rounded-xl border p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
                <FolderOpen size={20} className="text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold text-sm">Google Drive</h3>
                <p className="text-xs text-gray-500">Conectează foldere Drive pentru auto-import documente</p>
              </div>
            </div>
            <span className="px-3 py-1.5 bg-gray-100 text-gray-500 rounded-lg text-xs">
              {config?.has_drive_credentials ? "Configurat" : "În curând"}
            </span>
          </div>
        </div>

        {/* Telegram */}
        <div className="bg-white rounded-xl border p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-sky-50 flex items-center justify-center">
                <MessageCircle size={20} className="text-sky-600" />
              </div>
              <div>
                <h3 className="font-semibold text-sm">Telegram</h3>
                <p className="text-xs text-gray-500">Primește alerte și interacționează cu agentul via Telegram</p>
              </div>
            </div>
            <span className="px-3 py-1.5 bg-gray-100 text-gray-500 rounded-lg text-xs">
              {config?.has_telegram_bot ? "Configurat" : "În curând"}
            </span>
          </div>
        </div>

        {/* Status */}
        <div className="bg-white rounded-xl border p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center">
              <Bot size={20} className="text-purple-600" />
            </div>
            <div>
              <h3 className="font-semibold text-sm">Status Sistem</h3>
              <p className="text-xs text-gray-500">Configurare curentă</p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <div className="px-3 py-2 bg-gray-50 rounded-lg">
              <span className="text-xs text-gray-500">Model:</span>{" "}
              <span className="font-medium">{config?.llm_model || "..."}</span>
            </div>
            <div className="px-3 py-2 bg-gray-50 rounded-lg">
              <span className="text-xs text-gray-500">API Key:</span>{" "}
              <span className="font-medium">{config?.has_google_api_key ? "✓ Configurat" : "✗ Lipsă"}</span>
            </div>
            <div className="px-3 py-2 bg-gray-50 rounded-lg">
              <span className="text-xs text-gray-500">Alerte facturi (zile):</span>{" "}
              <span className="font-medium">{config?.alert_invoice_due_soon_days || "..."}</span>
            </div>
            <div className="px-3 py-2 bg-gray-50 rounded-lg">
              <span className="text-xs text-gray-500">Alerte contracte (zile):</span>{" "}
              <span className="font-medium">{config?.alert_contract_expiry_days || "..."}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
