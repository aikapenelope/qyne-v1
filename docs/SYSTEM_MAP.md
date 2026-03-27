# QYNE v1 — System Map: What We Have vs What Exists

## Connection Diagram

```
                         INTERNET
                            │
                    ┌───────┴───────┐
                    │   Traefik     │ ports 80/443 (firewall blocks them)
                    │   :80/:443   │ only SSH tunnel access for now
                    └───┬───────┬───┘
                        │       │
                   Frontend  WhatsApp webhook
                   :3000     (future)
                        │       │
                        └───┬───┘
                            │ AG-UI (HTTP/SSE)
                            ▼
                    ┌───────────────┐
                    │     AGNO      │ ← SQLite (sessions, memory)
                    │    :8000      │ ← LanceDB (knowledge, embeddings)
                    │               │ ← Docker socket (sandbox/micro-PC)
                    │  3 agents     │
                    │  2 tools      │
                    │  24 skills    │
                    │  6 knowledge  │
                    └───┬───────┬───┘
                   MCP  │       │ REST tools
                (future)│       │ (directus_business.py)
                        │       │
                        ▼       ▼
                    ┌───────────────┐
                    │   DIRECTUS    │ ← PostgreSQL (directus_db)
                    │    :8055      │ ← Redis (cache)
                    │               │ ← RustFS (file storage, future)
                    │ 10 collections│
                    │ + system fields│
                    │ + audit trail │
                    └───┬───────┬───┘
                        │       │
                   n8n  │       │ Prefect workers
                   :5678│       │ (via REST API)
                        │       │
                    ┌────┘       └────┐
                    ▼                 ▼
              ┌──────────┐    ┌──────────────┐
              │   n8n    │    │   Prefect    │ ← PostgreSQL (prefect_db)
              │  :5678   │    │   :4200      │
              │ SQLite   │    │              │
              │ 0 flows  │    │ 0 deployments│
              └──────────┘    └──────────────┘

              ┌──────────┐    ┌──────────┐
              │  RustFS  │    │  Uptime  │
              │ :9000    │    │  Kuma    │
              │ 0 buckets│    │  :3001   │
              └──────────┘    │ 0 monitors│
                              └──────────┘
```

## Agno: What We Have vs What Exists in nexus_legacy.py

### Agents (3 of 42 ported)

| Agent | Status | Purpose |
|-------|--------|---------|
| research_agent | PORTED | Web search, data gathering |
| knowledge_agent | PORTED | Knowledge base queries |
| support_agent | PORTED | Customer support (generic) |
| automation_agent | MISSING | n8n MCP + Directus MCP operations |
| trend_scout | MISSING | AI/tech trend research for content |
| scriptwriter | MISSING | Video scripts and storyboards |
| creative_director | MISSING | Evaluate storyboard variants |
| analytics_agent | MISSING | Content performance analysis |
| _synthesis_agent | MISSING | Deep research synthesis |
| _spider_scout | MISSING | Web crawling scout |
| _websearch_scout | MISSING | Web search scout |
| _research_planner | MISSING | Research planning |
| _research_synthesizer | MISSING | Research synthesis |
| _keyword_researcher | MISSING | SEO keyword research |
| _article_writer | MISSING | Blog article writing |
| _seo_auditor | MISSING | SEO audit |
| code_review_agent | MISSING | Code review and debugging |
| dash | MISSING | Self-learning data agent (6 layers of context) |
| pal | MISSING | Personal agent (learns preferences) |
| onboarding_agent | MISSING | Client onboarding |
| email_agent | MISSING | Email drafting and management |
| scheduler_agent | MISSING | Meeting scheduling |
| invoice_agent | MISSING | Invoice generation |
| _product_manager | MISSING | Product management |
| _ux_researcher | MISSING | UX research |
| _technical_writer | MISSING | Technical documentation |
| _image_generator | MISSING | AI image generation |
| _video_generator | MISSING | AI video generation |
| _media_describer | MISSING | Media description |
| _copywriter_es | MISSING | Spanish copywriting |
| _seo_strategist | MISSING | SEO strategy |
| _social_media_planner | MISSING | Social media planning |
| whabi_support_agent | MISSING | Whabi-specific support |
| docflow_support_agent | MISSING | Docflow-specific support |
| aurora_support_agent | MISSING | Aurora-specific support |
| general_support_agent | MISSING | General support router |
| _ig_post_agent | MISSING | Instagram post creation |
| _twitter_post_agent | MISSING | Twitter/X post creation |
| _linkedin_post_agent | MISSING | LinkedIn post creation |
| _social_auditor | MISSING | Social media audit |
| _competitor_content_scout | MISSING | Competitor content analysis |
| _competitor_pricing_scout | MISSING | Competitor pricing analysis |
| _competitor_reviews_scout | MISSING | Competitor reviews analysis |
| _competitor_synthesizer | MISSING | Competitor intelligence synthesis |

### Teams (0 of 7 ported)

| Team | Status | Mode | Members |
|------|--------|------|---------|
| cerebro | MISSING | route | research, knowledge, automation |
| content_team | MISSING | coordinate | trend_scout, scriptwriter, creative_director, analytics |
| whatsapp_support_team | MISSING | route | whabi, docflow, aurora, general support |
| product_dev_team | MISSING | coordinate | product_manager, ux_researcher, technical_writer |
| creative_studio | MISSING | coordinate | image_generator, video_generator, media_describer |
| marketing_latam | MISSING | coordinate | copywriter_es, seo_strategist, social_media_planner |
| nexus_master | MISSING | route | ALL agents and teams (top-level router) |

### Workflows (0 of 7 ported)

| Workflow | Status | Steps |
|----------|--------|-------|
| content_production_workflow | MISSING | trend → script → review → publish |
| client_research_workflow | MISSING | search → analyze → report |
| deep_research_workflow | MISSING | plan → search → synthesize |
| seo_content_workflow | MISSING | keywords → write → audit |
| social_media_workflow | MISSING | plan → create posts → schedule |
| competitor_intel_workflow | MISSING | content + pricing + reviews → synthesis |
| media_generation_workflow | MISSING | describe → generate → review |

### Structured Output Models (0 of 8 ported)

| Model | Status | Used By |
|-------|--------|---------|
| ResearchReport | MISSING | research agents |
| LeadReport | MISSING | support agents |
| TaskSummary | MISSING | automation agent |
| ContentBrief | MISSING | trend_scout |
| VideoScene | MISSING | scriptwriter |
| VideoStoryboard | MISSING | scriptwriter |
| SupportTicket | MISSING | support agents |
| PaymentConfirmation | MISSING | support agents |

### Agno Features: What We Use vs What's Available

| Feature | Available in Agno | We Use It | Status |
|---------|-------------------|-----------|--------|
| **Memory** | | | |
| User Memory (automatic) | Yes | Yes | WORKING |
| User Memory (agentic) | Yes | Yes | WORKING |
| Entity Memory | Yes | Yes | WORKING |
| Session Context | Yes | Yes | WORKING |
| **Learning** | | | |
| User Profile | Yes | Yes | WORKING |
| Learned Knowledge | Yes | Yes | WORKING |
| Decision Log | Yes | Yes | WORKING |
| Learning Curator | Yes | Unknown | CHECK |
| **Knowledge** | | | |
| LanceDB vector store | Yes | Yes | WORKING |
| Hybrid search (vector + keyword) | Yes | Yes | WORKING |
| DoclingReader | Yes (v2.5.10) | No | NOT USED |
| Knowledge isolation | Yes | No | NOT USED |
| Reranker (Infinity) | Yes | No | REMOVED |
| **Guardrails** | | | |
| PII Detection | Yes | Yes | WORKING |
| Prompt Injection | Yes | Yes | WORKING |
| Custom guardrails | Yes | No | NOT USED |
| **Context** | | | |
| Compression Manager | Yes | Yes | WORKING |
| Chat History | Yes | Yes | WORKING |
| Context Management | Yes | Unknown | CHECK |
| **Production** | | | |
| Tracing | Yes | Yes | WORKING |
| Scheduler | Yes | Yes | WORKING |
| Approvals (@approval) | Yes | Yes (in tools) | WORKING |
| Human-in-the-loop | Yes | Yes | WORKING |
| Evals (ResponseQualityEval) | Yes | In code, not active | INACTIVE |
| **Interfaces** | | | |
| AG-UI (CopilotKit) | Yes | Yes | WORKING |
| WhatsApp | Yes | Config only | NOT TESTED |
| Slack | Yes | No | NOT USED |
| Telegram | Yes (v2.5.10) | No | NOT USED |
| A2A Protocol | Yes | No | NOT USED |
| MCP Server mode | Yes | No | NOT USED |
| **Tools** | | | |
| 100+ built-in toolkits | Yes | ~15 imported | PARTIAL |
| MCP Tools (Directus) | Yes | In code, not tested | NOT TESTED |
| MCP Tools (n8n) | Yes | Not ported | MISSING |
| Custom tools (sandbox) | Yes | Yes | WORKING |
| Custom tools (Directus REST) | Yes | Yes | WORKING |
| **Skills** | | | |
| 24 domain skills | Yes | Loaded | WORKING |
| **Models** | | | |
| MiniMax (TOOL_MODEL) | Yes | Yes | WORKING |
| Groq (FAST_MODEL) | Yes | Yes | WORKING |
| OpenRouter (REASONING) | Yes | Yes | WORKING |
| Voyage AI (embeddings) | Yes | Yes | WORKING |

## Data Layer: What's Connected

| Connection | Status | How |
|------------|--------|-----|
| Agno → Directus (REST write) | WORKING | directus_business.py tools |
| Agno → Directus (MCP read) | NOT TESTED | npx @directus/content-mcp |
| Agno → LanceDB (knowledge) | WORKING | Embedded, /app/data/lancedb |
| Agno → SQLite (sessions) | WORKING | Embedded, /app/data/nexus.db |
| n8n → Directus | CONNECTED (network) | Nodo not installed yet |
| Prefect → Directus | CONNECTED (network) | No deployments yet |
| Frontend → Agno | WORKING | AG-UI protocol |
| Directus → PostgreSQL | WORKING | directus_db |
| Directus → Redis | WORKING | Cache |
| Prefect → PostgreSQL | WORKING | prefect_db |

## What's NOT Connected Yet

| Gap | Impact | Fix |
|-----|--------|-----|
| n8n has no workflows | No email ingestion, no triggers, no notifications | Create from UI |
| Prefect has no deployments | No scheduled scraping, no ETL | Create deployments |
| Uptime Kuma has no monitors | No health alerting | Configure from UI |
| RustFS has no buckets | Directus uses local storage | Create bucket, switch config |
| No domain/SSL | No WhatsApp, no public frontend | Buy domain, configure Traefik |
| Firewall blocks 80/443 | Traefik can't serve traffic | Open in Hetzner firewall |
| os.agno.com not connected | No visual tracing/monitoring | Needs Tailscale or domain |
| 39 agents not ported | System runs at ~7% capacity | Port from nexus_legacy.py |
| 7 teams not ported | No multi-agent coordination | Port from nexus_legacy.py |
| 7 workflows not ported | No automated pipelines | Port from nexus_legacy.py |
| 8 Pydantic models not ported | No structured outputs | Port from nexus_legacy.py |
| Evals not active | No quality monitoring | Activate in agent config |
| MCP Directus not tested | Agent can't read collections | Test after deploy |
| MCP n8n not ported | Agent can't create workflows | Port automation_agent |
