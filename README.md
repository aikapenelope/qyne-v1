# QYNE v1

Plataforma empresarial unificada. Cada servicio es independiente con su propia base de datos. Directus es la fuente de verdad para datos de negocio. Los servicios se comunican solo via HTTP APIs.

## Quick Start

```bash
git clone https://github.com/aikapenelope/qyne-v1.git
cd qyne-v1
chmod +x setup.sh && ./setup.sh
# Edit .env with your API keys, then:
docker compose restart agno
```

## Services (12)

| Service | Database | Port | Purpose |
|---------|----------|------|---------|
| PostgreSQL | - | 5432 | 2 databases: directus_db, prefect_db |
| Redis | - | 6379 | Directus cache |
| RustFS | files on disk | 9000/9001 | S3-compatible object storage |
| Reranker | model in memory | 7997 | Infinity (BAAI/bge-reranker-base) |
| Directus | PostgreSQL (directus_db) | 8055 | CMS + REST/GraphQL + MCP Server |
| Agno | SQLite + LanceDB | 8000 | AgentOS (identical to original nexus.py) |
| Frontend | - | 3000 | Next.js + CopilotKit (AG-UI) |
| n8n | SQLite | 5678 | Deterministic automations |
| Prefect | PostgreSQL (prefect_db) | 4200 | Workflow orchestration |
| Prefect Worker | - | - | Executes flows (scraping, ETL) |
| Uptime Kuma | SQLite | 3001 | Health monitoring |
| Traefik | - | 80/443 | Reverse proxy + SSL |

## Data Flow

```
All business data → Directus REST API → PostgreSQL (directus_db)

Agno agents    → POST /items/contacts, /items/tickets (via tools)
n8n workflows  → POST /items/emails, /items/events (via Directus node)
Prefect flows  → POST /items/scraped_data, /items/documents (via httpx)

Agno knowledge → LanceDB (local, /app/data/lancedb/)
Agno sessions  → SQLite (local, /app/data/nexus.db)
```

## Internet Exposure

Only 2 routes exposed via Traefik:
- `/` → Frontend (CopilotKit)
- `/whatsapp/webhook` → Agno (Meta webhook)

Everything else: Tailscale only.

## Dashboards (via Tailscale)

| Dashboard | URL |
|-----------|-----|
| os.agno.com | Connect to `http://<tailscale-ip>:8000` |
| Directus | `http://<tailscale-ip>:8055` |
| n8n | `http://<tailscale-ip>:5678` |
| Prefect | `http://<tailscale-ip>:4200` |
| Uptime Kuma | `http://<tailscale-ip>:3001` |
| RustFS | `http://<tailscale-ip>:9001` |

---

## Roadmap

### Fase 1 — Deploy y verificacion

- [x] 12 servicios con databases aisladas
- [x] Agno identico al repo original (SQLite + LanceDB + sandbox Docker)
- [x] Frontend completo (18 paginas, CopilotKit + AG-UI)
- [x] setup.sh para primer deploy
- [ ] Mergear PR y desplegar en VPS
- [ ] Verificar que los 12 servicios arrancan healthy
- [ ] Corregir errores de deploy si los hay

### Fase 2 — Conectar servicios a Directus

- [ ] Crear colecciones en Directus: contacts, companies, tickets, tasks, conversations, payments, documents, emails, scraped_data
- [ ] Configurar n8n: instalar nodo Directus verificado, crear credenciales con API token
- [ ] Primer workflow n8n: Directus trigger (nuevo item) → notificacion
- [ ] Primer workflow n8n: Gmail → Directus (ingesta de emails)
- [ ] Configurar Prefect: crear deployment para scraper_latam
- [ ] Configurar Prefect: crear deployment para etl_documents
- [ ] Primer schedule Prefect: scraping cada 6h

### Fase 3 — Portar agentes del nexus_legacy.py

- [ ] automation_agent (n8n MCP + Directus MCP)
- [ ] cerebro team (router entre research, knowledge, automation)
- [ ] whatsapp_support_team (whabi, docflow, aurora agents)
- [ ] content_team (trend_scout, scriptwriter, creative_director, analytics)
- [ ] product_dev_team, creative_studio, marketing_latam
- [ ] agentes individuales (dash, pal, onboarding, email, scheduler, invoice)
- [ ] workflows (7) y structured output models (Pydantic)
- [ ] ResponseQualityEval y registry

### Fase 4 — Produccion

- [ ] Dominio + SSL (Let's Encrypt via Traefik)
- [ ] Tailscale en VPS
- [ ] WhatsApp Business API (Meta credentials)
- [ ] Conectar os.agno.com via Tailscale
- [ ] Configurar Uptime Kuma monitors para todos los servicios
- [ ] Backup PostgreSQL → RustFS (Prefect flow)

### Fase 5 — Optimizacion

- [ ] Ajustar memory limits basado en `docker stats`
- [ ] Evaluar RustFS como storage de Directus (crear bucket, cambiar config)
- [ ] Evaluar reranker: conectar Agno a Infinity si mejora la busqueda
- [ ] Evaluar knowledge isolation por proyecto (whabi, docflow, aurora)
