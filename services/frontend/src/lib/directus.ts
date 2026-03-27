/**
 * Directus CRM data layer.
 *
 * Replaces Twenty CRM. Same interface so CRM pages work without changes.
 * Connects to Directus REST API via the Next.js server (SSR) or client-side.
 */

const DIRECTUS_URL =
  process.env.NEXT_PUBLIC_DIRECTUS_URL || "http://directus:8055";
const DIRECTUS_TOKEN = process.env.DIRECTUS_TOKEN || "";

/* ------------------------------------------------------------------ */
/* Generic request helper                                              */
/* ------------------------------------------------------------------ */

async function directusRequest<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${DIRECTUS_URL}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${DIRECTUS_TOKEN}`,
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Directus ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

function extractData<T>(response: unknown): T[] {
  if (!response) return [];
  const r = response as { data?: T[] };
  return r.data || [];
}

/* ------------------------------------------------------------------ */
/* Person (contacts collection)                                        */
/* ------------------------------------------------------------------ */

export interface Person {
  id: number;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  company?: string;
  product?: string;
  lead_score?: number;
  source?: string;
  status?: string;
  notes?: string;
  date_created?: string;
  date_updated?: string;
  // Compat fields for Twenty UI
  jobTitle?: string;
  city?: string;
  companyId?: string;
  createdAt?: string;
}

export function personDisplayName(p: Person): string {
  const parts = [p.first_name, p.last_name].filter(Boolean);
  return parts.length > 0 ? parts.join(" ") : "Sin nombre";
}

export function personEmail(p: Person): string {
  return p.email || "";
}

export function personPhone(p: Person): string {
  return p.phone || "";
}

export const listPeople = async (limit = 50): Promise<Person[]> => {
  const resp = await directusRequest<{ data: Person[] }>(
    `/items/contacts?limit=${limit}&sort=-date_created`
  );
  return (resp.data || []).map((p) => ({
    ...p,
    createdAt: p.date_created,
    companyId: p.company || undefined,
  }));
};

export const createPerson = (data: {
  firstName: string;
  lastName?: string;
  email?: string;
  phone?: string;
  jobTitle?: string;
}) =>
  directusRequest("/items/contacts", {
    method: "POST",
    body: JSON.stringify({
      first_name: data.firstName,
      last_name: data.lastName || "",
      email: data.email || "",
      phone: data.phone || "",
      source: "frontend",
      status: "lead",
    }),
  });

/* ------------------------------------------------------------------ */
/* Company (companies collection)                                      */
/* ------------------------------------------------------------------ */

export interface Company {
  id: number;
  name?: string;
  domain?: string;
  industry?: string;
  employees?: number;
  address?: string;
  date_created?: string;
  // Compat
  domainName?: string;
  createdAt?: string;
}

export const listCompanies = async (limit = 50): Promise<Company[]> => {
  const resp = await directusRequest<{ data: Company[] }>(
    `/items/companies?limit=${limit}&sort=-date_created`
  );
  return (resp.data || []).map((c) => ({
    ...c,
    domainName: c.domain,
    createdAt: c.date_created,
  }));
};

export const createCompany = (data: {
  name: string;
  domain?: string;
  employees?: number;
}) =>
  directusRequest("/items/companies", {
    method: "POST",
    body: JSON.stringify({
      name: data.name,
      domain: data.domain || "",
      employees: data.employees || 0,
    }),
  });

/* ------------------------------------------------------------------ */
/* Task (tasks collection)                                             */
/* ------------------------------------------------------------------ */

export interface Task {
  id: number;
  title?: string;
  body?: string;
  status?: string;
  assigned_to?: string;
  date_created?: string;
  // Compat
  dueAt?: string;
  createdAt?: string;
}

export const listTasks = async (limit = 50): Promise<Task[]> => {
  const resp = await directusRequest<{ data: Task[] }>(
    `/items/tasks?limit=${limit}&sort=-date_created`
  );
  return (resp.data || []).map((t) => ({
    ...t,
    createdAt: t.date_created,
  }));
};

export const createTask = (data: { title: string; body?: string }) =>
  directusRequest("/items/tasks", {
    method: "POST",
    body: JSON.stringify({
      title: data.title,
      body: data.body || "",
      status: "todo",
    }),
  });

/* ------------------------------------------------------------------ */
/* Note (conversations collection — closest equivalent)                */
/* ------------------------------------------------------------------ */

export interface Note {
  id: number;
  title?: string;
  body?: string;
  date_created?: string;
  // Compat
  createdAt?: string;
}

export const listNotes = async (limit = 50): Promise<Note[]> => {
  const resp = await directusRequest<{ data: Note[] }>(
    `/items/conversations?limit=${limit}&sort=-date_created&fields=id,channel,raw_message,intent,date_created`
  );
  return (resp.data || []).map((n: Record<string, unknown>) => ({
    id: n.id as number,
    title: (n.intent as string) || (n.channel as string) || "Conversacion",
    body: (n.raw_message as string) || "",
    date_created: n.date_created as string,
    createdAt: n.date_created as string,
  }));
};

export const createNote = (data: { title: string; body: string }) =>
  directusRequest("/items/conversations", {
    method: "POST",
    body: JSON.stringify({
      channel: "manual",
      direction: "outbound",
      raw_message: data.body,
      intent: data.title,
      agent_name: "frontend",
    }),
  });
