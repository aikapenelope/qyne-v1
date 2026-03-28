# QYNE v1 — Operations Runbook: Every Automation, Where It Lives, What It Does

## Why This Document Exists

Every enterprise system needs a single source of truth for all automations.
When something fails at 3am, this document tells you: what triggered, what
ran, what it touched, and where to look for logs.

This is standard practice in production systems (Google SRE, Netflix, Stripe).
Without it, automations become invisible infrastructure that nobody understands.

## The 4 Automation Layers

```
Layer 1: DIRECTUS FLOWS    → React to data changes (internal events)
Layer 2: N8N WORKFLOWS     → Connect external services (Gmail, Slack, Telegram)
Layer 3: PREFECT FLOWS     → Execute data pipelines (scraping, ETL, backups)
Layer 4: AGNO AGENTS       → Reason and decide (AI-powered, chat-triggered)
```

Each layer has a specific job. No overlap.

## Decision Matrix: Where Does Each Automation Live?

| Trigger | Simple action (create item, update field) | Call external API | Heavy data processing | AI reasoning needed |
|---------|------------------------------------------|-------------------|----------------------|-------------------|
| Data changes in Directus | **Directus Flow** | **Directus Flow** (Request URL) | **Directus Flow** → Prefect API | N/A |
| External webhook | **Directus Flow** (Webhook trigger) | **n8n** | **n8n** → Prefect API | N/A |
| External service (Gmail, Slack) | **n8n** → Directus | **n8n** | **n8n** → Prefect API | N/A |
| Schedule (cron) | **Directus Flow** (Schedule trigger) | **n8n** (Cron trigger) | **Prefect** (native schedule) | N/A |
| User chat command | N/A | N/A | **Agno** → Prefect API | **Agno** (agent decides) |

**Rule**: Use the simplest layer that can do the job.
- If Directus Flow can do it → use Directus Flow (no extra service)
- If it needs external services → use n8n
- If it needs heavy processing → use Prefect
- If it needs AI reasoning → use Agno

---

## Layer 1: Directus Flows (Internal Event Reactions)

Directus Flows run inside Directus. No external service needed.
Configure from Directus Admin → Settings → Flows.

### DF-001: New Document → Trigger Prefect ETL

| Field | Value |
|-------|-------|
| **Name** | Document ETL Trigger |
| **Trigger** | Event Hook (Action, Non-Blocking) |
| **Scope** | items.create |
| **Collection** | documents |
| **Condition** | status == "pending" |
| **Operation 1** | Request URL: POST http://prefect:4200/api/deployments/{etl-deployment-id}/create_flow_run |
| **Body** | `{"parameters": {"file_paths": []}}` |
| **Operation 2** | Update Data: set status = "processing" on the triggering item |
| **Logs** | Directus Activity log |

**What happens**: User uploads document → Directus creates item with status="pending" → Flow triggers → Prefect ETL parses document → Updates status to "indexed".

### DF-002: Urgent Ticket → Create Follow-up Task

| Field | Value |
|-------|-------|
| **Name** | Urgent Ticket Alert |
| **Trigger** | Event Hook (Action, Non-Blocking) |
| **Scope** | items.create |
| **Collection** | tickets |
| **Condition** | urgency IN ("high", "critical") |
| **Operation 1** | Create Data → tasks collection |
| **Payload** | `{title: "ALERTA: Ticket urgente - {{$trigger.product}}", body: "{{$trigger.summary}}", status: "todo", assigned_to: "ops"}` |
| **Operation 2** | Create Data → events collection |
| **Payload** | `{type: "urgent_ticket", payload: {ticket_id: "{{$trigger.id}}", product: "{{$trigger.product}}", urgency: "{{$trigger.urgency}}"}}` |

**What happens**: Agent logs urgent ticket → Directus Flow creates task for ops team + logs event.

### DF-003: Payment Approved → Follow-up Task

| Field | Value |
|-------|-------|
| **Name** | Payment Follow-up |
| **Trigger** | Event Hook (Action, Non-Blocking) |
| **Scope** | items.update |
| **Collection** | payments |
| **Condition** | status == "approved" |
| **Operation 1** | Create Data → tasks collection |
| **Payload** | `{title: "Verificar acreditacion: {{$trigger.product}} ${{$trigger.amount}}", status: "todo"}` |
| **Operation 2** | Create Data → events collection |
| **Payload** | `{type: "payment_approved", payload: {amount: "{{$trigger.amount}}", method: "{{$trigger.method}}"}}` |

### DF-004: High Lead Score → Sales Alert

| Field | Value |
|-------|-------|
| **Name** | Hot Lead Alert |
| **Trigger** | Event Hook (Action, Non-Blocking) |
| **Scope** | items.update |
| **Collection** | contacts |
| **Condition** | lead_score >= 8 |
| **Operation 1** | Create Data → tasks collection |
| **Payload** | `{title: "Lead caliente: {{$trigger.first_name}} {{$trigger.last_name}} (score={{$trigger.lead_score}})", status: "todo"}` |
| **Operation 2** | Create Data → events collection |
| **Payload** | `{type: "hot_lead", payload: {contact_id: "{{$trigger.id}}", score: "{{$trigger.lead_score}}"}}` |

### DF-005: Health Alert → Escalation

| Field | Value |
|-------|-------|
| **Name** | Health Alert Escalation |
| **Trigger** | Event Hook (Action, Non-Blocking) |
| **Scope** | items.create |
| **Collection** | tasks |
| **Condition** | title STARTS WITH "ALERT:" |
| **Operation 1** | Update Data → same task item |
| **Payload** | `{assigned_to: "ops"}` |

### DF-006: Scheduled Property Scrape

| Field | Value |
|-------|-------|
| **Name** | Property Scrape Schedule |
| **Trigger** | Schedule (CRON) |
| **Interval** | `0 0 */6 * * *` (every 6 hours) |
| **Operation 1** | Request URL: POST http://prefect:4200/api/deployments/{pipeline-id}/create_flow_run |
| **Body** | `{"parameters": {"sites": ["mercadolibre_ve"], "max_pages": 5}}` |

### DF-007: Daily Backup Trigger

| Field | Value |
|-------|-------|
| **Name** | Daily Backup |
| **Trigger** | Schedule (CRON) |
| **Interval** | `0 0 3 * * *` (daily 3am) |
| **Operation 1** | Request URL: POST http://prefect:4200/api/deployments/{backup-id}/create_flow_run |
| **Body** | `{"parameters": {"databases": ["directus_db", "prefect_db"]}}` |

---

## Layer 2: n8n Workflows (External Service Integrations)

n8n handles things Directus cannot: reading Gmail, sending Slack messages,
connecting to Telegram, processing complex multi-service workflows.

Configure from n8n UI → `http://localhost:5678` via SSH tunnel.

### N8N-001: Gmail → Directus (Email Ingestion)

| Field | Value |
|-------|-------|
| **Name** | Gmail Ingestion |
| **Trigger** | Gmail Trigger (polling every 5 min) |
| **Requires** | Gmail OAuth credentials in n8n |
| **Node 1** | Gmail Trigger → new email |
| **Node 2** | Directus: Create Item → emails collection |
| **Fields** | subject, body, sender, has_attachment |
| **Node 3** | IF: has_attachment == true |
| **Node 4** | Directus: Create Item → documents {status: "pending"} |
| **Result** | Email saved in Directus, attachment triggers ETL via DF-001 |

### N8N-002: Slack Notifications

| Field | Value |
|-------|-------|
| **Name** | Slack Notifier |
| **Trigger** | Webhook (called by Directus Flows or Prefect) |
| **Requires** | Slack Bot Token in n8n |
| **Node 1** | Webhook Trigger |
| **Node 2** | Slack: Send Message to #ops channel |
| **Fields** | message from webhook body |

### N8N-003: Telegram Bot

| Field | Value |
|-------|-------|
| **Name** | Telegram Alerts |
| **Trigger** | Webhook (called by Directus Flows) |
| **Requires** | Telegram Bot Token in n8n |
| **Node 1** | Webhook Trigger |
| **Node 2** | Telegram: Send Message |

---

## Layer 3: Prefect Flows (Data Pipelines)

Prefect handles heavy data processing. Triggered by Directus Flows,
n8n, Agno, or cron schedules.

Dashboard: `http://localhost:4200` via SSH tunnel.

### Pipelines (Multi-Stage)

| ID | Name | File | Trigger | Schedule |
|----|------|------|---------|----------|
| PF-001 | Property Pipeline | property_pipeline.py | Agno chat / DF-006 | Every 6h |
| PF-002 | Website Crawler | website_crawler.py | Agno chat | On-demand |

### Individual Flows

| ID | Name | File | Trigger | Schedule |
|----|------|------|---------|----------|
| PF-003 | ETL Documents | etl_documents.py | DF-001 | On-demand |
| PF-004 | Database Backup | database_backup.py | DF-007 | Daily 3am |
| PF-005 | Knowledge Indexer | knowledge_indexer.py | Agno chat | On-demand |
| PF-006 | Data Sync | data_sync.py | Agno chat | Hourly |
| PF-007 | Weekly Report | report_generator.py | Cron | Mon 8am |
| PF-008 | Daily Digest | email_digest.py | Cron | Daily 8am |
| PF-009 | Health Check | health_check.py | Cron | Every 5 min |
| PF-010 | Lead Scorer | lead_scorer.py | Cron | Daily 6am |
| PF-011 | Data Cleanup | data_cleanup.py | Cron | Sun 2am |
| PF-012 | Sentiment Analyzer | sentiment_analyzer.py | Cron | Daily |
| PF-013 | Data Enricher | data_enricher.py | Cron | Daily |
| PF-014 | Export CSV | export_csv.py | Agno chat | On-demand |
| PF-015 | Import CSV | import_csv.py | Agno chat | On-demand |
| PF-016 | Dedup Merger | dedup_merger.py | Agno chat | On-demand |
| PF-017 | Scraper LATAM | scraper_latam.py | Legacy | Every 6h |

---

## Layer 4: Agno Agents (AI-Powered Decisions)

Agno agents are triggered by user chat. They reason about what to do
and call the appropriate tools (Directus REST, Prefect API, MCP).

### Agent-Triggered Automations

| Chat Command | Agent | Action | Downstream |
|-------------|-------|--------|------------|
| "Scrapea propiedades de MercadoLibre" | Automation Agent | trigger_prefect_flow(property_pipeline) | PF-001 |
| "Crawlea docs.agno.com" | Automation Agent | trigger_prefect_flow(website_crawler) | PF-002 |
| "Indexa los documentos pendientes" | Automation Agent | trigger_prefect_flow(knowledge_indexer) | PF-005 |
| "Exporta contactos a CSV" | Automation Agent | trigger_prefect_flow(export_csv) | PF-014 |
| "Que flows corrieron hoy?" | Automation Agent | list_recent_flow_runs() | Prefect API |
| "Guarda este contacto: Juan..." | Support Agent | save_contact() | Directus REST |
| "Cuantas propiedades hay?" | Dash | read Directus MCP | Directus |
| "Investiga sobre X" | Research Agent | web search tools | DuckDuckGo/Tavily |

---

## Complete Event Flow Map

```
EXTERNAL EVENTS                    INTERNAL EVENTS                    SCHEDULED
─────────────                      ───────────────                    ─────────
Gmail email arrives                New document (status=pending)      Every 6h
    │                                  │                                 │
    ▼                                  ▼                                 ▼
n8n (N8N-001)                     Directus Flow (DF-001)            Directus Flow (DF-006)
    │                                  │                                 │
    ▼                                  ▼                                 ▼
Directus emails                   Prefect ETL (PF-003)              Prefect Pipeline (PF-001)
    │                                  │                                 │
    ▼                                  ▼                                 ▼
IF attachment → DF-001            Directus documents                 Directus properties
                                  + LanceDB embeddings               + RustFS images

Urgent ticket created              Payment approved                  Daily 3am
    │                                  │                                 │
    ▼                                  ▼                                 ▼
Directus Flow (DF-002)            Directus Flow (DF-003)            Directus Flow (DF-007)
    │                                  │                                 │
    ▼                                  ▼                                 ▼
Directus tasks + events           Directus tasks + events            Prefect Backup (PF-004)
                                                                         │
                                                                         ▼
                                                                     RustFS backups/

User chat: "Scrapea..."           Lead score >= 8                    Every 5 min
    │                                  │                                 │
    ▼                                  ▼                                 ▼
Agno Automation Agent             Directus Flow (DF-004)            Prefect Health (PF-009)
    │                                  │                                 │
    ▼                                  ▼                                 ▼
Prefect API                       Directus tasks + events            Directus events
    │                                                                IF down → tasks (ALERT)
    ▼                                                                    │
Prefect Pipeline (PF-001)                                                ▼
    │                                                                DF-005 → assign to ops
    ▼
Directus properties + RustFS
```

---

## Troubleshooting Guide

| Symptom | Check First | Check Second | Fix |
|---------|-------------|-------------|-----|
| Prefect flow didn't run | Prefect dashboard (localhost:4200) → Flow Runs | Is deployment paused? | Unpause or trigger manually |
| Directus Flow didn't trigger | Directus Admin → Settings → Flows → check status | Is the flow active? | Toggle on |
| n8n workflow didn't run | n8n UI (localhost:5678) → Executions | Is workflow active? | Toggle on |
| Data not appearing in Directus | Check DIRECTUS_TOKEN is valid | Check agent permissions | Verify token in .env |
| Images not in RustFS | Check RUSTFS_PASSWORD in .env | Check RustFS health | curl rustfs:9000/health |
| Knowledge search returns nothing | Check LanceDB data dir exists | Run knowledge_indexer | PF-005 |
| Agent can't trigger Prefect | Check PREFECT_API_URL env var | Check deployment ID | list_prefect_deployments |

---

## What's Missing (Future Additions)

| Gap | Impact | Solution |
|-----|--------|----------|
| No Slack integration | Can't send alerts to Slack | Configure n8n N8N-002 |
| No Telegram bot | Can't receive commands via Telegram | Configure n8n N8N-003 |
| No email sending | Can't send reports by email | Configure n8n with SMTP |
| No WhatsApp webhook | Can't receive WhatsApp messages | Need domain + SSL + Meta setup |
| No Directus Flows configured | Internal automations not active | Create DF-001 through DF-007 |
| Prefect deployments paused | Scheduled flows not running | Unpause from dashboard |
