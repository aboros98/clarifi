"use client";

import { useEffect, useState } from "react";
import { FolderOpen, Plus, Trash2, RefreshCw, Cloud, HardDrive } from "lucide-react";
import { api } from "@/lib/api";

export default function FoldersPage() {
  const [folders, setFolders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [newPath, setNewPath] = useState("");
  const [newName, setNewName] = useState("");

  useEffect(() => {
    loadFolders();
  }, []);

  async function loadFolders() {
    try {
      const data = await api.getFolders();
      setFolders(data.folders || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd() {
    if (!newPath.trim()) return;
    try {
      await api.addFolder({
        provider: "local",
        folder_path: newPath.trim(),
        display_name: newName.trim() || newPath.trim(),
      });
      setNewPath("");
      setNewName("");
      setShowAdd(false);
      setError(null);
      loadFolders();
    } catch (e: any) {
      setError(`Nu am putut adăuga: ${e.message}`);
    }
  }

  async function handleRemove(id: string) {
    await api.removeFolder(id);
    setFolders((prev) => prev.filter((f) => f.id !== id));
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <FolderOpen size={24} />
          <div>
            <h1 className="text-2xl font-bold">Folder Manager</h1>
            <p className="text-sm text-gray-500">Foldere monitorizate pentru documente noi</p>
          </div>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm"
        >
          <Plus size={16} /> Adauga folder
        </button>
      </div>

      {error && <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>}

      {showAdd && (
        <div className="mb-6 bg-white rounded-xl border p-4">
          <h3 className="text-sm font-semibold mb-3">Folder Nou</h3>
          <div className="flex gap-3">
            <input
              type="text"
              value={newPath}
              onChange={(e) => setNewPath(e.target.value)}
              placeholder="Cale folder (ex: /Users/docs/facturi)"
              className="flex-1 px-3 py-2 rounded-lg border text-sm"
            />
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Nume (optional)"
              className="w-48 px-3 py-2 rounded-lg border text-sm"
            />
            <button
              onClick={handleAdd}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
            >
              Salveaza
            </button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border divide-y">
        {folders.map((f) => (
          <div key={f.id} className="px-4 py-4 flex items-center gap-4">
            {f.provider === "google_drive" ? (
              <Cloud size={20} className="text-blue-500 shrink-0" />
            ) : (
              <HardDrive size={20} className="text-gray-500 shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <div className="font-medium text-sm">{f.display_name}</div>
              <div className="text-xs text-gray-400 truncate">
                {f.folder_path || f.folder_id}
              </div>
            </div>
            <div className="text-xs text-gray-500">
              {f.files_processed} fisiere procesate
            </div>
            <div className="text-xs">
              {f.is_active ? (
                <span className="text-green-600">Activ</span>
              ) : (
                <span className="text-gray-400">Inactiv</span>
              )}
            </div>
            <div className="text-xs text-gray-400">
              {f.last_synced_at
                ? `Sync: ${new Date(f.last_synced_at).toLocaleDateString("ro-RO")}`
                : "Nesincronizat"}
            </div>
            {f.is_active && (
              <button
                onClick={() => handleRemove(f.id)}
                className="text-red-400 hover:text-red-600"
              >
                <Trash2 size={16} />
              </button>
            )}
          </div>
        ))}
        {!loading && folders.length === 0 && (
          <div className="px-4 py-8 text-center text-gray-400">
            Niciun folder monitorizat. Adauga unul pentru a incepe.
          </div>
        )}
      </div>
    </div>
  );
}
