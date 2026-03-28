# QYNE v1 — Automation Agent: Production Command Architecture

## Why One Agent, Not Multiple

In production L4 systems (2026 standard), the automation layer uses a
**single orchestrator agent** with a comprehensive command playbook.
Multiple automation agents create:
- Confusion about which agent handles which system
- Duplicate tool calls (two agents calling the same API)
- Inconsistent state (one agent doesn't know what the other did)
- Harder debugging (which agent caused the error?)

The correct pattern: **one Automation Agent with specialized skills per system**.
The agent loads skills for Directus, Prefect, n8n, and uses the right
commands based on what you ask.

## How It Works in Production

```
User: "Crawlea docs.agno.com"
    │
    ▼
NEXUS Master → routes to Automation Agent
    │
    ▼
Automation Agent:
    1. Loads n8n-automation skill (for n8n commands)
    2. Loads automation-commands skill (for Prefect/Directus commands)
    3. Decides: this is a Prefect task (website crawling)
    4. Calls list_prefect_deployments() → finds website-crawler-ondemand
    5. Calls trigger_prefect_flow("643ba6b2-...", '{"url": "https://docs.agno.com"}')
    6. Reports: "Crawling iniciado. Revisa en Prefect dashboard o preguntame el status."
```

The agent doesn't need to know HOW to crawl. It knows WHICH tool to call
and with WHAT parameters. The skill provides the exact syntax.

## The Command Playbook Pattern

Instead of generic instructions ("you can trigger Prefect flows"), the agent
gets a **command playbook** with exact deployment IDs, parameter schemas,
and example commands. This eliminates syntax errors because the agent
copies from the playbook instead of guessing.

## Error Mitigation Strategy

1. **Exact IDs in skill**: No guessing deployment IDs
2. **Parameter schemas**: Agent knows exactly what each flow accepts
3. **Example commands**: Copy-paste patterns for common requests
4. **Validation rules**: Agent checks parameters before calling
5. **Status checking**: Agent verifies the flow started successfully
6. **Fallback instructions**: What to do if a tool call fails
