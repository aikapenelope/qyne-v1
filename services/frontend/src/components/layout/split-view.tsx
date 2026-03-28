"use client";

import { useState, useCallback } from "react";
import { PanelLeftClose, PanelLeftOpen, Maximize2, Minimize2 } from "lucide-react";

interface SplitViewProps {
  left: React.ReactNode;
  right: React.ReactNode;
  defaultSplit?: number; // percentage for left panel (default 50)
}

export default function SplitView({ left, right, defaultSplit = 50 }: SplitViewProps) {
  const [split, setSplit] = useState(defaultSplit);
  const [isDragging, setIsDragging] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);

  const handleMouseDown = useCallback(() => {
    setIsDragging(true);
  }, []);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging) return;
      const container = e.currentTarget as HTMLElement;
      const rect = container.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setSplit(Math.max(25, Math.min(75, pct)));
    },
    [isDragging]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  if (rightCollapsed) {
    return (
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {left}
        <button
          onClick={() => setRightCollapsed(false)}
          className="absolute bottom-4 right-4 p-2 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-400 hover:text-white hover:bg-zinc-700 transition-colors z-10"
          title="Abrir panel derecho"
        >
          <PanelLeftOpen size={16} />
        </button>
      </div>
    );
  }

  return (
    <div
      className="flex-1 flex overflow-hidden"
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      style={{ cursor: isDragging ? "col-resize" : "default" }}
    >
      {/* Left panel */}
      <div
        className="flex flex-col overflow-hidden"
        style={{ width: `${split}%` }}
      >
        {left}
      </div>

      {/* Divider */}
      <div
        className="w-1 bg-[#1e1e24] hover:bg-emerald-500/30 cursor-col-resize flex-shrink-0 relative group"
        onMouseDown={handleMouseDown}
      >
        <div className="absolute top-1/2 -translate-y-1/2 -left-3 -right-3 h-8 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="w-1 h-6 rounded-full bg-emerald-500/50" />
        </div>
      </div>

      {/* Right panel */}
      <div
        className="flex flex-col overflow-hidden relative"
        style={{ width: `${100 - split}%` }}
      >
        <div className="absolute top-2 right-2 flex gap-1 z-10">
          <button
            onClick={() => setRightCollapsed(true)}
            className="p-1.5 rounded-lg bg-zinc-900/80 border border-zinc-800 text-zinc-500 hover:text-white hover:bg-zinc-800 transition-colors"
            title="Cerrar panel"
          >
            <PanelLeftClose size={12} />
          </button>
          <button
            onClick={() => setSplit(50)}
            className="p-1.5 rounded-lg bg-zinc-900/80 border border-zinc-800 text-zinc-500 hover:text-white hover:bg-zinc-800 transition-colors"
            title="50/50"
          >
            <Maximize2 size={12} />
          </button>
          <button
            onClick={() => setSplit(35)}
            className="p-1.5 rounded-lg bg-zinc-900/80 border border-zinc-800 text-zinc-500 hover:text-white hover:bg-zinc-800 transition-colors"
            title="Expandir derecho"
          >
            <Minimize2 size={12} />
          </button>
        </div>
        {right}
      </div>
    </div>
  );
}
