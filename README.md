# QYNE v1

Plataforma empresarial unificada. Cada servicio es independiente, con su propia base de datos, comunicandose solo via HTTP APIs. Directus es la fuente de verdad para todos los datos de negocio.

## Quick Start

```bash
git clone https://github.com/aikapenelope/qyne-v1.git
cd qyne-v1
chmod +x setup.sh && ./setup.sh
# Edit .env with your API keys, then:
docker compose restart agno
```

## Services (12)

| Service | Database | Port | Access | Purpose |
|---------|----------|------|--------|---------|
| PostgreSQL | - | 5432 | Internal | 2 databases separadas (directus_db, prefect_db) |
| Redis | - | 6379 | Internal | Cache para Directus |
| RustFS | - | 9000/9001 | Tailscale | Object storage S3-compatible (documentos, media) |
| Reranker | - | 7997 | Internal | Infinity local (BAAI/bge-reranker-base) |
| Directus | PostgreSQL (directus_db) | 8055 | Tailscale | CMS + REST/GraphQL + MCP Server — fuente de verdad |
| Agno | SQLite + LanceDB | 8000 | Tailscale | AgentOS (AI agents, WhatsApp, AG-UI) |
| Frontend | - | 3000 | Internet | Next.js + CopilotKit |
| n8n | SQLite | 5678 | Tailscale | Automatizaciones deterministas (sin IA) |
| Prefect | PostgreSQL (prefect_db) | 4200 | Tailscale | Orquestacion de workers |
| Prefect Worker | - | - | Internal | Ejecuta flows (scraping, ETL con Docling) |
| Uptime Kuma | SQLite | 3001 | Tailscale | Health monitoring |
| Traefik | - | 80/443 | Internet | Reverse proxy (solo frontend + WhatsApp webhook) |

## Como fluyen los datos — Directus como destino central

Todos los datos de negocio terminan en Directus. Ningun servicio escribe directamente a la base de datos de otro.

```
                    ┌─────────────────────────────────────┐
                    │         DIRECTUS (directus_db)       │
                    │   Fuente de verdad para datos de     │
                    │   negocio. REST API + MCP Server.    │
                    └──────────┬──────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
    Agno (MCP/REST)      n8n (Node nativo)    Prefect (REST)
    Escribe via API      Escribe via API      Escribe via API
          │                    │                    │
    ┌─────┴─────┐        ┌────┴────┐         ┌────┴────┐
    │ SQLite    │        │ SQLite  │         │ Prefect │
    │ LanceDB   │        │ (propio)│         │   DB    │
    │ (propio)  │        └─────────┘         └─────────┘
    └───────────┘
```

### Flujos de datos concretos

**Chat/WhatsApp -> Directus:**
```
Usuario escribe -> Agno procesa -> Agno llama save_contact() -> POST http://directus:8055/items/contacts
                                -> Agno llama log_ticket()    -> POST http://directus:8055/items/tickets
```

**Email -> Directus (determinista, sin IA):**
```
Gmail -> n8n (Directus Trigger Node) -> POST http://directus:8055/items/emails
```

**Scraping -> Directus (determinista, sin IA):**
```
Prefect cron -> Worker ejecuta flow -> Crawl4AI scrape -> POST http://directus:8055/items/scraped_data
```

**Documento -> Directus + Knowledge (determinista + embeddings):**
```
Upload en Directus -> Directus Flow webhook -> n8n -> trigger Prefect ETL flow
                                                    -> Docling parsea documento
                                                    -> POST http://directus:8055/items/documents (texto)
                                                    -> LanceDB insert (embeddings, via volumen compartido)
```

**Directus -> n8n (triggers automaticos):**
```
Nuevo item en Directus -> Directus webhook -> n8n workflow se ejecuta
                                           -> Notificacion Slack/Telegram
                                           -> Sync con servicio externo
```

**Nota sobre n8n triggers:** Directus envia webhooks a n8n dentro de la red Docker (`http://qyne-n8n:5678`). No necesitan internet. Se configuran automaticamente cuando activas un workflow con Directus Trigger Node en n8n.

## Dashboards (todos via Tailscale)

| Dashboard | URL | Funcion |
|-----------|-----|---------|
| os.agno.com | Conecta a `http://<tailscale-ip>:8000` | Agentes, tracing, chat |
| Directus | `http://<tailscale-ip>:8055` | Datos, colecciones, RBAC |
| n8n | `http://<tailscale-ip>:5678` | Workflows de automatizacion |
| Prefect | `http://<tailscale-ip>:4200` | Workers, flows, schedules |
| Uptime Kuma | `http://<tailscale-ip>:3001` | Health monitoring |
| RustFS | `http://<tailscale-ip>:9001` | Object storage |
| Traefik | `http://<tailscale-ip>:8080` | Reverse proxy |

---

## Roadmap

### Fase 1 — Deploy funcional

- [x] 12 servicios con databases aisladas
- [x] Agno con SQLite + LanceDB (como repo original)
- [x] n8n con SQLite (sin PostgreSQL)
- [x] Directus y Prefect con PostgreSQL separado
- [x] Frontend (nexus-ui con CopilotKit + AG-UI)
- [x] Knowledge isolation por proyecto + reranker local
- [x] Docling tool + sandbox DinD + Prefect trigger tool
- [x] setup.sh para primer deploy
- [ ] Deploy en VPS y correccion de errores
- [ ] Crear colecciones en Directus (contacts, companies, tickets, tasks, conversations, payments, documents, emails, scraped_data)

### Fase 2 — Conectar servicios a Directus

- [ ] Configurar n8n: instalar nodo Directus, crear credenciales con API token
- [ ] Workflow n8n: Gmail -> Directus (ingesta de emails)
- [ ] Workflow n8n: Directus trigger -> notificaciones (Slack/Telegram)
- [ ] Workflow n8n: Directus trigger (nuevo documento) -> Prefect ETL flow
- [ ] Configurar Prefect: crear deployments para scraper y ETL
- [ ] Configurar schedules en Prefect (scraping cada 6h, re-embedding diario)

### Fase 3 — Portar agentes

- [ ] Portar automation_agent + cerebro team
- [ ] Portar whatsapp_support_team (whabi, docflow, aurora)
- [ ] Portar content_team + creative_studio
- [ ] Portar agentes individuales (dash, pal, onboarding, email, scheduler, invoice)
- [ ] Portar workflows (7) y structured output models

### Fase 4 — Produccion

- [ ] Dominio + SSL (Let's Encrypt via Traefik)
- [ ] Tailscale en VPS
- [ ] WhatsApp Business API
- [ ] Uptime Kuma monitors
- [ ] Conectar os.agno.com
- [ ] Backup PostgreSQL -> RustFS (Prefect flow)

### Fase 5 — Optimizacion

- [ ] Ajustar memory limits (`docker stats`)
- [ ] Evaluar RustFS como storage de Directus (crear bucket, cambiar config)
- [ ] Evaluar modelo de reranker mas grande si hay RAM
