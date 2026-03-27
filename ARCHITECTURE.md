# QYNE v1 — Architecture Plan

## Design Principles
1. Each service owns its own database. No shared databases.
2. Services communicate only via HTTP APIs. No direct SQL between services.
3. Agno uses SQLite + LanceDB (embedded, like the original nexus.py).
4. If a service crashes, others keep running.

## Services (12)

| Service | Database | Purpose |
|---------|----------|---------|
| PostgreSQL | - | Shared instance, 2 separate databases |
| Redis | - | Directus cache |
| Reranker (Infinity) | - | Local reranker, BAAI/bge-reranker-base |
| RustFS | - | S3-compatible object storage |
| Directus | PostgreSQL (directus_db) | CMS + REST/GraphQL + MCP Server |
| Agno | SQLite + LanceDB (embedded) | AgentOS, AI agents |
| Frontend | - | Next.js + CopilotKit (AG-UI) |
| n8n | SQLite (embedded) | Workflow automation |
| Prefect Server | PostgreSQL (prefect_db) | Workflow orchestration |
| Prefect Worker | - | Executes flows |
| Uptime Kuma | SQLite (embedded) | Health monitoring |
| Traefik | - | Reverse proxy + SSL |

## Database Layout

```
PostgreSQL (1 instance)
├── directus_db (owner: directus_user) — Directus only
└── prefect_db  (owner: prefect_user)  — Prefect only

Agno (embedded, no PostgreSQL)
├── /data/agno/nexus.db     — SQLite (sessions, memory, history)
└── /data/agno/lancedb/     — LanceDB (embeddings, knowledge)

n8n (embedded, no PostgreSQL)
└── /data/n8n/              — SQLite (workflows, executions)

Uptime Kuma (embedded)
└── /data/uptime-kuma/      — SQLite
```

## Connections (all HTTP, no SQL cross-service)

```
Frontend ---AG-UI---> Agno
Agno ------MCP-----> Directus (read/write collections)
Agno ------REST----> Directus (business logic tools)
Agno ------HTTP----> Prefect (trigger flows)
n8n -------Node----> Directus (CRUD + triggers)
Workers ---REST----> Directus (save scraped data)
Workers ---LanceDB-> /data/agno/lancedb/ (shared volume for embeddings)
Directus --SQL-----> PostgreSQL (directus_db only)
Prefect ---SQL-----> PostgreSQL (prefect_db only)
Directus --S3-----> RustFS (file storage)
```

## Internet Exposure
- Frontend (/): Internet via Traefik
- WhatsApp webhook (/whatsapp/webhook): Internet via Traefik
- Everything else: Tailscale only

## Files to Create
- docker-compose.yml
- config/postgres/init/00-init-databases.sql
- config/redis/redis.conf
- config/traefik/traefik.yml
- config/traefik/dynamic/routes.yml
- .env.example
- .gitignore
- setup.sh
- README.md
- services/agno/ (from nexus-ui repo, adapted)
- services/frontend/ (from nexus-ui)
- services/workers/ (Prefect flows)
