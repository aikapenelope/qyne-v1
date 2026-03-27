# QYNE v1

Plataforma empresarial unificada. Cada servicio es independiente, con su propia base de datos, comunicandose solo via HTTP APIs.

## Quick Start

```bash
git clone https://github.com/aikapenelope/qyne-v1.git
cd qyne-v1
chmod +x setup.sh && ./setup.sh
```

## Services (12)

| Service | DB | Port | Access |
|---------|-----|------|--------|
| PostgreSQL | - | 5432 | Internal |
| Redis | - | 6379 | Internal |
| RustFS | - | 9000/9001 | Tailscale |
| Reranker | - | 7997 | Internal |
| Directus | PostgreSQL (directus_db) | 8055 | Tailscale |
| Agno | SQLite + LanceDB | 8000 | Tailscale |
| Frontend | - | 3000 | Internet |
| n8n | SQLite | 5678 | Tailscale |
| Prefect | PostgreSQL (prefect_db) | 4200 | Tailscale |
| Prefect Worker | - | - | Internal |
| Uptime Kuma | SQLite | 3001 | Tailscale |
| Traefik | - | 80/443 | Internet |

## Connections (all HTTP, no SQL cross-service)

```
Frontend ---AG-UI---> Agno ---MCP/REST---> Directus ---SQL---> PostgreSQL (directus_db)
                      Agno ---HTTP-------> Prefect ---SQL---> PostgreSQL (prefect_db)
                      Agno ---embedded---> SQLite + LanceDB (local)
n8n --------Node----> Directus
Workers ----REST----> Directus
Workers ----LanceDB-> shared volume (read-only)
```

Internet: only Frontend (`/`) and WhatsApp webhook (`/whatsapp/webhook`).
