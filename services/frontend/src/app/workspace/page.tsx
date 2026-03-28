"use client";

import { useState } from "react";
import { MessageSquare, Database, FileText, Activity, Globe, Bot } from "lucide-react";
import SplitView from "@/components/layout/split-view";

/* ------------------------------------------------------------------ */
/* Panel selector                                                      */
/* ------------------------------------------------------------------ */

const PANELS = [
  { id: "chat", label: "Chat", icon: MessageSquare, path: "/chat" },
  { id: "data", label: "Data Explorer", icon: Database, path: "/data" },
  { id: "traces", label: "Traces", icon: Activity, path: "/traces" },
  { id: "crm", label: "CRM", icon: FileText, path: "/crm" },
  { id: "agents", label: "Agentes", icon: Bot, path: "/agents" },
  { id: "topology", label: "Topologia", icon: Globe, path: "/topology" },
];

function PanelSelector({ current, onSelect }: { current: string; onSelect: (id: string) => void }) {
  return (
    <div className="flex gap-1 px-2 py-1.5 bg-[#0c0c0f] border-b border-[#1e1e24]">
      {PANELS.map((p) => (
        <button
          key={p.id}
          onClick={() => onSelect(p.id)}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] transition-colors ${
            current === p.id
              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
              : "text-zinc-600 hover:text-zinc-400 hover:bg-white/[0.03]"
          }`}
        >
          <p.icon size={11} />
          {p.label}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Embedded panel (iframe to same app)                                 */
/* ------------------------------------------------------------------ */

function EmbeddedPanel({ path }: { path: string }) {
  return (
    <iframe
      src={path}
      className="w-full h-full border-0 bg-[#09090b]"
      title={path}
    />
  );
}

/* ------------------------------------------------------------------ */
/* Workspace page                                                      */
/* ------------------------------------------------------------------ */

export default function WorkspacePage() {
  const [leftPanel, setLeftPanel] = useState("chat");
  const [rightPanel, setRightPanel] = useState("data");

  const leftPath = PANELS.find((p) => p.id === leftPanel)?.path || "/chat";
  const rightPath = PANELS.find((p) => p.id === rightPanel)?.path || "/data";

  return (
    <div className="h-screen flex flex-col bg-[#09090b]">
      {/* Header */}
      <div className="h-10 flex items-center justify-between px-4 border-b border-[#1e1e24] shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-medium text-white">Workspace</span>
          <span className="text-[10px] text-zinc-600 bg-zinc-900 px-1.5 py-0.5 rounded">Split View</span>
        </div>
        <a href="/" className="text-[11px] text-zinc-600 hover:text-zinc-400 transition-colors">
          Volver al dashboard
        </a>
      </div>

      {/* Split content */}
      <SplitView
        left={
          <div className="h-full flex flex-col">
            <PanelSelector current={leftPanel} onSelect={setLeftPanel} />
            <div className="flex-1 overflow-hidden">
              <EmbeddedPanel path={leftPath} />
            </div>
          </div>
        }
        right={
          <div className="h-full flex flex-col">
            <PanelSelector current={rightPanel} onSelect={setRightPanel} />
            <div className="flex-1 overflow-hidden">
              <EmbeddedPanel path={rightPath} />
            </div>
          </div>
        }
        defaultSplit={50}
      />
    </div>
  );
}
