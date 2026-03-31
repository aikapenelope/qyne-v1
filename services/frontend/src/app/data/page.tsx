"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Database,
  FolderOpen,
  FileText,
  Users,
  Building2,
  MessageSquare,
  ClipboardList,
  CreditCard,
  Mail,
  Globe,
  Activity,
  Home,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  Loader2,
  Search,
} from "lucide-react";
import PageHeader from "@/components/layout/page-header";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface CollectionInfo {
  name: string;
  icon: typeof Database;
  color: string;
  count: number;
  recent: Record<string, unknown>[];
}

const COLLECTIONS: Array<{ name: string; icon: typeof Database; color: string; label: string }> = [
  { name: "contacts", icon: Users, color: "text-emerald-400", label: "Contactos" },
  { name: "companies", icon: Building2, color: "text-blue-400", label: "Empresas" },
  { name: "conversations", icon: MessageSquare, color: "text-violet-400", label: "Conversaciones" },
  { name: "tickets", icon: ClipboardList, color: "text-amber-400", label: "Tickets" },
  { name: "tasks", icon: ClipboardList, color: "text-orange-400", label: "Tareas" },
  { name: "payments", icon: CreditCard, color: "text-green-400", label: "Pagos" },
  { name: "documents", icon: FileText, color: "text-cyan-400", label: "Documentos" },
  { name: "emails", icon: Mail, color: "text-pink-400", label: "Emails" },
  { name: "scraped_data", icon: Globe, color: "text-yellow-400", label: "Datos Scrapeados" },
  { name: "events", icon: Activity, color: "text-red-400", label: "Eventos" },
  { name: "properties", icon: Home, color: "text-teal-400", label: "Propiedades" },
];

/* ------------------------------------------------------------------ */
/* Data fetching                                                       */
/* ------------------------------------------------------------------ */

async function fetchCollection(name: string, limit = 5): Promise<{ count: number; items: Record<string, unknown>[] }> {
  try {
    const [countResp, itemsResp] = await Promise.all([
      fetch(`/api/proxy/directus/items/${name}?aggregate[count]=id`),
      fetch(`/api/proxy/directus/items/${name}?limit=${limit}&sort=-date_created`),
    ]);
    const countData = await countResp.json();
    const itemsData = await itemsResp.json();
    const count = countData?.data?.[0]?.count?.id || 0;
    return { count: Number(count), items: itemsData?.data || [] };
  } catch {
    return { count: 0, items: [] };
  }
}

/* ------------------------------------------------------------------ */
/* Collection folder component                                         */
/* ------------------------------------------------------------------ */

function CollectionFolder({ col, data, expanded, onToggle }: {
  col: typeof COLLECTIONS[0];
  data: { count: number; items: Record<string, unknown>[] };
  expanded: boolean;
  onToggle: () => void;
}) {
  const Icon = col.icon;

  function renderValue(val: unknown): string {
    if (val === null || val === undefined) return "-";
    if (typeof val === "object") return JSON.stringify(val).slice(0, 60);
    return String(val).slice(0, 80);
  }

  function getItemTitle(item: Record<string, unknown>): string {
    // Properties: show operation + price + city
    if (item.realtor_name || item.external_id) {
      const op = (item.operation as string) || "";
      const price = item.price ? `$${Number(item.price).toLocaleString()}` : "";
      const city = (item.neighborhood as string) || (item.city as string) || "";
      return [op.toUpperCase(), price, city].filter(Boolean).join(" | ") || `ID ${item.id}`;
    }
    return (
      (item.first_name ? `${item.first_name} ${item.last_name || ""}` : "") ||
      (item.title as string) ||
      (item.name as string) ||
      (item.subject as string) ||
      (item.type as string) ||
      (item.intent as string) ||
      (item.product as string) ||
      `ID ${item.id}`
    ).trim();
  }

  return (
    <div className="border border-[#1e1e24] rounded-xl overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/[0.02] transition-colors"
      >
        {expanded ? <ChevronDown size={12} className="text-zinc-600" /> : <ChevronRight size={12} className="text-zinc-600" />}
        <Icon size={16} className={col.color} />
        <span className="text-[13px] font-medium text-white flex-1 text-left">{col.label}</span>
        <span className="text-[11px] text-zinc-600 bg-zinc-900 px-2 py-0.5 rounded">{data.count}</span>
      </button>

      {expanded && (
        <div className="border-t border-[#1e1e24] bg-[#09090b]">
          {data.items.length === 0 ? (
            <div className="px-4 py-3 text-[11px] text-zinc-700">Vacio</div>
          ) : (
            <div className="divide-y divide-[#1e1e24]">
              {data.items.map((item, i) => (
                <div key={i} className="px-4 py-2.5 hover:bg-white/[0.02]">
                  <div className="text-[12px] text-white font-medium">{getItemTitle(item)}</div>
                  <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-1">
                    {Object.entries(item)
                      .filter(([k]) => !["id", "date_created", "date_updated", "user_created", "user_updated"].includes(k))
                      .filter(([, v]) => v !== null && v !== undefined && v !== "")
                      .slice(0, 4)
                      .map(([k, v]) => (
                        <span key={k} className="text-[10px] text-zinc-600">
                          {k}: <span className="text-zinc-400">{renderValue(v)}</span>
                        </span>
                      ))}
                  </div>
                  {typeof item["date_created"] === "string" && (
                    <span className="text-[9px] text-zinc-700 mt-1 block">
                      {new Date(item["date_created"]).toLocaleString("es")}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function DataExplorerPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<Record<string, { count: number; items: Record<string, unknown>[] }>>({});
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");

  const fetchAll = useCallback(async () => {
    setLoading(true);
    const results: Record<string, { count: number; items: Record<string, unknown>[] }> = {};
    await Promise.all(
      COLLECTIONS.map(async (col) => {
        results[col.name] = await fetchCollection(col.name);
      })
    );
    setData(results);
    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const totalItems = Object.values(data).reduce((sum, d) => sum + d.count, 0);
  const activeCollections = Object.values(data).filter((d) => d.count > 0).length;

  const filtered = COLLECTIONS.filter((col) =>
    !search || col.label.toLowerCase().includes(search.toLowerCase()) || col.name.includes(search.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col">
      <PageHeader title="Data Explorer" badge={`${totalItems} items · ${activeCollections} colecciones activas`}>
        <button onClick={fetchAll} className="p-2 rounded-lg text-zinc-600 hover:text-zinc-400 hover:bg-white/5 transition-colors">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </PageHeader>

      <div className="px-6 py-3 border-b border-[#1e1e24]">
        <div className="relative w-[300px]">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar coleccion..."
            className="w-full bg-[#0f0f12] border border-[#1e1e24] rounded-lg pl-8 pr-3 py-1.5 text-[12px] text-white placeholder-zinc-600 outline-none focus:border-zinc-700"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {loading ? (
          <div className="text-center py-12">
            <Loader2 size={20} className="animate-spin mx-auto mb-3 text-zinc-500" />
            <p className="text-[13px] text-zinc-600">Cargando colecciones...</p>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-2">
            {/* Summary cards */}
            <div className="grid grid-cols-5 gap-2 mb-4">
              {COLLECTIONS.slice(0, 5).map((col) => {
                const d = data[col.name] || { count: 0, items: [] };
                const Icon = col.icon;
                return (
                  <div key={col.name} className="bg-[#0f0f12] border border-[#1e1e24] rounded-xl p-3 text-center">
                    <Icon size={16} className={`${col.color} mx-auto mb-1`} />
                    <div className="text-[18px] font-semibold text-white">{d.count}</div>
                    <div className="text-[10px] text-zinc-600">{col.label}</div>
                  </div>
                );
              })}
            </div>

            {/* Collection folders */}
            {filtered.map((col) => (
              <CollectionFolder
                key={col.name}
                col={col}
                data={data[col.name] || { count: 0, items: [] }}
                expanded={expanded.has(col.name)}
                onToggle={() => {
                  const next = new Set(expanded);
                  if (next.has(col.name)) next.delete(col.name);
                  else next.add(col.name);
                  setExpanded(next);
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
