# QYNE — Migration Roadmap: 42 Agents → 8 Agents + Prefect Backbone

> Plan de migracion del sistema actual (42 agentes AgNO con teams y workflows)
> al nuevo esquema (8 agentes core + Prefect como backbone deterministico).

---

## Estado Actual del Codigo

### Estructura de archivos

```
services/
  agno/
    app/
      config.py          # Modelos, DB, knowledge base, Directus config
      main.py            # AgentOS entry point (registra 42 agentes, 7 teams, 7 workflows)
      shared.py          # Guardrails, learning, compression
      models.py          # Pydantic models (ResearchReport, etc.)
    agents/
      research.py        # research_agent
      knowledge.py       # knowledge_agent
      support.py         # support_agent
      content/agents.py  # trend_scout, scriptwriter, creative_director, analytics_agent
      seo/agents.py      # keyword_researcher, article_writer, seo_auditor
      social/agents.py   # ig_post_agent, twitter_post_agent, linkedin_post_agent, social_auditor + workflow
      marketing/agents.py # copywriter_es, seo_strategist, social_media_planner + marketing_latam team
      competitor/agents.py # 4 scouts + synthesizer + competitor_intel_workflow
      creative/agents.py  # image_generator, video_generator, media_describer + creative_studio team
      deep_research/agents.py # planner, scouts (Tavily/Exa/Firecrawl/WebSearch), synthesizer
      product_dev/agents.py   # product_manager, ux_researcher, technical_writer + team
      utility/agents.py       # automation_agent, dash, pal, onboarding, email, scheduler, invoice, code_review
      whatsapp_support/agents.py # whabi/docflow/aurora/general support + whatsapp_support_team
    teams/
      cerebro.py         # cerebro team (router)
      content_team.py    # content_team (coordinate)
      nexus_master.py    # nexus_master (top-level router)
    workflows/
      content_production.py  # trend → compact → script → review
      seo_content.py         # keyword → article → audit loop
      research.py            # client_research + deep_research workflows
      media_generation.py    # describe → generate
    tools/
      directus_business.py   # save_contact, log_ticket, confirm_payment, etc.
      prefect_api.py         # list/trigger/check Prefect flows
      chat_export.py         # save chat to Directus/knowledge
      sandbox.py             # Docker sandbox
    skills/                  # 24 skill directories con SKILL.md
    knowledge/               # PDFs, docs para RAG
  workers/
    flows/                   # 21 Prefect flows (scraping, ETL, backups, etc.)
    pyproject.toml           # Prefect >= 3.0, Crawl4AI, httpx, voyageai
  frontend/                  # Next.js + CopilotKit
```

### Problemas del esquema actual

1. **42 agentes registrados en AgentOS** — la mayoria nunca se han ejecutado en produccion
2. **Teams coordinan agentes** consumiendo tokens extra para "decidir quien hace que"
3. **Workflows de AgNO** duplican lo que Prefect ya hace mejor (retry, timeout, scheduling)
4. **Agentes especializados** (ig_post_agent, linkedin_post_agent, etc.) son el mismo LLM con instrucciones diferentes — no necesitan ser agentes separados
5. **Tools de Directus no vinculan contact_id** — registros huerfanos
6. **nexus_master → cerebro → agent** = 3 niveles de routing que consumen tokens sin agregar valor

---

## Prefect: Capacidades Confirmadas para Este Esquema

Prefect 3.x (version actual en el proyecto) soporta todo lo necesario:

| Capacidad | Soporte | Como |
|-----------|---------|------|
| **Async tasks** | Si | `@task` con `async def`, `await` nativo |
| **Retry con backoff** | Si | `@task(retries=3, retry_delay_seconds=[10, 30, 60])` |
| **Timeout** | Si | `@task(timeout_seconds=300)` |
| **Parallel execution** | Si | `.submit()` retorna Future, multiples tasks en paralelo |
| **Concurrency limits** | Si | Global y tag-based concurrency limits |
| **Scheduling (cron)** | Si | Deployments con `cron="0 7 * * 1"` (lunes 7am) |
| **State management** | Si | Cada task tiene estado (Pending, Running, Completed, Failed) |
| **Logging** | Si | `get_run_logger()`, `log_prints=True` |
| **Caching** | Si | `@task(cache_key_fn=..., cache_expiration=timedelta(hours=1))` |
| **Map (fan-out)** | Si | `task.map([item1, item2, ...])` para procesar listas en paralelo |
| **Conditional branching** | Si | Python `if/else` nativo dentro del flow |
| **Sub-flows** | Si | Un flow puede llamar a otro flow |
| **Artifacts** | Si | Guardar resultados como artifacts visibles en UI |
| **Notifications** | Si | Automations que notifican en Slack/email/webhook on failure |
| **Dashboard** | Si | UI web con estado de todos los flows y tasks |

**Limitacion vs LangGraph:** Prefect no tiene "checkpointing" mid-LLM-call ni "time-travel debugging" de estados de agente. Pero no lo necesitamos — los agentes AgNO manejan su propio estado internamente, Prefect solo los invoca y recibe el resultado.

**Patron clave:** Prefect task que invoca un agente AgNO:

```python
from agno.agent import Agent
from prefect import task

@task(retries=2, retry_delay_seconds=30, timeout_seconds=120)
async def invoke_agent(agent: Agent, prompt: str) -> str:
    """Invoca un agente AgNO desde un Prefect task."""
    response = await agent.arun(prompt)
    return response.content
```

Si el agente falla (timeout LLM, rate limit, error de tool), Prefect hace retry automaticamente. El agente no necesita manejar su propia recuperacion.

---

## Los 8 Agentes: Definicion Detallada

### Capa Prefect (4 agentes invocados por tasks)

#### 1. Researcher

**Reemplaza:** research_agent, knowledge_agent, trend_scout, research_planner,
research_synthesizer, websearch_scout, tavily_scout, exa_scout, firecrawl_scout,
competitor_content_scout, competitor_pricing_scout, competitor_reviews_scout,
competitor_synthesizer, keyword_researcher (14 agentes)

**Tools:** DuckDuckGoTools, WebSearchTools, TavilyTools, ExaTools, FirecrawlTools,
KnowledgeTools (LanceDB), Directus MCP (read-items)

**Como funciona:** Un solo agente con todos los tools de investigacion.
Las instrucciones especificas vienen del Prefect task que lo invoca:

```python
@task
async def research_trends(topic: str) -> dict:
    return await invoke_agent(researcher,
        f"Investiga tendencias de las ultimas 48h sobre {topic}. "
        f"Max 3 tool calls. Produce brief con hooks en espanol.")

@task
async def research_competitor(competitor: str) -> dict:
    return await invoke_agent(researcher,
        f"Analiza a {competitor}: contenido, pricing, reviews en G2/Capterra.")

@task
async def research_keywords(niche: str) -> dict:
    return await invoke_agent(researcher,
        f"Encuentra keywords con alto potencial GEO para {niche} en espanol.")
```

Mismo agente, diferentes instrucciones. Prefect decide cuando y como invocarlo.

#### 2. Writer

**Reemplaza:** article_writer, copywriter_es, ig_post_agent,
twitter_post_agent, linkedin_post_agent, technical_writer, seo_auditor (7 agentes)

**Tools:** FileTools, Directus MCP (create-item)

**Como funciona:** Un solo agente que escribe cualquier formato.
El Prefect task le da las instrucciones especificas:

```python
@task
async def write_article(brief: dict, brand: str) -> dict:
    return await invoke_agent(writer,
        f"Escribe articulo SEO/GEO de 1500-2500 palabras en espanol. "
        f"Estructura: Quick Answer, Intro, Entries, Tabla, FAQ. "
        f"Brief: {json.dumps(brief)}. Brand: {brand}.")

@task
async def write_social_posts(brief: dict, brand: str) -> dict:
    return await invoke_agent(writer,
        f"Genera 3 posts adaptados: 1 para Instagram (hooks visuales, "
        f"hashtags 10-15), 1 para X (thread 5 tweets, max 280 chars), "
        f"1 para LinkedIn (profesional, line breaks). Brand: {brand}. "
        f"Brief: {json.dumps(brief)}.")

@task
async def write_email(context: dict) -> dict:
    return await invoke_agent(writer,
        f"Redacta email profesional en espanol LATAM. "
        f"Contexto: {json.dumps(context)}. Muestra draft, no envies.")
```

#### 3. Analyst

**Reemplaza:** analytics_agent, creative_director, social_auditor,
seo_auditor (funcion de evaluacion), product_manager, ux_researcher (6 agentes)

**Tools:** CalculatorTools, PythonTools, Directus MCP (read-items), WebSearchTools

**Como funciona:** Analiza, evalua, compara, produce reportes.

```python
@task
async def analyze_content_performance(period_days: int) -> dict:
    return await invoke_agent(analyst,
        f"Genera reporte semanal de performance social. "
        f"Lee social_analytics de Directus (ultimos {period_days} dias). "
        f"Top/bottom posts, performance por pilar, 3 recomendaciones.")

@task
async def evaluate_variants(variants: list[dict]) -> dict:
    return await invoke_agent(analyst,
        f"Evalua estas {len(variants)} variantes de contenido. "
        f"Para cada una: mood, fortaleza, debilidad. "
        f"Recomienda la mejor con justificacion. "
        f"Variantes: {json.dumps(variants)}")

@task
async def audit_seo(article: str) -> dict:
    return await invoke_agent(analyst,
        f"Audita este articulo para SEO y GEO. Checklist: Quick Answer, "
        f"listicle, evidence density, FAQ, titulo <60 chars, >1500 words. "
        f"Score X/100. Veredicto: PUBLISH / REVISE / REWRITE. "
        f"Articulo: {article[:3000]}")
```

#### 4. Strategist

**Reemplaza:** Growth Strategist (nuevo), seo_strategist, social_media_planner (3 agentes)

**Tools:** Directus MCP (read-items de analytics, deals, learnings, experiments),
CalculatorTools, PythonTools

**Como funciona:** Sintetiza datos en planes y decisiones.

```python
@task
async def generate_weekly_plan(brand: str) -> dict:
    return await invoke_agent(strategist,
        f"Produce plan semanal para {brand}. "
        f"Lee de Directus: social_analytics (ultima semana), deals (pipeline), "
        f"marketing_learnings (insights acumulados), experiments (resultados). "
        f"Output: canales a priorizar, topics, allocation 70/20/10, KPIs target.")
```

### Capa AgNO Real-Time (4 agentes conversacionales)

#### 5. Support Router

**Reemplaza:** whatsapp_support_team (team router)

Se mantiene como AgNO Team en modo route porque necesita routing dinamico
en tiempo real basado en el mensaje del cliente.

#### 6. Support Agent

**Reemplaza:** whabi_support_agent, docflow_support_agent, aurora_support_agent,
general_support_agent (4 agentes)

Un solo agente con skills por producto. El Support Router le pasa el producto
identificado y el agente carga el skill correspondiente.

**Tools:** save_contact, log_support_ticket (con contact_id), log_conversation,
confirm_payment, escalate_to_human, get_customer_360, Directus MCP, KnowledgeTools

#### 7. Dash

Se mantiene igual. Agente conversacional para preguntas de negocio ad-hoc.

#### 8. Pal

Se mantiene igual. Asistente personal con memoria agentiva.

---

## Mapeo: 42 Agentes → 8 Agentes

| Agente actual | Nuevo agente | Invocado por |
|--------------|-------------|-------------|
| research_agent | **Researcher** | Prefect |
| knowledge_agent | **Researcher** (con KnowledgeTools) | Prefect |
| trend_scout | **Researcher** (instrucciones de trends) | Prefect |
| research_planner | Eliminado (Prefect planifica) | - |
| research_synthesizer | **Researcher** (instrucciones de sintesis) | Prefect |
| websearch_scout | **Researcher** | Prefect |
| tavily_scout | **Researcher** (con TavilyTools) | Prefect |
| exa_scout | **Researcher** (con ExaTools) | Prefect |
| firecrawl_scout | **Researcher** (con FirecrawlTools) | Prefect |
| competitor_content_scout | **Researcher** (instrucciones de competitor content) | Prefect |
| competitor_pricing_scout | **Researcher** (instrucciones de pricing) | Prefect |
| competitor_reviews_scout | **Researcher** (instrucciones de reviews) | Prefect |
| competitor_synthesizer | **Analyst** (instrucciones de sintesis competitiva) | Prefect |
| keyword_researcher | **Researcher** (instrucciones de keywords) | Prefect |
| scriptwriter | Eliminado (video descartado) | - |
| article_writer | **Writer** (instrucciones de articulos SEO) | Prefect |
| copywriter_es | **Writer** (instrucciones de copy LATAM) | Prefect |
| ig_post_agent | **Writer** (instrucciones de Instagram) | Prefect |
| twitter_post_agent | **Writer** (instrucciones de X/Twitter) | Prefect |
| linkedin_post_agent | **Writer** (instrucciones de LinkedIn) | Prefect |
| technical_writer | **Writer** (instrucciones de documentacion) | Prefect |
| creative_director | **Analyst** (instrucciones de evaluacion creativa) | Prefect |
| analytics_agent | **Analyst** (instrucciones de analytics) | Prefect |
| social_auditor | **Analyst** (instrucciones de auditoria social) | Prefect |
| seo_auditor | **Analyst** (instrucciones de auditoria SEO) | Prefect |
| seo_strategist | **Strategist** (instrucciones de SEO strategy) | Prefect |
| social_media_planner | **Strategist** (instrucciones de calendario) | Prefect |
| product_manager | **Analyst** (instrucciones de RICE scoring) | Prefect |
| ux_researcher | **Analyst** (instrucciones de UX) | Prefect |
| image_generator | **Writer** (con NanoBananaTools) | Prefect |
| video_generator | Eliminado (video descartado) | - |
| media_describer | **Analyst** (instrucciones de descripcion) | Prefect |
| automation_agent | Eliminado (Prefect ES la automatizacion) | - |
| email_agent | **Writer** (instrucciones de email, HITL) | Prefect |
| scheduler_agent | Eliminado (Prefect + Directus Flows) | - |
| invoice_agent | **Writer** (instrucciones de invoice, HITL) | Prefect |
| code_review_agent | **Analyst** (instrucciones de code review) | Prefect |
| onboarding_agent | **Support Agent** (instrucciones de onboarding) | AgNO real-time |
| whabi_support_agent | **Support Agent** (skill whabi) | AgNO real-time |
| docflow_support_agent | **Support Agent** (skill docflow) | AgNO real-time |
| aurora_support_agent | **Support Agent** (skill aurora) | AgNO real-time |
| general_support_agent | **Support Agent** (skill general) | AgNO real-time |

**Eliminados completamente (5):**
- `research_planner` — Prefect planifica los steps, no un agente
- `automation_agent` — Prefect ES la automatizacion, no necesita un agente que llame a Prefect
- `scheduler_agent` — Directus Flows + Prefect schedules reemplazan esto
- `scriptwriter` — Video descartado (costo alto, calidad inconsistente)
- `video_generator` — Video descartado

**Teams eliminados (6 de 7):**
- `nexus_master` — Eliminado. NEXUS chat usa routing simple, no un team de 42 agentes
- `cerebro` — Eliminado. Prefect orquesta research/knowledge/automation
- `content_team` — Eliminado. Prefect flow content_production
- `product_dev_team` — Eliminado. Prefect tasks con Analyst
- `creative_studio` — Eliminado. Prefect tasks con Writer
- `marketing_latam` — Eliminado. Prefect tasks con Writer + Strategist

**Team que se mantiene (1):**
- `whatsapp_support_team` — Se simplifica a Support Router + Support Agent

**Workflows AgNO eliminados (todos los 7):**
Todos se convierten en Prefect flows. Los AgNO workflows no aportan nada
que Prefect no haga mejor (retry, timeout, scheduling, logging, dashboard).

---

## Nuevos Prefect Flows de Marketing

Estos reemplazan los 7 AgNO workflows + agregan los nuevos (Growth Strategist, Experiments):

| Flow | Schedule | Steps | Agentes invocados |
|------|----------|-------|-------------------|
| `content_production` | On-demand / diario | research → compact → write variants → evaluate → store | Researcher, Writer, Analyst |
| `seo_content` | On-demand | research keywords → write article → audit → loop → store | Researcher, Writer, Analyst |
| `social_media_generation` | Diario | read weekly_plan → write posts por plataforma → audit → store en Directus | Writer, Analyst |
| `social_media_publish` | Diario (post-aprobacion) | read approved posts → Postiz CLI → log analytics | Ninguno (deterministico) |
| `deep_research` | On-demand | parallel(research x N angles) → merge → synthesize | Researcher (x3-4 parallel) |
| `competitor_intel` | Semanal | parallel(content + pricing + reviews) → synthesize | Researcher (x3 parallel), Analyst |
| `growth_strategist` | Lunes 7am | read analytics + CRM + learnings → strategize → store plan | Strategist |
| `experiment_analysis` | Viernes | read experiment results → compare variants → declare winners → store learnings | Analyst |
| `content_recycling` | Semanal | find top performers → generate variations → schedule re-publish | Writer |
| `lead_scoring` | Diario 6am | read contacts + activity → calculate scores → update → create deals | Ninguno (deterministico) |
| `sentiment_analysis` | Diario | read conversations → keyword scoring → update | Ninguno (deterministico) |
| `sla_compliance` | Diario | read tickets → calculate FRT/TTR → update dashboard | Ninguno (deterministico) |

**Flows existentes que se mantienen sin cambios:**
- `website_crawler` — Ya es Prefect, funciona bien
- `database_backup` — Ya es Prefect
- `health_check` — Ya es Prefect
- `data_sync`, `data_cleanup`, `dedup_merger`, `data_enricher` — Ya son Prefect
- `export_csv`, `import_csv` — Ya son Prefect
- `etl_documents`, `knowledge_indexer` — Ya son Prefect

---

## Estructura de Archivos Post-Migracion

```
services/
  agno/
    app/
      config.py          # Sin cambios (modelos, DB, knowledge)
      main.py            # Simplificado: 8 agentes, 1 team, 0 workflows AgNO
      shared.py          # Sin cambios
      models.py          # Agregar StepArtifact, Decision
    agents/
      researcher.py      # 1 agente con todos los tools de investigacion
      writer.py          # 1 agente con tools de escritura + media
      analyst.py         # 1 agente con tools de analisis
      strategist.py      # 1 agente con tools de estrategia
      support.py         # Support Router (team) + Support Agent (1 agente multi-skill)
      dash.py            # Sin cambios
      pal.py             # Sin cambios
    tools/
      directus_business.py  # CORREGIR: agregar contact_id a todos los tools
      agent_invoker.py      # Nuevo: helper para invocar agentes desde Prefect
      postiz.py             # Nuevo: wrapper para Postiz CLI
    skills/                 # Mantener todos (los agentes los cargan segun contexto)
    knowledge/              # Sin cambios
  workers/
    flows/
      # Existentes (sin cambios):
      website_crawler.py, database_backup.py, health_check.py, etc.
      # Nuevos (marketing):
      content_production.py    # Reemplaza AgNO content_production_workflow
      seo_content.py           # Reemplaza AgNO seo_content_workflow
      social_media.py          # Reemplaza AgNO social_media_workflow
      deep_research.py         # Reemplaza AgNO deep_research_workflow
      competitor_intel.py      # Reemplaza AgNO competitor_intel_workflow
      growth_strategist.py     # Nuevo
      experiment_analysis.py   # Nuevo
      content_recycling.py     # Nuevo
      lead_scoring.py          # Ya existe, mejorar
      sentiment_analysis.py    # Ya existe
      sla_compliance.py        # Nuevo
    pyproject.toml           # Agregar: agno como dependencia (para invocar agentes)
  frontend/                  # Sin cambios
```

---

## Plan de Migracion (Orden de Ejecucion)

### Fase 0 — Preparacion (antes de tocar agentes)

1. **Crear `agent_invoker.py`** — Helper que invoca agentes AgNO desde Prefect tasks
   con retry, timeout, structured output parsing
2. **Crear `postiz.py`** — Wrapper para Postiz CLI
3. **Corregir `directus_business.py`** — Agregar contact_id a todos los tools
4. **Crear modelos Pydantic** — StepArtifact, Decision, y output schemas por tipo de task
5. **Agregar `agno` como dependencia** en workers/pyproject.toml

### Fase 1 — Crear los 4 agentes Prefect (sin eliminar los viejos)

6. **Crear `researcher.py`** — Un agente con todos los tools de investigacion
7. **Crear `writer.py`** — Un agente con tools de escritura
8. **Crear `analyst.py`** — Un agente con tools de analisis
9. **Crear `strategist.py`** — Un agente con tools de estrategia

### Fase 2 — Crear Prefect flows de marketing (en paralelo con los viejos)

10. **`content_production.py`** (Prefect) — Reemplaza AgNO workflow
11. **`seo_content.py`** (Prefect) — Reemplaza AgNO workflow
12. **`social_media.py`** (Prefect) — Reemplaza AgNO workflow
13. **`deep_research.py`** (Prefect) — Reemplaza AgNO workflow
14. **`competitor_intel.py`** (Prefect) — Reemplaza AgNO workflow

### Fase 3 — Crear nuevos flows L4

15. **`growth_strategist.py`** — Plan semanal (lunes 7am)
16. **`experiment_analysis.py`** — Comparar variantes (viernes)
17. **`content_recycling.py`** — Re-publicar top performers
18. **`sla_compliance.py`** — Calcular SLA diario

### Fase 4 — Simplificar soporte

19. **Refactorizar `support.py`** — 1 Support Agent multi-skill en lugar de 4
20. **Simplificar Support Router** — Team minimo (router + 1 agent)

### Fase 5 — Limpiar

21. **Simplificar `main.py`** — Registrar solo 8 agentes, 1 team, 0 workflows AgNO
22. **Eliminar archivos obsoletos** — agents/content/, agents/seo/, agents/social/,
    agents/marketing/, agents/competitor/, agents/creative/, agents/product_dev/,
    teams/, workflows/
23. **Actualizar frontend** — Si hay referencias a agentes especificos

### Validacion en cada fase

- Fase 1: Los 4 nuevos agentes responden correctamente a prompts de test
- Fase 2: Los Prefect flows producen output equivalente a los AgNO workflows
- Fase 3: Growth Strategist produce plan semanal coherente con datos de test
- Fase 4: Support Agent maneja conversaciones de los 3 productos
- Fase 5: `main.py` arranca limpio con 8 agentes, dashboard funciona

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Mitigacion |
|--------|-------------|-----------|
| Agente Writer no es tan bueno como agentes especializados | Media | Skills cargan instrucciones especificas. Si un formato necesita mas especializacion, se agrega un skill, no un agente. |
| Prefect worker no puede importar AgNO | Baja | Agregar agno a pyproject.toml del worker. Ambos son Python. |
| Latencia de Prefect task overhead | Baja | Overhead de Prefect es ~100ms por task. Irrelevante vs 2-10s de LLM call. |
| Perder memoria/learning de agentes viejos | Media | Los nuevos agentes usan la misma DB SQLite y LanceDB. La memoria persiste. |
| Support Agent no routea bien entre productos | Media | Mantener Support Router como team AgNO. Solo el routing es multi-agente. |
