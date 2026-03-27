# QYNE v1 — L4 Enterprise Flows

## How QYNE Works (The Single Dashboard Principle)

You give orders from ONE place (the NEXUS dashboard). You never need to open
Prefect, n8n, or Directus for normal operations. Those dashboards exist only
for debugging when something fails.

```
YOU (NEXUS chat)
    │
    │ "Scrapea propiedades de MercadoLibre"
    ▼
NEXUS Master (router)
    │
    ▼
Automation Agent
    │
    ├─► Prefect API: trigger scraper flow
    ├─► Directus: log the command as event
    └─► Response: "Scraping iniciado. Te aviso cuando termine."
         │
         ▼
    Prefect Worker (background)
         │
         ├─► Crawl4AI: fetch pages
         ├─► Parse: extract data + image URLs
         └─► Directus: save to scraped_data collection
              │
              ▼
         YOU (NEXUS CRM tab)
              │
              └─► See results in scraped_data table
```

## All L4 Flows

### Flow 1: Scraping (Chat → Prefect → Directus)

**Trigger**: You say "Scrapea [URL]" in chat
**Agent**: Automation Agent → calls Prefect API
**Worker**: scraper_latam flow
**Result**: Data appears in Directus `scraped_data` collection
**View**: CRM tab → scraped_data, or ask Dash "cuantas propiedades se scrapearon"

```
Chat order → Automation Agent → POST prefect:4200/api/deployments/{id}/create_flow_run
                                  → parameters: {urls: ["https://..."]}
```

### Flow 2: Document Processing (Upload → n8n → Prefect → LanceDB)

**Trigger**: Upload PDF/DOCX in frontend, or say "Procesa este documento"
**Pipeline**:
1. Frontend uploads file to RustFS (S3)
2. Creates item in Directus `documents` with status="pending"
3. n8n detects new item (Directus trigger) → calls Prefect API
4. Prefect worker: Docling parses → text to Directus → embeddings to LanceDB
5. Status updated to "indexed"

**View**: Ask Knowledge Agent "que dice el documento X"

### Flow 3: Daily Operations (Automatic, no human trigger)

| Time | Flow | What happens |
|------|------|-------------|
| 03:00 | database_backup | pg_dump → RustFS |
| 06:00 | lead_scorer | Recalculate contact scores |
| 08:00 | email_digest | Daily summary → Directus events |
| Every 5m | health_check | Verify services, alert if down |
| Every 6h | scraper_latam | Scrape configured URLs |

### Flow 4: Weekly Operations

| Day | Flow | What happens |
|-----|------|-------------|
| Monday 08:00 | report_generator | Weekly metrics report |
| Sunday 02:00 | data_cleanup | Find duplicates, old data (report only) |

### Flow 5: On-Demand (Triggered by chat or n8n)

| Trigger | Flow | What happens |
|---------|------|-------------|
| "Scrapea [URL]" | scraper_latam | Scrape specific URLs |
| Upload document | etl_documents | Parse + index in LanceDB |
| "Indexa los documentos pendientes" | knowledge_indexer | Batch index pending docs |
| "Sincroniza contactos" | data_sync | Sync between collections |

### Flow 6: Customer Interaction (WhatsApp/Chat → Agno → Directus)

```
Customer message
    │
    ▼
WhatsApp Support Team (router)
    │
    ├─► Whabi Support / Docflow Support / Aurora Support
    │       │
    │       ├─► save_contact() → Directus contacts
    │       ├─► log_ticket() → Directus tickets
    │       ├─► log_conversation() → Directus conversations
    │       ├─► confirm_payment() → Directus payments (requires approval)
    │       └─► escalate_to_human() → Directus tasks
    │
    └─► Response to customer
```

### Flow 7: Content Production (Chat → Team → Files)

```
"Crea un video sobre IA en LATAM"
    │
    ▼
Content Factory (team)
    │
    ├─► Trend Scout: research topic (3 tool calls max)
    ├─► Scriptwriter: 3 storyboard variants (JSON files)
    ├─► Creative Director: evaluate and recommend best variant
    └─► You choose which to produce
```

### Flow 8: Research (Chat → Parallel Scouts → Report)

```
"Investiga a [competitor]"
    │
    ▼
Deep Research Workflow
    │
    ├─► Planner: creates execution plan
    ├─► Scouts (parallel): Tavily + Exa + Firecrawl + WebSearch
    ├─► Quality Gate: enough data?
    └─► Synthesizer: markdown report saved to knowledge/
```

### Flow 9: Competitor Intelligence (Chat → Parallel → Synthesis)

```
"Analiza la competencia de Whabi"
    │
    ▼
Competitor Intel Workflow
    │
    ├─► Content Scout: analyze competitor content
    ├─► Pricing Scout: research competitor pricing
    ├─► Reviews Scout: gather G2/Capterra reviews
    └─► Synthesizer: actionable report
```

### Flow 10: SEO Content (Chat → Workflow → Publish)

```
"Escribe un articulo SEO sobre CRM para WhatsApp"
    │
    ▼
SEO Content Workflow
    │
    ├─► Keyword Researcher: find GEO-optimized topic
    ├─► Article Writer: 1500-2500 word listicle in Spanish
    ├─► SEO Auditor: score and suggest fixes
    └─► Loop: revise until PUBLISH verdict (max 2 rounds)
```

## Where to See Results

| What | Where |
|------|-------|
| Agent conversations | NEXUS Chat + Traces tab |
| CRM data (contacts, tickets) | NEXUS CRM tab |
| Scraped data | NEXUS CRM tab → scraped_data |
| Documents | NEXUS CRM tab → documents |
| Flow execution logs | Prefect dashboard (debugging only) |
| n8n workflow logs | n8n dashboard (debugging only) |
| Directus admin | Directus UI (data management only) |
| Service health | health_check flow → Directus events |
| Weekly reports | report_generator → Directus events |

## The Rule

**Normal operations**: NEXUS dashboard only.
**Something broke**: Prefect dashboard for flow errors, n8n for webhook errors.
**Data management**: Directus admin for bulk edits, schema changes.
