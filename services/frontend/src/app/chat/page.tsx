"use client";

import { useState, useRef, useEffect, FormEvent, useCallback } from "react";
import {
  Send,
  Paperclip,
  Sparkles,
  RotateCcw,
  ChevronDown,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  AlertTriangle,
  X,
  MessageSquare,
  Plus,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import PageHeader from "@/components/layout/page-header";
import { runTeam } from "@/lib/api";

const API_URL = "/api/proxy/agno";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface ApprovalReq {
  tool_name: string;
  tool_args: Record<string, unknown>;
  needs_confirmation: boolean;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: string;
  timestamp: Date;
  followups?: string[];
  isPaused?: boolean;
  runId?: string;
  requirements?: ApprovalReq[];
  files?: string[];
}

interface SessionEntry {
  id: string;
  label: string;
  ts: number;
}

/* ------------------------------------------------------------------ */
/* Suggestions                                                         */
/* ------------------------------------------------------------------ */

const SUGGESTIONS = [
  { text: "Investiga las ultimas tendencias en AI agents", icon: "🔍" },
  { text: "Crea un plan de marketing para Docflow", icon: "📊" },
  { text: "Genera una imagen para Instagram de Aurora", icon: "🎨" },
  { text: "Analiza el feedback de clientes de Docflow", icon: "📋" },
  { text: "Redacta un email de seguimiento para un lead", icon: "✉️" },
  { text: "Revisa el codigo del ultimo PR", icon: "💻" },
];

/* ------------------------------------------------------------------ */
/* Empty state                                                         */
/* ------------------------------------------------------------------ */

function EmptyState({ onSelect }: { onSelect: (t: string) => void }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6">
      <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 flex items-center justify-center mb-6">
        <Sparkles size={28} className="text-emerald-400" />
      </div>
      <h1 className="text-2xl font-semibold text-white mb-2 tracking-tight">NEXUS Chat</h1>
      <p className="text-sm text-zinc-500 mb-8 max-w-md text-center leading-relaxed">
        46 agentes especializados. Pregunta lo que necesites.
      </p>
      <div className="grid grid-cols-2 gap-2.5 max-w-lg w-full">
        {SUGGESTIONS.map((s) => (
          <button key={s.text} onClick={() => onSelect(s.text)} className="text-left px-4 py-3.5 rounded-xl bg-[#0f0f12] border border-[#1e1e24] hover:border-zinc-700 hover:bg-[#141418] transition-all duration-150 group">
            <span className="text-base mr-2">{s.icon}</span>
            <span className="text-[13px] text-zinc-400 group-hover:text-zinc-300 leading-snug">{s.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Approval card                                                       */
/* ------------------------------------------------------------------ */

function ApprovalCard({ requirements, runId, onResolved }: { requirements: ApprovalReq[]; runId?: string; onResolved: () => void }) {
  const [resolving, setResolving] = useState(false);
  const [resolved, setResolved] = useState<"approved" | "rejected" | null>(null);

  async function handleResolve(action: "approved" | "rejected") {
    if (!runId || resolving) return;
    setResolving(true);
    try {
      await fetch(`${API_URL}/teams/nexus-master/runs/${runId}/continue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      setResolved(action);
      onResolved();
    } catch {
      // ignore
    } finally {
      setResolving(false);
    }
  }

  if (resolved) {
    return (
      <div className={`flex items-center gap-2 px-4 py-3 rounded-xl border ${resolved === "approved" ? "bg-emerald-500/5 border-emerald-500/20" : "bg-red-500/5 border-red-500/20"}`}>
        {resolved === "approved" ? <CheckCircle size={14} className="text-emerald-400" /> : <XCircle size={14} className="text-red-400" />}
        <span className="text-[13px] text-zinc-300">{resolved === "approved" ? "Aprobado" : "Rechazado"}</span>
      </div>
    );
  }

  return (
    <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <AlertTriangle size={14} className="text-amber-400" />
        <span className="text-[13px] font-medium text-amber-400">Aprobacion requerida</span>
      </div>
      {requirements.map((req, i) => (
        <div key={i} className="bg-black/20 rounded-lg p-3">
          <div className="text-[12px] text-zinc-300 font-mono mb-1">{req.tool_name}</div>
          {Object.entries(req.tool_args).map(([k, v]) => (
            <div key={k} className="flex gap-2 text-[11px]">
              <span className="text-zinc-600">{k}:</span>
              <span className="text-zinc-400">{String(v)}</span>
            </div>
          ))}
        </div>
      ))}
      <div className="flex gap-2">
        <button onClick={() => handleResolve("rejected")} disabled={resolving} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-[12px] font-medium hover:bg-red-500/20 disabled:opacity-40 transition-colors">
          {resolving ? <Loader2 size={12} className="animate-spin" /> : <XCircle size={12} />} Rechazar
        </button>
        <button onClick={() => handleResolve("approved")} disabled={resolving} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-600 text-white text-[12px] font-medium hover:bg-emerald-500 disabled:opacity-40 transition-colors">
          {resolving ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle size={12} />} Aprobar
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Message bubble                                                      */
/* ------------------------------------------------------------------ */

function MessageBubble({ msg, onFollowup }: { msg: Message; onFollowup: (t: string) => void }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[70%] bg-emerald-600/15 border border-emerald-500/20 rounded-2xl rounded-br-md px-4 py-3">
          <p className="text-[14px] text-zinc-100 leading-relaxed whitespace-pre-wrap">{msg.content}</p>
          {msg.files && msg.files.length > 0 && (
            <div className="flex gap-1.5 mt-2">
              {msg.files.map((f) => (
                <span key={f} className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded flex items-center gap-1">
                  <Paperclip size={8} />{f}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 max-w-[85%]">
      <div className="w-7 h-7 rounded-lg bg-[#141418] border border-[#1e1e24] flex items-center justify-center shrink-0 mt-0.5">
        <span className="text-[11px]">🤖</span>
      </div>
      <div className="flex-1 min-w-0 space-y-2">
        {msg.agent && (
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-[11px] font-medium text-emerald-400">{msg.agent}</span>
            <span className="text-[10px] text-zinc-600 flex items-center gap-1"><Clock size={9} />{msg.timestamp.toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" })}</span>
          </div>
        )}
        <div className="agent-response text-[14px] text-zinc-300 leading-relaxed">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
        </div>
        {msg.isPaused && msg.requirements && msg.requirements.length > 0 && (
          <ApprovalCard requirements={msg.requirements} runId={msg.runId} onResolved={() => {}} />
        )}
        {msg.followups && msg.followups.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-2">
            {msg.followups.map((f) => (
              <button key={f} onClick={() => onFollowup(f)} className="text-[11px] text-zinc-500 bg-zinc-900 border border-[#1e1e24] px-3 py-1.5 rounded-lg hover:text-zinc-300 hover:border-zinc-700 transition-colors">
                {f}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Loading                                                             */
/* ------------------------------------------------------------------ */

function LoadingIndicator() {
  return (
    <div className="flex gap-3 max-w-[85%]">
      <div className="w-7 h-7 rounded-lg bg-[#141418] border border-[#1e1e24] flex items-center justify-center shrink-0">
        <span className="text-[11px]">🤖</span>
      </div>
      <div className="flex items-center gap-1.5 py-3">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce" />
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce [animation-delay:100ms]" />
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce [animation-delay:200ms]" />
        <span className="text-[12px] text-zinc-600 ml-2">Procesando...</span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Session sidebar                                                     */
/* ------------------------------------------------------------------ */

function SessionSidebar({
  sessions,
  currentId,
  onSelect,
  onNew,
  loadingSession,
}: {
  sessions: SessionEntry[];
  currentId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  loadingSession: boolean;
}) {
  return (
    <div className="w-[240px] border-r border-[#1e1e24] flex flex-col bg-[#0a0a0d] shrink-0">
      <div className="p-3 border-b border-[#1e1e24]">
        <button
          onClick={onNew}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 text-[12px] font-medium hover:bg-emerald-600/20 transition-colors"
        >
          <Plus size={12} /> Nueva conversacion
        </button>
      </div>
      <div className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5">
        {sessions.map((s) => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            disabled={loadingSession}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-[12px] transition-colors ${
              s.id === currentId
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.03]"
            }`}
          >
            <div className="flex items-center gap-2">
              <MessageSquare size={11} className="shrink-0" />
              <span className="truncate flex-1">{s.label}</span>
            </div>
            <div className="text-[10px] text-zinc-700 mt-1 pl-[19px]">
              {new Date(s.ts).toLocaleDateString("es", { day: "2-digit", month: "short" })}
              {" "}
              {new Date(s.ts).toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" })}
            </div>
          </button>
        ))}
        {sessions.length === 0 && (
          <div className="text-[11px] text-zinc-700 text-center py-6">Sin conversaciones</div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Chat page                                                           */
/* ------------------------------------------------------------------ */

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingSession, setLoadingSession] = useState(false);
  const [files, setFiles] = useState<File[]>([]);

  // Session persistence
  const [sessionId, setSessionId] = useState(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("qyne-current-session");
      if (saved) return saved;
    }
    const newId = `nexus-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    if (typeof window !== "undefined") {
      localStorage.setItem("qyne-current-session", newId);
      const history = JSON.parse(localStorage.getItem("qyne-session-history") || "[]") as SessionEntry[];
      history.unshift({ id: newId, label: "Nueva conversacion", ts: Date.now() });
      localStorage.setItem("qyne-session-history", JSON.stringify(history.slice(0, 10)));
    }
    return newId;
  });

  const [sessions, setSessions] = useState<SessionEntry[]>(() => {
    if (typeof window !== "undefined") {
      return JSON.parse(localStorage.getItem("qyne-session-history") || "[]");
    }
    return [];
  });

  function updateSessionLabel(label: string) {
    if (typeof window === "undefined") return;
    const history = JSON.parse(localStorage.getItem("qyne-session-history") || "[]") as SessionEntry[];
    const idx = history.findIndex((h) => h.id === sessionId);
    if (idx >= 0) {
      history[idx].label = label.slice(0, 50);
      localStorage.setItem("qyne-session-history", JSON.stringify(history));
      setSessions([...history]);
    }
  }

  // Load conversation from Agno when switching sessions
  const loadSession = useCallback(async (id: string) => {
    setSessionId(id);
    setMessages([]);
    setLoadingSession(true);
    if (typeof window !== "undefined") {
      localStorage.setItem("qyne-current-session", id);
    }

    try {
      const resp = await fetch(`${API_URL}/teams/nexus-master/runs?session_id=${encodeURIComponent(id)}&limit=20`);
      if (!resp.ok) { setLoadingSession(false); return; }
      const runs = await resp.json();

      if (!Array.isArray(runs) || runs.length === 0) { setLoadingSession(false); return; }

      // Convert runs to messages (each run has run_input + content)
      const loaded: Message[] = [];
      // Runs come newest-first, reverse for chronological order
      const sorted = [...runs].reverse();

      for (const run of sorted) {
        const userText = run.run_input || run.input || "";
        const agentText = typeof run.content === "string" ? run.content : (run.content?.text || "");
        const ts = run.created_at ? new Date(run.created_at) : new Date();

        if (userText) {
          loaded.push({
            id: `h-u-${run.run_id}`,
            role: "user",
            content: userText,
            timestamp: ts,
          });
        }
        if (agentText) {
          loaded.push({
            id: `h-a-${run.run_id}`,
            role: "assistant",
            content: agentText,
            agent: run.agent_name || "NEXUS",
            timestamp: ts,
          });
        }
      }

      setMessages(loaded);
    } catch {
      // Failed to load, show empty
    } finally {
      setLoadingSession(false);
    }
  }, []);

  // Load current session on mount
  useEffect(() => {
    loadSession(sessionId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function newSession() {
    const newId = `nexus-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setSessionId(newId);
    setMessages([]);
    if (typeof window !== "undefined") {
      localStorage.setItem("qyne-current-session", newId);
      const history = JSON.parse(localStorage.getItem("qyne-session-history") || "[]") as SessionEntry[];
      history.unshift({ id: newId, label: "Nueva conversacion", ts: Date.now() });
      const trimmed = history.slice(0, 10);
      localStorage.setItem("qyne-session-history", JSON.stringify(trimmed));
      setSessions(trimmed);
    }
  }

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 160)}px`;
    }
  }, [input]);

  async function send(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;

    const fileNames = files.map((f) => f.name);
    const userMessage: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      content: msg,
      timestamp: new Date(),
      files: fileNames.length > 0 ? fileNames : undefined,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("message", msg);
      formData.append("stream", "false");
      formData.append("session_id", sessionId);
      formData.append("user_id", "nexus-ui-user");
      for (const f of files) {
        formData.append("files", f);
      }

      const response = await fetch(`${API_URL}/teams/nexus-master/runs`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();

      const content =
        typeof data.content === "string"
          ? data.content
          : ((data.content as Record<string, unknown>)?.text as string) || JSON.stringify(data);

      const followups: string[] = [];
      if (Array.isArray(data.followups)) {
        for (const f of data.followups) {
          if (typeof f === "string") followups.push(f);
          else if (typeof f === "object" && f !== null && "text" in f) followups.push((f as { text: string }).text);
        }
      }

      const isPaused = Boolean(data.is_paused);
      const requirements: ApprovalReq[] = [];
      if (isPaused && Array.isArray(data.active_requirements)) {
        for (const req of data.active_requirements) {
          if (typeof req === "object" && req !== null) {
            const r = req as Record<string, unknown>;
            const te = r.tool_execution as Record<string, unknown> | undefined;
            requirements.push({
              tool_name: (te?.tool_name as string) || "unknown",
              tool_args: (te?.tool_args as Record<string, unknown>) || {},
              needs_confirmation: Boolean(r.needs_confirmation),
            });
          }
        }
      }

      if (messages.length === 0) {
        updateSessionLabel(msg);
      }

      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: "assistant",
          content,
          agent: (data.agent_name as string) || "NEXUS",
          timestamp: new Date(),
          followups: followups.length > 0 ? followups : undefined,
          isPaused,
          runId: data.run_id as string | undefined,
          requirements: requirements.length > 0 ? requirements : undefined,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { id: `e-${Date.now()}`, role: "assistant", content: `Error: ${err instanceof Error ? err.message : "Conexion fallida"}`, timestamp: new Date() },
      ]);
    } finally {
      setLoading(false);
      setFiles([]);
      inputRef.current?.focus();
    }
  }

  function handleSubmit(e: FormEvent) { e.preventDefault(); send(); }
  function handleKeyDown(e: React.KeyboardEvent) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }
  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) setFiles(Array.from(e.target.files));
  }

  const hasMessages = messages.length > 0;

  return (
    <div className="h-full flex">
      {/* Session sidebar */}
      <SessionSidebar
        sessions={sessions}
        currentId={sessionId}
        onSelect={loadSession}
        onNew={newSession}
        loadingSession={loadingSession}
      />

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        <PageHeader title="Chat" badge={`Session: ${sessionId.slice(-8)}`} />

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {loadingSession ? (
            <div className="flex items-center justify-center h-full">
              <div className="flex items-center gap-2 text-zinc-600">
                <Loader2 size={16} className="animate-spin" />
                <span className="text-[13px]">Cargando conversacion...</span>
              </div>
            </div>
          ) : !hasMessages ? (
            <EmptyState onSelect={(t) => send(t)} />
          ) : (
            <div className="max-w-3xl mx-auto px-6 py-6 space-y-6">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} msg={msg} onFollowup={(t) => send(t)} />
              ))}
              {loading && <LoadingIndicator />}
            </div>
          )}
        </div>

        {/* Scroll to bottom */}
        {hasMessages && (
          <div className="flex justify-center -mt-4 mb-1 relative z-10">
            <button onClick={() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })} className="w-7 h-7 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-400 hover:text-white hover:bg-zinc-700 transition-colors shadow-lg">
              <ChevronDown size={14} />
            </button>
          </div>
        )}

        {/* File preview */}
        {files.length > 0 && (
          <div className="px-6">
            <div className="max-w-3xl mx-auto flex gap-2 pb-2">
              {files.map((f) => (
                <span key={f.name} className="text-[11px] text-zinc-400 bg-zinc-900 border border-[#1e1e24] px-2.5 py-1 rounded-lg flex items-center gap-1.5">
                  <Paperclip size={10} />{f.name}
                  <button onClick={() => setFiles((prev) => prev.filter((p) => p.name !== f.name))} className="text-zinc-600 hover:text-zinc-400"><X size={10} /></button>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="px-6 pb-5 pt-2">
          <form onSubmit={handleSubmit} className="max-w-3xl mx-auto relative">
            <div className="flex items-end gap-2 bg-[#0f0f12] border border-[#1e1e24] rounded-2xl px-4 py-3 focus-within:border-zinc-700 transition-colors shadow-lg">
              <button type="button" onClick={() => fileRef.current?.click()} className="p-1 text-zinc-600 hover:text-zinc-400 transition-colors shrink-0 mb-0.5">
                <Paperclip size={16} />
              </button>
              <input ref={fileRef} type="file" multiple accept="image/*,.pdf,.csv,.txt,.md,.json,.docx" onChange={handleFileSelect} className="hidden" />
              <textarea ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder="Escribe un mensaje..." rows={1} className="flex-1 bg-transparent text-[14px] text-white placeholder-zinc-600 outline-none resize-none max-h-40 leading-relaxed" disabled={loading} />
              <button type="submit" disabled={loading || (!input.trim() && files.length === 0)} className="p-2 rounded-xl bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-150 shrink-0 mb-0.5">
                <Send size={14} />
              </button>
            </div>
            <p className="text-center text-[11px] text-zinc-700 mt-2.5">Shift+Enter para nueva linea</p>
          </form>
        </div>
      </div>
    </div>
  );
}
