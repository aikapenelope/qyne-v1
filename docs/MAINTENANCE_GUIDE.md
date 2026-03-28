# QYNE v1 — Production Maintenance & Debugging Guide

## Integration Verification (Current State)

### Agno + AG-UI + CopilotKit — Verified Correct

| Component | Configuration | Status |
|-----------|--------------|--------|
| Agno backend | `AGUI(team=nexus_master)` on `/agui` endpoint | Correct (matches docs) |
| CopilotKit route | `HttpAgent({url: "http://agno:8000/agui"})` server-side | Correct |
| CopilotKit provider | `<CopilotKit runtimeUrl="/api/copilotkit" agent="nexus">` | Correct |
| OpenAIAdapter | Requires OPENAI_API_KEY or Groq alternative | Needs key for overlay |
| Chat page | Uses `/api/proxy/agno/teams/nexus-master/runs` (REST, not AG-UI) | Correct |
| All other pages | Use `/api/proxy/agno/*` (REST) | Correct |

The AG-UI protocol is only used by the CopilotKit overlay (floating chat button
on dashboard). All pages use the Agno REST API via server-side proxy.

---

## Logging Architecture

### Where Logs Live

| Service | Log Location | How to Access |
|---------|-------------|---------------|
| Agno | Docker stdout | `docker logs qyne-agno` |
| Directus | Docker stdout | `docker logs qyne-directus` |
| Frontend | Docker stdout | `docker logs qyne-frontend` |
| n8n | Docker stdout + UI | `docker logs qyne-n8n` or n8n Executions tab |
| Prefect | Docker stdout + UI | `docker logs qyne-prefect` or Prefect dashboard |
| Prefect Worker | Docker stdout + UI | `docker logs qyne-prefect-worker` |
| PostgreSQL | Docker stdout | `docker logs qyne-postgres` |
| Redis | Docker stdout | `docker logs qyne-redis` |
| Traefik | Docker stdout | `docker logs qyne-traefik` |
| RustFS | Docker stdout | `docker logs qyne-rustfs` |
| Uptime Kuma | Docker stdout + UI | `docker logs qyne-uptime-kuma` or Kuma dashboard |

### Log Levels

| Level | When to Use | Example |
|-------|------------|---------|
| ERROR | Something broke, needs attention | `Failed to initialize MCP toolkit` |
| WARNING | Something unexpected but not broken | `Fetch failed for URL` |
| INFO | Normal operation | `Fetched 42 agents` |
| DEBUG | Detailed debugging (not enabled by default) | Request/response bodies |

### Enabling Debug Logs

**Agno**: Set `AGNO_LOG_LEVEL=DEBUG` in docker-compose environment.

**Prefect**: Set `PREFECT_LOGGING_LEVEL=DEBUG` in worker environment.

**n8n**: Set `N8N_LOG_LEVEL=debug` in docker-compose environment.

**Directus**: Set `LOG_LEVEL=debug` in docker-compose environment.

Only enable debug logs temporarily for troubleshooting. They generate
massive output and can fill disk.

---

## Maintenance Schedule

### Daily (Automated)

| Time | Task | System | Status |
|------|------|--------|--------|
| 03:00 UTC | Database backup | Prefect (backup-daily-3am) | Paused — activate when ready |
| 05:00 UTC | Data enricher | Prefect (data-enricher-daily) | Paused |
| 06:00 UTC | Lead scorer | Prefect (lead-scorer-daily6am) | Paused |
| 07:00 UTC | Sentiment analyzer | Prefect (sentiment-daily) | Paused |
| 08:00 UTC | Daily digest | Prefect (daily-digest-8am) | Paused |
| Every 5 min | Health check | Prefect (health-check-5min) | Paused |
| Every 6h | Property scraper | Prefect (property-pipeline-6h) | Paused |

Activate from Prefect dashboard (`localhost:4200`) as needed.

### Weekly (Manual Review)

| Day | Task | How |
|-----|------|-----|
| Monday | Review weekly report | Check Directus events (type=weekly_report) |
| Monday | Check Uptime Kuma | Review uptime percentages, any downtime |
| Monday | Review Prefect flow runs | Check for failed runs in dashboard |
| Sunday | Data cleanup report | Check Directus events (type=cleanup_report) |

### Monthly

| Task | How |
|------|-----|
| Update Docker images | `docker compose pull && docker compose up -d` |
| Review disk usage | `df -h /` and `docker system df` |
| Clean Docker cache | `docker system prune -f` (removes unused images/containers) |
| Review Pulumi ESC secrets | Verify all keys are current, rotate if needed |
| Check n8n workflow executions | Review error rates in n8n Executions tab |
| Review Agno traces | Check for patterns in errors or slow responses |

### Quarterly

| Task | How |
|------|-----|
| Update Agno version | Check agno releases, test in dev before deploying |
| Update n8n version | Check n8n releases, backup workflows before updating |
| Update Prefect version | Check prefect releases |
| Security audit | Review Directus roles, API tokens, firewall rules |
| Performance review | Check RAM usage trends, response times |
| Backup verification | Restore a backup to verify it works |

---

## Debugging Procedures

### Procedure 1: Service Won't Start

```bash
# 1. Check container status
docker compose ps

# 2. Check logs for the failing service
docker logs qyne-{service} --tail 50

# 3. Check if it's a dependency issue
docker compose ps | grep -v healthy

# 4. Restart the service
docker compose restart {service}

# 5. If still failing, rebuild
docker compose build {service} && docker compose up -d {service}
```

### Procedure 2: Agent Not Responding

```bash
# 1. Check Agno health
curl http://127.0.0.1:8000/health

# 2. Check if agent is registered
curl http://127.0.0.1:8000/agents | python3 -c "import sys,json; [print(a['name']) for a in json.load(sys.stdin)]"

# 3. Check Agno logs for errors
docker logs qyne-agno --tail 30 | grep -i error

# 4. Check MCP initialization
docker logs qyne-agno 2>&1 | grep "MCP"

# 5. Test agent directly
curl -X POST http://127.0.0.1:8000/agents/{agent-id}/runs \
  -F "message=test" -F "stream=false" -F "session_id=debug" -F "user_id=debug"
```

### Procedure 3: Prefect Flow Failed

```bash
# 1. Check recent flow runs
docker exec -e PREFECT_API_URL=http://prefect:4200/api qyne-prefect-worker \
  prefect flow-run ls --limit 5

# 2. Check worker logs
docker logs qyne-prefect-worker --tail 30

# 3. Check if worker is picking up jobs
docker logs qyne-prefect-worker 2>&1 | grep "Executing\|Completed\|Failed"

# 4. Run flow manually for debugging
docker exec -e PREFECT_API_URL=http://prefect:4200/api -w /app \
  qyne-prefect-worker python3 -c "
import sys; sys.path.insert(0, '/app')
from flows.{flow_name} import {flow_function}
# Run with test parameters
"
```

### Procedure 4: Directus Connection Issues

```bash
# 1. Check Directus health
curl http://127.0.0.1:8055/server/health

# 2. Test with admin token
curl http://127.0.0.1:8055/auth/login -H "Content-Type: application/json" \
  -d '{"email":"admin@qyne.dev","password":"..."}'

# 3. Test agent token
curl http://127.0.0.1:8055/items/contacts?limit=1 \
  -H "Authorization: Bearer {DIRECTUS_TOKEN}"

# 4. Check PostgreSQL
docker exec qyne-postgres psql -U postgres -c "SELECT 1"

# 5. Check Directus logs
docker logs qyne-directus --tail 30 | grep -i error
```

### Procedure 5: Frontend Not Loading

```bash
# 1. Check frontend health
curl http://127.0.0.1:3000 -o /dev/null -w "HTTP %{http_code}"

# 2. Check proxy routes
curl http://127.0.0.1:3000/api/proxy/agno/agents | head -1

# 3. Check frontend logs
docker logs qyne-frontend --tail 20

# 4. Rebuild if needed
docker compose build frontend && docker compose up -d frontend
```

---

## The 4 Golden Signals (Google SRE)

Monitor these for every service:

### 1. Latency
How long requests take.
- **Agno**: Agent response time (visible in traces)
- **Directus**: API response time
- **Prefect**: Flow execution duration
- **Target**: < 30s for agent responses, < 500ms for API calls

### 2. Traffic
How many requests per second.
- **Agno**: Requests to /agents, /teams, /agui
- **Directus**: Requests to /items/*
- **Frontend**: Page loads
- **Monitor**: Uptime Kuma tracks request counts

### 3. Errors
Rate of failed requests.
- **Agno**: 5xx responses, MCP failures
- **Directus**: 4xx/5xx responses
- **Prefect**: Failed flow runs
- **Monitor**: Uptime Kuma alerts on errors

### 4. Saturation
How full the system is.
- **RAM**: `docker stats` — alert if any service > 80% of limit
- **Disk**: `df -h /` — alert if > 80%
- **CPU**: `docker stats` — alert if sustained > 80%
- **PostgreSQL**: Connection count, query time

---

## Quick Health Check Command

Run this to check everything at once:

```bash
echo "=== Services ===" && \
docker compose ps --format "table {{.Name}}\t{{.Status}}" && \
echo "" && echo "=== RAM ===" && \
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}" && \
echo "" && echo "=== Disk ===" && \
df -h / | tail -1 && \
echo "" && echo "=== Agno ===" && \
curl -sf http://127.0.0.1:8000/health && echo "" && \
echo "=== Directus ===" && \
curl -sf http://127.0.0.1:8055/server/health && echo "" && \
echo "=== Prefect ===" && \
curl -sf http://127.0.0.1:4200/api/health && echo "" && \
echo "=== Frontend ===" && \
curl -sf http://127.0.0.1:3000 -o /dev/null -w "HTTP %{http_code}" && echo ""
```

---

## Incident Response

### Severity Levels

| Level | Definition | Response Time | Example |
|-------|-----------|---------------|---------|
| P1 Critical | System down, no workaround | Immediate | All services down, database corrupted |
| P2 High | Major feature broken | < 1 hour | Chat not working, agents not responding |
| P3 Medium | Minor feature broken | < 4 hours | One Prefect flow failing, traces not showing |
| P4 Low | Cosmetic or minor | Next business day | UI alignment, slow response |

### Incident Checklist

1. **Identify**: What's broken? Check Uptime Kuma first.
2. **Contain**: Is it spreading? Check if other services are affected.
3. **Diagnose**: Check logs of the affected service.
4. **Fix**: Apply the fix (restart, rebuild, config change).
5. **Verify**: Confirm the fix works (run health check).
6. **Document**: Log what happened in Directus events collection.

### Rollback Procedure

```bash
# If a deploy broke something:
cd /opt/qyne-v1
git log --oneline -5  # Find the last good commit
git checkout {good-commit-hash} -- services/{broken-service}/
docker compose build {service}
docker compose up -d {service}
```
