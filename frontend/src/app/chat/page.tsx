"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2, Plus } from "lucide-react";
import { api } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Salut! Sunt Clarifi, asistentul tau financiar.\n\nIncearca sa ma intrebi:\n- Cati bani am in cont?\n- Cine imi datoreaza bani?\n- Ce facturi am restante?\n- Ce trebuie sa fac saptamana asta?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | undefined>();
  const bottomRef = useRef<HTMLDivElement>(null);

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
            response.response || "Nu am putut procesa cererea. Incearca din nou.",
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

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="px-4 sm:px-6 py-3 border-b bg-white flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Chat cu Clarifi</h1>
          <p className="text-xs text-gray-500">
            {threadId
              ? "Agentul isi aminteste conversatia"
              : "Conversatie noua"}
          </p>
        </div>
        <button
          onClick={handleNewChat}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border hover:bg-gray-50"
        >
          <Plus size={14} /> Nou
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {msg.role === "assistant" && (
              <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center shrink-0">
                <Bot size={16} className="text-indigo-600" />
              </div>
            )}
            <div
              className={`max-w-[85%] sm:max-w-[70%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white"
                  : "bg-white border text-gray-800"
              }`}
            >
              {msg.content}
            </div>
            {msg.role === "user" && (
              <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center shrink-0">
                <User size={16} className="text-gray-600" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
              <Loader2 size={16} className="text-indigo-600 animate-spin" />
            </div>
            <div className="bg-white border rounded-2xl px-4 py-3 text-sm text-gray-400">
              Analizez datele...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 sm:px-6 py-4 border-t bg-white">
        <div className="flex gap-2 max-w-3xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Scrie o intrebare... (ex: Cati bani am?)"
            className="flex-1 px-4 py-3 rounded-xl border bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="px-4 py-3 rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
