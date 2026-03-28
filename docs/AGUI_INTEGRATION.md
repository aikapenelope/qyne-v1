# QYNE v1 — Agno + CopilotKit + AG-UI Integration Guide

## Architecture Overview

QYNE has TWO communication channels between frontend and Agno:

```
Channel 1: API Direct (for pages: agents, teams, chat, traces, CRM)
┌──────────┐     /api/proxy/agno/*     ┌──────────┐     HTTP     ┌──────────┐
│  Browser  │ ──────────────────────► │  Next.js  │ ──────────► │   Agno   │
│  (pages)  │ ◄────────────────────── │  (proxy)  │ ◄────────── │  :8000   │
└──────────┘        JSON               └──────────┘    JSON      └──────────┘

Channel 2: AG-UI Protocol (for CopilotKit overlay/sidebar only)
┌──────────┐    /api/copilotkit     ┌──────────┐   AG-UI SSE   ┌──────────┐
│  Browser  │ ──────────────────► │  Next.js  │ ──────────► │   Agno   │
│(CopilotKit│ ◄────────────────── │ (runtime) │ ◄────────── │  /agui   │
│  overlay) │    SSE stream        └──────────┘   events     └──────────┘
└──────────┘
```

### Channel 1: API Direct (Primary)

This is how ALL pages get data. It uses a simple proxy pattern:

1. Browser calls `/api/proxy/agno/agents`
2. Next.js API route (server-side) calls `http://agno:8000/agents`
3. Returns JSON to browser

**Used by**: Agents page, Teams page, Workflows page, Chat page, Traces page,
Topology page, Data Explorer, CRM, Memory, Knowledge, History, Analytics

**Code**: `src/lib/api.ts` → `const API_URL = "/api/proxy/agno"`

**Proxy**: `src/app/api/proxy/agno/[...path]/route.ts`

### Channel 2: AG-UI Protocol (Secondary)

This is ONLY for the CopilotKit overlay (the floating chat button on the dashboard).
It uses the AG-UI streaming protocol, not regular HTTP.

1. CopilotKit React component sends message to `/api/copilotkit`
2. Next.js CopilotRuntime forwards to `http://agno:8000/agui` via HttpAgent
3. Agno streams AG-UI events (text, tool calls, state) back
4. CopilotKit renders the streaming response

**Used by**: CopilotKit overlay on dashboard page ONLY

**Code**: `src/app/api/copilotkit/route.ts`

**Requires**: OpenAIAdapter (needs OPENAI_API_KEY as fallback adapter)

## Why Two Channels?

The original Agno repo (nexus-ui) was designed this way:
- **Pages** (agents, chat, traces) use the Agno REST API directly
- **CopilotKit overlay** uses AG-UI for streaming chat experience

The chat page (`/chat`) does NOT use CopilotKit. It uses `runTeam()` from
`api.ts` which calls the Agno REST API. This is intentional — the REST API
supports approvals, followups, and tool calls that CopilotKit doesn't handle.

## Docker Networking

In Docker, the browser cannot access `agno:8000` (internal hostname).
The solution is server-side proxy routes:

```
Browser → /api/proxy/agno/agents → Next.js server → http://agno:8000/agents
Browser → /api/proxy/directus/items/contacts → Next.js server → http://directus:8055/items/contacts
```

The proxy routes are in:
- `src/app/api/proxy/agno/[...path]/route.ts`
- `src/app/api/proxy/directus/[...path]/route.ts`

## Configuration

### Environment Variables (Frontend Container)

| Variable | Value | Used By |
|----------|-------|---------|
| HOSTNAME | 0.0.0.0 | Next.js standalone binding |
| NEXT_PUBLIC_API_URL | http://agno:8000 | NOT USED (legacy, proxy replaces it) |
| AGNO_AGUI_URL | http://agno:8000/agui | CopilotKit route (server-side) |
| NEXT_PUBLIC_DIRECTUS_URL | http://directus:8055 | NOT USED (proxy replaces it) |
| DIRECTUS_TOKEN | (agent token) | Directus proxy (server-side) |
| GROQ_API_KEY | (groq key) | CopilotKit OpenAIAdapter fallback |

### Key Files

| File | Purpose |
|------|---------|
| `src/lib/api.ts` | API client for Agno REST. Uses `/api/proxy/agno` |
| `src/lib/directus.ts` | API client for Directus REST. Uses `/api/proxy/directus` |
| `src/app/api/proxy/agno/[...path]/route.ts` | Server-side proxy to Agno |
| `src/app/api/proxy/directus/[...path]/route.ts` | Server-side proxy to Directus |
| `src/app/api/copilotkit/route.ts` | CopilotKit + AG-UI runtime |
| `src/app/chat/page.tsx` | Chat page (uses api.ts, NOT CopilotKit) |
| `src/app/page.tsx` | Dashboard (has CopilotKit overlay) |

## Agno Endpoints

| Endpoint | Method | Returns | Used By |
|----------|--------|---------|---------|
| `/` | GET | `{name, id, version}` | Health check |
| `/health` | GET | `{status: "ok"}` | Docker healthcheck |
| `/agents` | GET | `Agent[]` | Agents page |
| `/agents/{id}/runs` | POST | Run result | Chat, Topology |
| `/teams` | GET | `Team[]` | Teams page |
| `/teams/{id}/runs` | POST | Run result | Chat |
| `/workflows` | GET | `Workflow[]` | Workflows page |
| `/traces` | GET | `{data: Trace[], meta}` | Traces page |
| `/traces/{id}` | GET | `{data: Trace}` | Trace detail |
| `/config` | GET | Full OS config | AgentOS UI |
| `/agui` | POST | AG-UI SSE stream | CopilotKit |
| `/approvals` | GET | `Approval[]` | Approvals page |

## CopilotKit Setup (AG-UI)

CopilotKit requires an `OpenAIAdapter` as service adapter even when using
AG-UI agents. This is a CopilotKit requirement — the adapter is a fallback
for when no AG-UI agent handles the request.

```typescript
// route.ts
const serviceAdapter = new OpenAIAdapter();
// Needs OPENAI_API_KEY in environment
// Alternative: use GroqAdapter or pass OpenAI instance with Groq base URL
```

For production without OpenAI key, use Groq as the adapter:
```typescript
import OpenAI from "openai";
const openai = new OpenAI({
  apiKey: process.env.GROQ_API_KEY,
  baseURL: "https://api.groq.com/openai/v1",
});
const serviceAdapter = new OpenAIAdapter({ openai, model: "llama-3.1-8b-instant" });
```

## Common Issues

### "No agents visible"
- Check: `curl localhost:3000/api/proxy/agno/agents` returns 42 agents
- If yes: browser cache. Hard refresh (Ctrl+Shift+R)
- If no: proxy route not built. Rebuild frontend

### "Chat Error: Load failed"
- This is the CopilotKit overlay, NOT the chat page
- Cause: OPENAI_API_KEY not set for OpenAIAdapter
- Fix: Set GROQ_API_KEY in frontend env and use Groq adapter
- Note: The main chat page (/chat) works independently of CopilotKit

### "Traces empty"
- Agno returns `{data: [...]}` not flat array
- `listTraces()` in api.ts must extract `.data`
- Check: `curl localhost:3000/api/proxy/agno/traces?limit=5`

### "Data Explorer empty"
- Check: `curl localhost:3000/api/proxy/directus/items/contacts`
- If empty response: DIRECTUS_TOKEN not set in frontend env
- If error: Directus not healthy

## Production Checklist

- [ ] All pages use `/api/proxy/agno` (not NEXT_PUBLIC_API_URL)
- [ ] No page has hardcoded `localhost:8000` or `agno:8000`
- [ ] CopilotKit has valid adapter key (Groq or OpenAI)
- [ ] Proxy routes handle errors gracefully
- [ ] DIRECTUS_TOKEN set in frontend container
- [ ] Frontend rebuilt after any api.ts or route changes
