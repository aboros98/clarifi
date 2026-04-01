"use client";

import { useEffect, useState, useRef } from "react";
import {
  FolderOpen,
  Folder,
  FileText,
  ChevronRight,
  ArrowLeft,
  Upload,
  Eye,
  X,
  Loader2,
  Trash2,
  RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";

interface FolderNode {
  id: string;
  name: string;
  path: string;
  parent_id: string | null;
  file_count: number;
  trace_summary: string | null;
}

interface FileNode {
  id: string;
  filename: string;
  mime_type: string | null;
  file_size: number | null;
  status: string | null;
  extracted_entity_type: string | null;
  created_at: string | null;
}

const TYPE_LABELS: Record<string, string> = {
  invoice: "Factura",
  contract: "Contract",
  bank_statement: "Extras de cont",
  estimate: "Deviz",
  unknown: "Necunoscut",
};

function friendlySize(bytes: number | null): string {
  if (!bytes) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function friendlyDate(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleDateString("ro-RO", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function DocumentExplorer() {
  const [treeFolders, setTreeFolders] = useState<FolderNode[]>([]);
  const [currentFolder, setCurrentFolder] = useState<FolderNode | null>(null);
  const [subfolders, setSubfolders] = useState<FolderNode[]>([]);
  const [files, setFiles] = useState<FileNode[]>([]);
  const [breadcrumb, setBreadcrumb] = useState<FolderNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Document viewer
  const [viewingDoc, setViewingDoc] = useState<any>(null);
  const [docLoading, setDocLoading] = useState(false);

  // Upload
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState<string[]>([]);
  const [dragging, setDragging] = useState(false);

  // Load folder tree on mount
  useEffect(() => {
    loadTree();
  }, []);

  async function loadTree() {
    try {
      const [treeData, docData] = await Promise.all([
        api.getFileTree().catch(() => ({ folders: [] })),
        api.getDocuments(100).catch(() => ({ documents: [] })),
      ]);
      setTreeFolders(treeData.folders || []);

      // Show documents as flat list when not in a folder
      if (!currentFolder) {
        const docs = docData.documents || [];
        setFiles(
          docs.map((d: any) => ({
            id: d.id,
            filename: d.filename || d.original_filename,
            mime_type: d.mime_type,
            file_size: null,
            status: d.processing_status,
            extracted_entity_type: d.document_type,
            created_at: d.created_at,
          }))
        );
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function openFolder(folder: FolderNode) {
    setLoading(true);
    try {
      const data = await api.getFolder(folder.id);
      setCurrentFolder({
        ...folder,
        trace_summary: data.folder?.trace_summary || null,
      });
      setSubfolders(data.subfolders || []);
      setFiles(data.files || []);

      // Update breadcrumb
      const idx = breadcrumb.findIndex((b) => b.id === folder.id);
      if (idx >= 0) {
        setBreadcrumb(breadcrumb.slice(0, idx + 1));
      } else {
        setBreadcrumb([...breadcrumb, folder]);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function goToRoot() {
    setCurrentFolder(null);
    setSubfolders([]);
    setBreadcrumb([]);
    // Reload everything fresh
    setLoading(true);
    Promise.all([
      api.getFileTree().catch(() => ({ folders: [] })),
      api.getDocuments(100).catch(() => ({ documents: [] })),
    ]).then(([treeData, docData]) => {
      setTreeFolders(treeData.folders || []);
      setFiles(
        (docData.documents || []).map((d: any) => ({
          id: d.id,
          filename: d.filename || d.original_filename,
          mime_type: d.mime_type,
          file_size: null,
          status: d.processing_status,
          extracted_entity_type: d.document_type,
          created_at: d.created_at,
        }))
      );
    }).finally(() => setLoading(false));
  }

  async function viewDocument(fileId: string) {
    setDocLoading(true);
    try {
      const doc = await api.getDocument(fileId);
      setViewingDoc(doc);
    } catch (e: any) {
      setError(`Nu pot deschide: ${e.message}`);
    } finally {
      setDocLoading(false);
    }
  }

  async function uploadFiles(fileList: FileList | File[]) {
    const filesToUpload = Array.from(fileList);
    if (filesToUpload.length === 0) return;
    setUploading(true);
    setUploadResults([]);
    setError(null);

    const results: string[] = [];
    for (const file of filesToUpload) {
      try {
        const res = await api.uploadDocument(file);
        if (res.status === "duplicate") {
          results.push(`${file.name} — deja exista`);
        } else {
          results.push(`${file.name} — incarcat, se analizeaza...`);
        }
      } catch {
        results.push(`${file.name} — eroare la incarcare`);
      }
      setUploadResults([...results]);
    }

    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
    loadTree();

    // Poll for updates while documents are processing
    let polls = 0;
    const pollInterval = setInterval(() => {
      polls++;
      loadTree();
      if (polls >= 30) clearInterval(pollInterval); // stop after 5 min
    }, 10000);
  }

  function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) uploadFiles(e.target.files);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length > 0) {
      uploadFiles(e.dataTransfer.files);
    }
  }

  // Root folders (no parent)
  const rootFolders = treeFolders.filter((f) => !f.parent_id);

  return (
    <div
      className="p-4 sm:p-6 max-w-5xl mx-auto space-y-4"
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {dragging && (
        <div className="fixed inset-0 z-40 bg-indigo-600/10 border-4 border-dashed border-indigo-400 flex items-center justify-center pointer-events-none">
          <div className="bg-white rounded-2xl shadow-xl px-8 py-6 text-center">
            <Upload size={32} className="text-indigo-600 mx-auto mb-2" />
            <p className="text-lg font-semibold text-gray-900">Trage fisierele aici</p>
            <p className="text-sm text-gray-500">PDF, DOCX, TXT, CSV, XLSX, imagini</p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FolderOpen size={24} /> Documente
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Documentele tale organizate de agent
          </p>
        </div>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            multiple
            accept=".pdf,.docx,.doc,.txt,.csv,.xlsx,.xls,.png,.jpg,.jpeg"
            onChange={handleUpload}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {uploading ? (
              <><Loader2 size={16} className="animate-spin" /> Se proceseaza...</>
            ) : (
              <><Upload size={16} /> Incarca documente</>
            )}
          </button>
        </div>
      </div>

      {/* Upload results */}
      {uploadResults.length > 0 && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-xl text-sm">
          <div className="flex items-center justify-between mb-1">
            <span className="text-green-700 font-medium">
              {uploading ? "Se proceseaza..." : "Finalizat"}
            </span>
            {!uploading && (
              <button onClick={() => setUploadResults([])} className="text-green-400 hover:text-green-600">
                <X size={14} />
              </button>
            )}
          </div>
          {uploadResults.map((r, i) => (
            <p key={i} className={`text-xs ${r.includes("eroare") ? "text-red-500" : "text-green-600"}`}>
              {r}
            </p>
          ))}
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 text-red-400 hover:text-red-600"
          >
            <X size={14} className="inline" />
          </button>
        </div>
      )}

      {/* Breadcrumb */}
      {breadcrumb.length > 0 && (
        <div className="flex items-center gap-1 text-sm">
          <button
            onClick={goToRoot}
            className="text-indigo-600 hover:underline flex items-center gap-1"
          >
            <ArrowLeft size={14} /> Toate
          </button>
          {breadcrumb.map((b, i) => (
            <span key={b.id} className="flex items-center gap-1">
              <ChevronRight size={14} className="text-gray-400" />
              {i < breadcrumb.length - 1 ? (
                <button
                  onClick={() => openFolder(b)}
                  className="text-indigo-600 hover:underline"
                >
                  {b.name}
                </button>
              ) : (
                <span className="text-gray-700 font-medium">{b.name}</span>
              )}
            </span>
          ))}
        </div>
      )}

      {/* Folder trace summary */}
      {currentFolder?.trace_summary && (
        <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4 text-sm text-indigo-800">
          <span className="font-semibold">Analiza agentului:</span>{" "}
          {currentFolder.trace_summary}
        </div>
      )}

      {/* Content */}
      <div className="bg-white rounded-xl border divide-y">
        {/* Subfolders */}
        {(currentFolder ? subfolders : rootFolders).map((f) => (
          <div
            key={f.id}
            onClick={() => openFolder(f)}
            className="px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-gray-50 transition-colors"
          >
            <Folder size={20} className="text-yellow-500 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">{f.name}</p>
              {f.trace_summary && (
                <p className="text-xs text-gray-400 truncate">
                  {f.trace_summary}
                </p>
              )}
            </div>
            <span className="text-xs text-gray-400 shrink-0">
              {f.file_count || 0} fisiere
            </span>
            <ChevronRight size={16} className="text-gray-300 shrink-0" />
          </div>
        ))}

        {/* Files */}
        {files.map((f) => {
          const isProcessing = f.status === "uploaded" || f.status === "parsing" || f.status === "extracting";
          const STATUS_LABELS: Record<string, string> = {
            uploaded: "Se analizeaza...",
            parsing: "Se analizeaza...",
            extracting: "Se extrag date...",
            needs_review: "Necesita verificare",
            validated: "Validat",
            stored: "Procesat",
            failed: "Eroare",
          };
          return (
            <div
              key={f.id}
              onClick={() => viewDocument(f.id)}
              className="px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-gray-50 transition-colors"
            >
              {isProcessing ? (
                <Loader2 size={20} className="text-indigo-500 shrink-0 animate-spin" />
              ) : (
                <FileText size={20} className="text-gray-400 shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{f.filename}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  {isProcessing && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-yellow-50 text-yellow-700 animate-pulse">
                      {STATUS_LABELS[f.status || ""] || "Se proceseaza..."}
                    </span>
                  )}
                  {f.status === "failed" && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-red-50 text-red-600">
                      Eroare la procesare
                    </span>
                  )}
                  {f.extracted_entity_type && !isProcessing && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600">
                      {TYPE_LABELS[f.extracted_entity_type] ||
                        f.extracted_entity_type}
                    </span>
                  )}
                  <span className="text-xs text-gray-400">
                    {friendlyDate(f.created_at)}
                  </span>
                  {f.file_size && (
                    <span className="text-xs text-gray-400">
                      {friendlySize(f.file_size)}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {isProcessing ? (
                  <RefreshCw size={16} className="text-indigo-400 animate-spin" />
                ) : (
                  <button
                    onClick={(e) => { e.stopPropagation(); viewDocument(f.id); }}
                    className="p-1 text-gray-300 hover:text-gray-600"
                    title="Vezi document"
                  >
                    <Eye size={16} />
                  </button>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm("Stergi acest document?")) {
                      api.deleteDocument(f.id).then(() => {
                        setFiles((prev) => prev.filter((x) => x.id !== f.id));
                        loadTree();
                      });
                    }
                  }}
                  className="p-1 text-gray-300 hover:text-red-500"
                  title="Sterge document"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          );
        })}

        {/* Empty state */}
        {!loading &&
          (currentFolder ? subfolders : rootFolders).length === 0 &&
          files.length === 0 && (
            <div className="px-4 py-12 text-center">
              <Upload size={32} className="text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-400">
                Niciun document inca. Incarca documente prin chat sau pune-le
                in folderul inbox/.
              </p>
            </div>
          )}
      </div>

      {/* Document viewer overlay */}
      {viewingDoc && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b">
              <div className="min-w-0">
                <h2 className="font-semibold truncate">
                  {viewingDoc.filename}
                </h2>
                <div className="flex items-center gap-2 mt-1">
                  {viewingDoc.document_type && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600">
                      {TYPE_LABELS[viewingDoc.document_type] ||
                        viewingDoc.document_type}
                    </span>
                  )}
                  {viewingDoc.extraction_confidence && (
                    <span className="text-xs text-gray-400">
                      {Math.round(viewingDoc.extraction_confidence * 100)}%
                      incredere
                    </span>
                  )}
                  <span className="text-xs text-gray-400">
                    {friendlyDate(viewingDoc.created_at)}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setViewingDoc(null)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {viewingDoc.raw_text ? (
                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono bg-gray-50 rounded-xl p-4 border">
                  {viewingDoc.raw_text}
                </pre>
              ) : (
                <p className="text-sm text-gray-400 text-center py-8">
                  Continutul documentului nu este disponibil.
                </p>
              )}

              {/* Extracted data */}
              {viewingDoc.extraction_raw_response && (
                <div className="mt-6">
                  <h3 className="text-sm font-semibold text-gray-600 mb-2">
                    Date extrase
                  </h3>
                  <pre className="text-xs text-gray-600 bg-gray-50 rounded-xl p-4 border overflow-x-auto max-h-60">
                    {typeof viewingDoc.extraction_raw_response === "string"
                      ? viewingDoc.extraction_raw_response
                      : JSON.stringify(
                          viewingDoc.extraction_raw_response,
                          null,
                          2
                        )}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Loading overlay for doc viewer */}
      {docLoading && (
        <div className="fixed inset-0 z-50 bg-black/30 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
        </div>
      )}
    </div>
  );
}
