"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2, Plus, Upload } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { api } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  tools?: string[];
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Salut! Sunt **Clarifi**, asistentul tau financiar.\n\nPoti sa ma intrebi:\n- Cati bani am in cont?\n- Cine imi datoreaza bani?\n- Ce facturi am restante?\n- Ce trebuie sa fac saptamana asta?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | undefined>();
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleNewChat() {
    setThreadId(undefined);
    setMessages([
      {
        role: "assistant",
        content: "Conversatie noua. Cu ce te pot ajuta?",
      },
    ]);
  }

  async function handleSend() {
    if (!input.trim() || loading) return;

    const userMsg: Message = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const response = await api.chat(userMsg.content, threadId);
      setThreadId(response.thread_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            response.response ||
            "Nu am putut procesa cererea. Incearca din nou.",
          tools: response.tools_used || [],
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "A aparut o eroare. Verifica conexiunea si incearca din nou.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: `📎 ${file.name}` },
    ]);
    setLoading(true);

    try {
      const result = await api.uploadDocument(file);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            result.status === "duplicate"
              ? `Documentul **${file.name}** exista deja in sistem.`
              : `Am primit **${file.name}**. Il analizez in fundal — vei vedea rezultatele in pagina de Documente.`,
          tools: ["Incarc document"],
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Nu am putut incarca **${file.name}**. Incearca din nou.`,
        },
      ]);
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <div className="px-4 sm:px-6 py-3 border-b flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold">Clarifi</h1>
          <p className="text-xs text-gray-400">
            {threadId ? "Conversatie activa" : "Conversatie noua"}
          </p>
        </div>
        <button
          onClick={handleNewChat}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border hover:bg-gray-50 transition-colors"
        >
          <Plus size={14} /> Nou
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-6">
          {messages.map((msg, i) => (
            <div key={i}>
              {msg.role === "assistant" ? (
                <div className="flex gap-3">
                  <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot size={14} className="text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    {msg.tools && msg.tools.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-2">
                        {msg.tools.map((t, j) => (
                          <span
                            key={j}
                            className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-500"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="prose prose-sm prose-gray max-w-none [&>p]:mb-2 [&>ul]:mb-2 [&>ol]:mb-2 [&>h1]:text-lg [&>h2]:text-base [&>h3]:text-sm [&>*:last-child]:mb-0">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex gap-3 justify-end">
                  <div className="bg-gray-100 rounded-2xl px-4 py-2.5 text-sm max-w-[80%]">
                    {msg.content}
                  </div>
                  <div className="w-7 h-7 rounded-full bg-gray-300 flex items-center justify-center shrink-0 mt-0.5">
                    <User size={14} className="text-white" />
                  </div>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center shrink-0">
                <Loader2 size={14} className="text-white animate-spin" />
              </div>
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t bg-white px-4 sm:px-6 py-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-end gap-2 bg-gray-50 rounded-2xl border px-4 py-2">
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".pdf,.docx,.doc,.txt,.csv,.xlsx,.xls,.png,.jpg,.jpeg"
              onChange={handleFileUpload}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
              className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-200 disabled:opacity-50 shrink-0 transition-colors"
              title="Incarca document"
            >
              <Upload size={18} />
            </button>
            <textarea
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = Math.min(e.target.scrollHeight, 150) + "px";
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Scrie o intrebare..."
              rows={1}
              className="flex-1 bg-transparent text-sm resize-none focus:outline-none py-1.5 max-h-[150px]"
              disabled={loading}
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="p-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-30 shrink-0 transition-colors"
            >
              <Send size={16} />
            </button>
          </div>
          <p className="text-[10px] text-gray-400 text-center mt-2">
            Clarifi poate face greseli. Verifica datele importante.
          </p>
        </div>
      </div>
    </div>
  );
}
