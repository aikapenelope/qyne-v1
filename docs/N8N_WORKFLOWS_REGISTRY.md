# QYNE v1 — n8n Workflows Registry

## Overview

n8n handles event-driven automations that react to changes in Directus
or external services. Unlike Prefect (scheduled/triggered data pipelines),
n8n is for real-time reactive workflows.

**Access**: `http://localhost:5678` via SSH tunnel.
**Credentials**: admin / (see Pulumi ESC `nexus/secrets` → N8N_PASSWORD)
**Version**: 2.13.4 (latest stable)

## Planned Workflows

### 1. Gmail → Directus (Email Ingestion)

**Trigger**: Gmail polling (every 5 minutes) or IMAP push.
**Purpose**: Automatically capture incoming emails in Directus for agent access.

```
Gmail (new email)
    │
    ├── Directus Node: Create Item → emails collection
    │   {subject, body, sender, has_attachment, date_created}
    │
    ├── IF has attachment:
    │   ├── Download attachment
    │   ├── Upload to RustFS (HTTP Request node)
    │   └── Directus Node: Create Item → documents {status: "pending"}
    │       (triggers Knowledge Indexer via Prefect)
    │
    └── IF sender matches contact:
        └── Directus Node: Update Item → contacts {notes: "Email received"}
```

**n8n Nodes**: Gmail Trigger → IF → Directus → HTTP Request (RustFS)

### 2. Directus Trigger → Notifications

**Trigger**: Directus webhook (item created/updated).
**Purpose**: React to CRM changes in real-time.

```
Directus Trigger (tickets collection, new item)
    │
    ├── IF urgency == "high" or urgency == "critical":
    │   └── Slack/Telegram notification
    │       "🚨 Ticket urgente: {product} - {summary}"
    │
    ├── IF type == "escalation":
    │   └── Email to team
    │       "Escalacion: {client} necesita atencion humana"
    │
    └── Log to Directus events
        {type: "notification_sent", payload: {ticket_id, channel}}
```

**n8n Nodes**: Directus Trigger → Switch → Slack/Email → Directus

### 3. New Document → Prefect ETL

**Trigger**: Directus webhook (documents collection, status="pending").
**Purpose**: Bridge between Directus and Prefect for document processing.

```
Directus Trigger (documents, item created, status="pending")
    │
    └── HTTP Request → POST prefect:4200/api/deployments/{etl-id}/create_flow_run
        parameters: {file_paths: ["/path/to/doc"]}
```

**n8n Nodes**: Directus Trigger → HTTP Request (Prefect API)

### 4. Payment Approved → Invoice Flow

**Trigger**: Directus webhook (payments collection, status="approved").
**Purpose**: Generate follow-up tasks when a payment is confirmed.

```
Directus Trigger (payments, status changed to "approved")
    │
    ├── Directus Node: Create Item → tasks
    │   {title: "Verificar acreditacion: {client}", status: "todo"}
    │
    ├── Directus Node: Create Item → events
    │   {type: "payment_approved", payload: {amount, method, client}}
    │
    └── Email notification to finance team
```

**n8n Nodes**: Directus Trigger → Directus (create task) → Email

### 5. Scheduled Scrape Trigger

**Trigger**: Cron schedule (every 6 hours).
**Purpose**: Trigger Prefect property pipeline on schedule via n8n (alternative to Prefect schedules).

```
Cron Trigger (0 */6 * * *)
    │
    └── HTTP Request → POST prefect:4200/api/deployments/{pipeline-id}/create_flow_run
        parameters: {sites: ["mercadolibre_ve"], max_pages: 5}
```

**n8n Nodes**: Cron → HTTP Request (Prefect API)

### 6. Contact Score Alert

**Trigger**: Directus webhook (contacts collection, lead_score updated).
**Purpose**: Alert sales team when a high-value lead is detected.

```
Directus Trigger (contacts, lead_score changed)
    │
    ├── IF lead_score >= 8:
    │   ├── Slack: "🔥 Hot lead: {name} ({company}) score={lead_score}"
    │   └── Directus: Create task → "Contactar lead caliente: {name}"
    │
    └── IF lead_score >= 5 AND lead_score < 8:
        └── Directus: Create task → "Seguimiento lead: {name}"
```

**n8n Nodes**: Directus Trigger → IF → Slack → Directus

### 7. Health Alert Escalation

**Trigger**: Directus webhook (tasks collection, title contains "ALERT").
**Purpose**: Escalate health check alerts to multiple channels.

```
Directus Trigger (tasks, title starts with "ALERT:")
    │
    ├── Slack notification (ops channel)
    ├── Email to admin
    └── Directus: Update task → assigned_to: "ops-oncall"
```

**n8n Nodes**: Directus Trigger → Slack → Email → Directus

## n8n Configuration Notes

### Directus Connection
- **URL**: `http://directus:8055` (internal Docker network)
- **Token**: Use the agent support token (read + create, no delete)
- **Trigger**: Directus has native webhook support — n8n's Directus Trigger node creates the webhook automatically

### Prefect Connection
- **URL**: `http://prefect:4200/api` (internal Docker network)
- **Auth**: None (Prefect OSS has no auth)
- **Trigger flows**: `POST /deployments/{id}/create_flow_run`

### Environment Variables
```
N8N_SECURE_COOKIE=false          # Safari compatibility via SSH tunnel
N8N_COMMUNITY_PACKAGES_ENABLED=true
N8N_RUNNERS_ENABLED=false        # Prevent memory leaks
N8N_DEFAULT_BINARY_DATA_MODE=filesystem
```

## How to Create a Workflow in n8n

1. Open `http://localhost:5678` via SSH tunnel
2. Click "Add workflow"
3. Add trigger node (Directus Trigger, Cron, Gmail, etc.)
4. Add action nodes (Directus, HTTP Request, Slack, Email)
5. Connect nodes
6. Test with "Execute workflow"
7. Activate (toggle on)

## n8n vs Prefect: When to Use Which

| Use Case | n8n | Prefect |
|----------|-----|---------|
| React to Directus changes | Yes (webhook trigger) | No (no webhooks in OSS) |
| Send notifications | Yes (Slack, Email, Telegram) | No (use n8n) |
| Schedule data pipelines | Possible but not ideal | Yes (native schedules) |
| Multi-stage data processing | No (not designed for ETL) | Yes (tasks, retries, caching) |
| Bridge webhooks → Prefect | Yes (HTTP Request node) | N/A |
| Visual workflow builder | Yes (drag and drop) | No (Python code) |
| Heavy data processing | No (memory limits) | Yes (workers, parallelism) |
