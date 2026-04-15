# QYNE

Multi-brand marketing platform. Manages content, SEO, social media, research,
CRM, customer support, and analytics for multiple businesses from a single
dashboard.

## Architecture

```
Prefect ─── deterministic backbone (all marketing flows)
  │
  ├── tasks: invoke AgNO agents, Crawl4AI, httpx, Postiz CLI
  │
AgNO ───── AI intelligence (8 agents)
  │
  ├── 4 Prefect agents: Researcher, Writer, Analyst, Strategist
  ├── 4 real-time agents: Support Router, Support Agent, Dash, Pal
  │
Directus ── data layer, CRM, Kanban, triggers
  │
Postiz ──── social media publishing (30+ platforms)
```

Prefect controls the flow. AgNO provides intelligence at specific steps.
Directus stores everything. Postiz publishes.

## Services

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL 16 | 5432 | 2 databases: directus_db, prefect_db |
| Redis 7 | 6379 | Directus cache |
| RustFS | 9000/9001 | S3-compatible object storage |
| Directus | 8055 | CMS + REST/GraphQL + MCP Server + CRM Kanban |
| AgNO | 8000 | AgentOS (8 agents, 1 team) |
| Frontend | 3000 | Next.js + CopilotKit (AG-UI) |
| Prefect Server | 4200 | Workflow orchestration + dashboard |
| Prefect Worker | - | Executes all marketing flows |
| Postiz | - | Social media scheduling + publishing |
| Uptime Kuma | 3001 | Health monitoring |
| Traefik | 80/443 | Reverse proxy + SSL |

## The 8 Agents

| Agent | Role | Invoked by |
|-------|------|-----------|
| **Researcher** | Web search, knowledge base, competitor analysis, keyword research | Prefect tasks |
| **Writer** | Articles, social posts, scripts, emails, copy, invoices | Prefect tasks |
| **Analyst** | Performance reports, content evaluation, SEO audit, code review | Prefect tasks |
| **Strategist** | Weekly plans, channel allocation, cross-brand insights | Prefect tasks |
| **Support Router** | Routes WhatsApp messages to correct product context | AgNO real-time |
| **Support Agent** | Customer support with CRM tools and knowledge base | AgNO real-time |
| **Dash** | Business analytics, ad-hoc questions about metrics | AgNO real-time |
| **Pal** | Personal assistant with persistent memory | AgNO real-time |

## Prefect Marketing Flows

| Flow | Schedule | What it does |
|------|----------|-------------|
| content_production | On-demand | Research → write 3 variants → evaluate → store |
| seo_content | On-demand | Keywords → article → audit loop → publish-ready MDX |
| social_media_generation | Daily | Read weekly plan → write posts per platform → audit → store |
| social_media_publish | Daily | Read approved posts → Postiz CLI → log analytics |
| deep_research | On-demand | Parallel research (N angles) → quality gate → synthesize |
| competitor_intel | Weekly | Parallel (content + pricing + reviews) → synthesize |
| growth_strategist | Mon 7am | Read analytics + CRM + learnings → produce weekly plan |
| experiment_analysis | Fri 5pm | Compare A/B variants → declare winners → store learnings |
| content_recycling | Weekly | Find top performers → generate variations → re-schedule |
| lead_scoring | Daily 6am | Calculate scores → create deals automatically |
| sentiment_analysis | Daily | Keyword-based sentiment scoring (0 tokens) |
| sla_compliance | Daily | Calculate FRT/TTR → update SLA dashboard |

Plus existing infrastructure flows: website_crawler, database_backup,
health_check, data_sync, data_cleanup, etl_documents, knowledge_indexer,
export_csv, import_csv, dedup_merger, data_enricher.

## Brands

| Brand | Product | Pricing |
|-------|---------|---------|
| Whabi | WhatsApp Business CRM | $49 / $149 / custom |
| Docflow | Electronic Health Records | $99 / $249 / custom |
| Aurora | Voice-first PWA | $0 / $29 / $79 |

## Quick Start

```bash
git clone https://github.com/aikapenelope/qyne-v1.git
cd qyne-v1
chmod +x setup.sh && ./setup.sh
# Edit .env with your API keys, then:
docker compose up -d
```

## Access (via Tailscale)

| Dashboard | URL |
|-----------|-----|
| NEXUS (main) | `http://<tailscale-ip>:3000` |
| AgentOS | `http://<tailscale-ip>:8000` |
| Directus | `http://<tailscale-ip>:8055` |
| Prefect | `http://<tailscale-ip>:4200` |
| Uptime Kuma | `http://<tailscale-ip>:3001` |

Internet exposure: only `/` (frontend) and `/whatsapp/webhook` via Traefik.
Everything else: Tailscale only.

## Data Flow

```
Prefect flows → invoke AgNO agents → structured output (Pydantic)
                                   → store in Directus via REST API
                                   → publish via Postiz CLI

AgNO real-time → WhatsApp/chat → Directus CRM (contacts, tickets, conversations)

Crawl4AI → Directus documents → LanceDB (RAG knowledge base)
```

## Documentation

| Document | What it covers |
|----------|---------------|
| [EXECUTIVE_SUMMARY.md](docs/EXECUTIVE_SUMMARY.md) | Quick reference of the entire system |
| [MARKETING_PLATFORM.md](docs/MARKETING_PLATFORM.md) | All 35 capabilities, architecture, decisions, roadmap |
| [TECHNICAL_ROADMAP.md](docs/TECHNICAL_ROADMAP.md) | Detailed migration plan with code references |
| [MIGRATION_ROADMAP.md](docs/MIGRATION_ROADMAP.md) | Agent mapping (42 → 8) and file structure |
| [ARCHITECTURE_DECISIONS.md](docs/ARCHITECTURE_DECISIONS.md) | Technical decisions with research backing |
| [CAPABILITIES.md](docs/CAPABILITIES.md) | Raw inventory of current codebase |

## Project Structure

```
services/
  agno/                    # AgNO AgentOS
    agents/                # 8 agents (researcher, writer, analyst, strategist,
                           #           support, dash, pal)
    app/                   # Config, models, shared components
    tools/                 # Directus REST, Postiz CLI, agent invoker, sandbox
    skills/                # 24 domain skills (seo-geo, content-strategy, etc.)
    knowledge/             # Documents for RAG indexing
  workers/                 # Prefect flows
    flows/                 # All marketing + infrastructure flows
  frontend/                # Next.js + CopilotKit dashboard
config/                    # PostgreSQL, Redis, Traefik configs
docker-compose.yml
setup.sh
```

## License

See [LICENSE](LICENSE).
