# QYNE v1 — Prefect Deployment Activation Guide

## How Prefect Deployments Work

A deployment has 3 states:

| State | Schedule runs? | Manual trigger? | Worker picks up? |
|-------|---------------|----------------|-----------------|
| **Active + schedule** | Yes (automatic) | Yes | Yes |
| **Active + no schedule** | No | Yes | Yes |
| **Paused** | No | No (creates Late run) | No |

**Production recommendation**: Keep all deployments **active**. Scheduled ones
run on their cron. On-demand ones only run when triggered. Pausing is for
maintenance windows, not normal operation.

## Current State

### On-Demand Flows (trigger from chat or API)

These have NO schedule. They only run when you tell them to.
**Recommendation: ACTIVE** (already active).

| Deployment | Status | Trigger |
|------------|--------|---------|
| website-crawler-ondemand | ACTIVE | Chat: "Crawlea [URL]" |
| etl-documents-on-demand | ACTIVE | Directus Flow (new document) |
| knowledge-indexer-ondemand | ACTIVE | Chat: "Indexa knowledge" |
| export-csv-ondemand | ACTIVE | Chat: "Exporta [collection]" |
| import-csv-ondemand | ACTIVE | Chat: "Importa [file]" |
| dedup-merger-ondemand | ACTIVE | Chat: "Busca duplicados" |

### Scheduled Flows (automatic cron)

These run automatically on schedule AND can be triggered manually.
**Recommendation: ACTIVATE in phases.**

#### Phase 1: Activate immediately (low risk, high value)

| Deployment | Schedule | Why activate now |
|------------|----------|-----------------|
| **health-check-5min** | Every 5 min | Detects service failures. Creates alert tasks. Zero side effects. |
| **backup-daily-3am** | Daily 3:00 UTC | Database protection. If RustFS isn't configured, it logs a skip. |

#### Phase 2: Activate after first week of operation

| Deployment | Schedule | Why wait |
|------------|----------|---------|
| **daily-digest-8am** | Daily 8:00 UTC | Needs real data to be useful. Wait until you have conversations/tickets. |
| **lead-scorer-daily6am** | Daily 6:00 UTC | Needs contacts with activity. Wait until CRM has data. |
| **sentiment-daily** | Daily 7:00 UTC | Needs conversations. Wait until chat is being used. |
| **data-enricher-daily** | Daily 5:00 UTC | Needs contacts. Wait until CRM has data. |

#### Phase 3: Activate when needed

| Deployment | Schedule | When to activate |
|------------|----------|-----------------|
| **weekly-report-mon8am** | Monday 8:00 UTC | When you want weekly reports. |
| **data-cleanup-sun2am** | Sunday 2:00 UTC | When you have enough data to clean. |
| **data-sync-hourly** | Every hour | When you need collection-to-collection sync. |
| **property-pipeline-6h** | Every 6 hours | When you configure property scraping sites. |
| **scraper-latam-6h** | Every 6 hours | Legacy. Use property-pipeline instead. |

## How to Activate

### From Prefect Dashboard (UI)

1. Open `http://localhost:4200` via SSH tunnel
2. Go to Deployments
3. Click on the deployment
4. Toggle "Paused" off

### From Chat (via Automation Agent)

Not supported yet — Prefect API can unpause but the Automation Agent
doesn't have that tool. Use the dashboard.

### From CLI

```bash
docker exec -e PREFECT_API_URL=http://prefect:4200/api qyne-prefect-worker \
  prefect deployment resume "Flow Name/deployment-name"
```

## What Happens When a Scheduled Flow Runs

1. Prefect creates a flow run at the scheduled time
2. Worker picks it up from default-pool
3. Flow executes (tasks with retries)
4. Results saved to Directus
5. Run logged in Prefect dashboard (success/failed/crashed)
6. If failed: Prefect retries based on flow config

**If a flow fails repeatedly**: It shows as "Failed" in the dashboard.
No cascading damage — each flow is independent. Fix the issue and
trigger manually to catch up.

## Idempotency (Safe to Run Multiple Times)

All flows are designed to be idempotent:

| Flow | Idempotency mechanism |
|------|----------------------|
| health-check | Logs new event each time (append-only) |
| backup | Creates new backup file with timestamp (no overwrite) |
| lead-scorer | Recalculates scores (same input = same output) |
| sentiment | Only processes conversations without sentiment (skip scored) |
| data-enricher | Only enriches contacts without enrichment (skip enriched) |
| daily-digest | Creates new digest event (append-only) |
| weekly-report | Creates new report event (append-only) |
| data-cleanup | Report only, never deletes (safe) |
| dedup-merger | Dry run by default (safe) |

## Monitoring Active Flows

### Quick Check

```bash
# See recent runs
docker exec -e PREFECT_API_URL=http://prefect:4200/api qyne-prefect-worker \
  prefect flow-run ls --limit 10

# See failed runs only
docker exec -e PREFECT_API_URL=http://prefect:4200/api qyne-prefect-worker \
  python3 -c "
import urllib.request, json
r = urllib.request.urlopen(urllib.request.Request(
    'http://prefect:4200/api/flow_runs/filter',
    data=json.dumps({'limit':10, 'flow_runs':{'state':{'name':{'any_':['Failed','Crashed']}}}}).encode(),
    headers={'Content-Type':'application/json'}, method='POST'))
for run in json.loads(r.read()):
    print(f\"  {run['name']} | {run['state']['name']} | {run.get('deployment_id','?')[:12]}\")
"
```

### Dashboard

Prefect dashboard (`localhost:4200`) shows:
- All flow runs with status (green/red/yellow)
- Timeline of executions
- Logs per task
- Retry history
- Duration trends

## Cost of Running Scheduled Flows

| Flow | RAM impact | CPU impact | Directus writes |
|------|-----------|-----------|----------------|
| health-check (5min) | ~20MB spike | Minimal | 1 event per run |
| backup (daily) | ~50MB spike | pg_dump CPU | 0 (writes to RustFS) |
| lead-scorer (daily) | ~30MB spike | Minimal | N contact updates |
| sentiment (daily) | ~20MB spike | Minimal | N conversation updates |
| digest (daily) | ~20MB spike | Minimal | 1 event |
| enricher (daily) | ~30MB spike | Minimal | N contact updates |

Total additional RAM: negligible (spikes are temporary, ~30 seconds each).
Total Directus writes: ~100-500 per day depending on data volume.
