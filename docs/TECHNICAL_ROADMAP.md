# QYNE — Technical Roadmap

> Roadmap detallado con referencias al codigo actual, archivos a crear,
> archivos a modificar, y archivos a eliminar en cada fase.

---

## Fase 0 — Preparacion (antes de tocar agentes)

### 0.1 Crear `services/agno/tools/agent_invoker.py`

Helper que invoca agentes AgNO desde Prefect tasks con retry y structured output.

```python
# Nuevo archivo
# Patron: Prefect task wraps AgNO agent call
# Input: agent instance + prompt string + optional output_schema
# Output: parsed Pydantic model or raw string
# Maneja: timeout, retry (delegado a Prefect @task decorator), error logging
```

**Referencia actual:** No existe. Los agentes solo se invocan desde AgentOS (app/main.py)
o desde otros agentes (teams). Este archivo es el puente Prefect → AgNO.

**Dependencia:** `agno` debe ser importable desde el worker. Ver 0.4.

### 0.2 Corregir `services/agno/tools/directus_business.py`

**Problema actual (lineas 179-240):** `save_contact()` crea contacto pero no retorna
el ID de Directus. Los demas tools (`log_support_ticket` L86-127, `log_conversation`
L282-330, `confirm_payment` L40-82) no reciben ni guardan `contact_id`.

**Cambios:**
1. `save_contact()` → buscar primero por phone/email (GET con filter), si existe
   retornar ID existente, si no crear y retornar ID nuevo
2. `_directus_create()` (L22-37) → retornar el `id` del registro creado
3. Agregar parametro `contact_id: str = ""` a: `log_support_ticket`, `log_conversation`,
   `confirm_payment`, `escalate_to_human`
4. Cada tool guarda `contact_id` como campo relacional M2O

**Nuevo tool a agregar:**
```python
@tool()
def get_customer_360(contact_id: str) -> str:
    """Retorna historial completo del cliente: tickets, conversaciones,
    pagos, deals, lead score."""
```

### 0.3 Crear modelos Pydantic en `services/agno/app/models.py`

**Archivo actual** ya tiene: ResearchReport, LeadReport, TaskSummary, ContentBrief,
VideoScene, VideoStoryboard, SupportTicket, PaymentConfirmation.

**Agregar:**
```python
class StepArtifact(BaseModel):
    """Artefacto estandar entre steps de Prefect flow."""
    content: str
    decisions: list[Decision]
    constraints: list[str]
    quality_signals: dict
    sources: list[str]

class Decision(BaseModel):
    what: str
    why: str
    alternatives_rejected: list[str]
    constraint_for_next: str

class WeeklyPlan(BaseModel):
    """Output del Growth Strategist."""
    week: str
    channels_priority: list[dict]
    topics_by_brand: dict[str, list[str]]
    content_to_pause: list[str]
    allocation: dict[str, float]  # % por area
    kpis_target: dict[str, float]
    cross_brand_insights: list[str]

class ExperimentResult(BaseModel):
    """Resultado de un experimento A/B."""
    experiment_id: str
    variants: list[dict]
    winner: str | None
    winner_metric: str
    learning: str
    confidence: str

class MarketingLearning(BaseModel):
    """Insight estructurado para marketing_learnings."""
    brand: str
    channel: str
    category: str
    insight: str
    evidence: str
    confidence: str
    applicable_to: list[str]
```

### 0.4 Agregar AgNO como dependencia del worker

**Archivo:** `services/workers/pyproject.toml`

**Cambio:** Agregar `"agno[os]"` y `"agno[openai]"` a dependencies para que
los Prefect flows puedan importar y ejecutar agentes AgNO.

**Alternativa:** Si el worker no puede importar agno directamente (conflicto
de dependencias), crear un endpoint HTTP en el servicio agno que el worker
llama via httpx. Menos elegante pero desacoplado.

### 0.5 Crear `services/agno/tools/postiz.py`

Wrapper para Postiz CLI.

```python
# Nuevo archivo
# Funciones: create_post, schedule_post, list_channels, get_analytics
# Usa subprocess para llamar al CLI de Postiz
# O httpx para llamar a la API REST de Postiz
```

### 0.6 Crear colecciones en Directus

Colecciones nuevas necesarias (crear via Directus UI o script):

| Coleccion | Campos clave | Uso |
|-----------|-------------|-----|
| `deals` | contact_id, product, stage, value, next_action, next_action_date, assigned_to | Pipeline ventas Kanban |
| `support_faq` | product, question, answer, times_used, status | FAQ por producto |
| `marketing_learnings` | brand, channel, category, insight, evidence, confidence, applicable_to, source | Memoria L4 |
| `experiments` | experiment_id, topic, variants, start_date, end_date, winner_variant, winner_metric, status | A/B testing |
| `weekly_plan` | week, brand, channels_priority, topics, allocation, kpis_target | Growth Strategist output |
| `social_posts` | content, platform, brand, status, experiment_id, variant, scheduled_at, postiz_id | Posts para publicar |
| `social_analytics` | post_id, platform, views, engagement_rate, saves, shares, completion_rate | Metricas de Postiz |
| `customer_health` | contact_id, product, plan, start_date, renewal_date, usage_score, churn_risk | Post-venta |
| `onboarding_progress` | contact_id, product, steps_completed, current_step, started_at | Tracking onboarding |
| `agent_audit_log` | agent_name, action, input, output, approval_status, approved_by, timestamp | HITL audit trail |

**Campos a agregar a colecciones existentes:**
- `support_tickets`: agregar `contact_id`, `first_response_at`, `resolved_at`, `csat_score`, `channel`
- `conversations`: agregar `contact_id`
- `payments`: agregar `contact_id`

**Referencia:** `scripts/init-directus.py` existe pero esta vacio. Puede usarse
para automatizar la creacion de colecciones via Directus API.

---

## Fase 1 — Contenido + Learnings (semanas 1-2)

### 1.1 Crear `services/agno/agents/researcher.py`

**Reemplaza:** research_agent (agents/research.py), knowledge_agent (agents/knowledge.py),
trend_scout (agents/content/agents.py L54-95), research_planner (agents/deep_research/agents.py L165-188),
research_synthesizer (agents/deep_research/agents.py L195-233), todos los scouts
(agents/deep_research/agents.py L62-155), keyword_researcher (agents/seo/agents.py L39-67),
competitor scouts (agents/competitor/agents.py L16-80)

**Un solo agente con todos los tools de investigacion:**
- DuckDuckGoTools, WebSearchTools (de research_agent)
- KnowledgeTools, knowledge_base (de knowledge_agent)
- TavilyTools, ExaTools, FirecrawlTools (de deep_research scouts, condicional por API key)
- Directus MCP read-items (de support.py L31-50)

**Skills:** deep-search, deep-synthesis, content-strategy, seo-geo, competitive-analysis,
market-intelligence, content-research, community-research, academic-research, github-research,
latam-research (carga todos, el agente usa los relevantes segun el prompt)

**Config:** TOOL_MODEL, tool_call_limit=8, retries=2, compression_manager, learning_minimal

### 1.2 Crear `services/agno/agents/writer.py`

**Reemplaza:** scriptwriter (agents/content/agents.py L105-143), article_writer
(agents/seo/agents.py L76-105), copywriter_es (agents/marketing/agents.py L26-41),
ig_post_agent (agents/social/agents.py L15-28), twitter_post_agent (L30-43),
linkedin_post_agent (L45-58), technical_writer (agents/product_dev/agents.py L56-70),
image_generator (agents/creative/agents.py L20-34), email_agent (agents/utility/agents.py L301-325),
invoice_agent (agents/utility/agents.py L368-398)

**Tools:** FileTools, NanoBananaTools (condicional), Directus MCP create-item,
save_chat_to_directus, save_chat_to_knowledge

**Skills:** content-strategy, seo-geo, copywriting-es

### 1.3 Crear `services/agno/agents/analyst.py`

**Reemplaza:** analytics_agent (agents/content/agents.py L182-224), creative_director
(agents/content/agents.py L150-175), social_auditor (agents/social/agents.py L60-74),
seo_auditor (agents/seo/agents.py L112-146), product_manager (agents/product_dev/agents.py L21-37),
ux_researcher (agents/product_dev/agents.py L39-54), code_review_agent (agents/utility/agents.py L409-448)

**Tools:** CalculatorTools, PythonTools, WebSearchTools, FileTools, Directus MCP read-items,
CodingTools + ReasoningTools (para code review)

**Skills:** campaign-analytics, competitive-analysis, content-strategy, agent-ops

### 1.4 Crear `services/agno/agents/strategist.py`

**Reemplaza:** seo_strategist (agents/marketing/agents.py L43-59),
social_media_planner (agents/marketing/agents.py L61-77)

**Nuevo:** Growth Strategist (no existia)

**Tools:** Directus MCP read-items (analytics, deals, learnings, experiments),
CalculatorTools, PythonTools, WebSearchTools

**Skills:** content-strategy, seo-geo, market-intelligence, campaign-analytics

### 1.5 Crear `services/workers/flows/content_production.py`

**Reemplaza:** `services/agno/workflows/content_production.py`

```python
@flow(name="Content Production", log_prints=True, retries=1)
async def content_production(topic: str, brand: str):
    # Step 1: Research (Researcher agent)
    brief = await research_topic.submit(topic)

    # Step 2: Compact (Python puro, 0 tokens)
    compact = extract_key_points(brief.result())

    # Step 3: Write 3 variants (Writer agent)
    variants = await write_content_variants.submit(compact, brand)

    # Step 4: Evaluate (Analyst agent)
    evaluation = await evaluate_variants.submit(variants.result())

    # Step 5: Store in Directus (httpx, 0 tokens)
    await store_content.submit(variants.result(), evaluation.result(), brand)
```

### 1.6 Crear `services/workers/flows/seo_content.py` (Prefect version)

**Reemplaza:** `services/agno/workflows/seo_content.py`

```python
@flow(name="SEO Content", log_prints=True)
async def seo_content(niche: str, brand: str):
    keywords = await research_keywords.submit(niche)
    article = await write_article.submit(keywords.result(), brand)

    # Audit loop (max 2 rounds) - deterministic, not agent
    for round in range(2):
        audit = await audit_seo.submit(article.result())
        if "PUBLISH" in audit.result().get("verdict", ""):
            break
        article = await revise_article.submit(article.result(), audit.result())

    await store_article.submit(article.result(), brand)
```

### 1.7 Registrar nuevos deployments

**Archivo:** `services/workers/flows/register_deployments.py`

Agregar los nuevos flows de marketing a la lista de deployments (L34-131).
Los property pipeline deployments (L36-50) se pueden comentar o eliminar
ya que no se usaran para marketing.

---

## Fase 2 — Social Media + Experimentacion (semanas 3-4)

### 2.1 Crear `services/workers/flows/social_media.py`

**Reemplaza:** `services/agno/agents/social/agents.py` (social_media_workflow L76-85)

Dos flows separados:
- `social_media_generation`: Lee weekly_plan → Writer genera posts por plataforma → Analyst audita → Store en Directus social_posts (status=draft)
- `social_media_publish`: Lee posts approved → Postiz CLI publica → Log analytics

### 2.2 Setup Postiz

- Agregar Postiz al docker-compose.yml
- Configurar cuentas de social media
- Crear Directus Flow: status cambia a "approved" → trigger social_media_publish

### 2.3 Experimentacion basica

- Writer genera 3 variantes de hook por post (ya lo hace el Scriptwriter actual)
- Cada variante se tagea con experiment_id y variant en social_posts
- Se publican en horarios diferentes via Postiz

---

## Fase 3 — Analytics + Decision Engine (semanas 5-6)

### 3.1 Crear `services/workers/flows/growth_strategist.py`

```python
@flow(name="Growth Strategist", log_prints=True)
async def growth_strategist():
    # Step 1: Gather data (deterministico, 0 tokens)
    analytics = read_directus("social_analytics", last_7_days)
    deals = read_directus("deals", all_open)
    learnings = read_directus("marketing_learnings", all)
    experiments = read_directus("experiments", last_7_days)

    # Step 2: Strategize (Strategist agent, ~3K tokens)
    plan = await invoke_strategist(analytics, deals, learnings, experiments)

    # Step 3: Store (deterministico, 0 tokens)
    save_to_directus("weekly_plan", plan)
```

**Deployment:** `cron="0 7 * * 1"` (lunes 7am)

### 3.2 Crear `services/workers/flows/experiment_analysis.py`

```python
@flow(name="Experiment Analysis", log_prints=True)
async def experiment_analysis():
    # Step 1: Read experiments with variants (deterministico)
    experiments = read_directus("experiments", status="running")

    for exp in experiments:
        # Step 2: Read analytics per variant (deterministico)
        variant_metrics = read_variant_analytics(exp)

        # Step 3: Compare and declare winner (Analyst agent OR deterministico)
        # Si la diferencia es >20%, es deterministico. Si es ambiguo, Analyst.
        result = compare_variants(variant_metrics)

        # Step 4: Store learning (deterministico)
        if result.winner:
            save_to_directus("marketing_learnings", result.learning)
            update_experiment(exp.id, winner=result.winner)
```

**Deployment:** `cron="0 17 * * 5"` (viernes 5pm)

---

## Fase 4 — CRM y Soporte (semanas 7-8)

### 4.1 Configurar Directus Kanban

- Coleccion `deals` con layout Kanban (stages como campo status)
- Coleccion `support_tickets` con layout Kanban por producto
- Directus Flows para automatizaciones:
  - Deal sin actividad 3 dias → crear task
  - Ticket critical 1h → escalacion
  - Ticket resuelto → trigger CSAT

### 4.2 Simplificar soporte

**Archivo actual:** `services/agno/agents/whatsapp_support/agents.py` (238 lineas,
4 agentes + 1 team)

**Nuevo:** `services/agno/agents/support.py` ya existe (83 lineas, 1 agente generico).
Refactorizar para:
1. Support Router: Team minimo con 1 miembro (Support Agent)
   que routea por producto usando skills
2. Support Agent: El agente actual (support.py) + skills por producto
   (whabi, docflow, aurora) + get_customer_360 tool + support_faq tool

### 4.3 Crear `services/workers/flows/sla_compliance.py`

Flow deterministico (0 tokens) que calcula FRT y TTR de tickets.

---

## Fase 5 — Investigacion (semanas 9-10)

### 5.1 Crear `services/workers/flows/deep_research.py` (Prefect version)

**Reemplaza:** `services/agno/workflows/research.py` (deep_research_workflow)

```python
@flow(name="Deep Research", log_prints=True)
async def deep_research(topic: str, angles: list[str] | None = None):
    if not angles:
        angles = ["news", "academic", "community", "technical"]

    # Parallel research (Researcher agent x N)
    futures = [research_angle.submit(topic, angle) for angle in angles]
    results = [f.result() for f in futures]

    # Quality gate (deterministico)
    if sum(len(r) for r in results) < 500:
        return {"error": "Research too thin", "results": results}

    # Synthesize (Researcher agent con instrucciones de sintesis)
    report = await synthesize_research.submit(results, topic)

    # Store
    save_to_directus("documents", report.result())
    return report.result()
```

### 5.2 Crear `services/workers/flows/competitor_intel.py` (Prefect version)

**Reemplaza:** `services/agno/agents/competitor/agents.py` (competitor_intel_workflow)

Mismo patron: parallel(content + pricing + reviews) → synthesize. Pero en Prefect.

### 5.3 Crear `services/workers/flows/research_crawler.py`

**Nuevo:** Research sin tokens via Crawl4AI.

Usa el patron del website_crawler.py existente (L1-50) pero con
AdaptiveCrawling y KeywordRelevanceScorer.

---

## Fase 6 — Automatizacion (semanas 11-12)

### 6.1 Email con HITL

Writer con instrucciones de email + `requires_confirmation=True`.
Invocado desde Prefect task o desde NEXUS chat.

### 6.2 Invoice con HITL

Writer con instrucciones de invoice + `@approval` + `requires_confirmation=True`.
Usa confirm_payment tool (ya tiene HITL).

---

## Fase 7 — Optimizacion (mes 4+)

### 7.1 Experimentacion completa con escalado automatico
### 7.2 Content recycling (Prefect flow)
### 7.3 AI Perception Monitoring
### 7.4 Revenue optimization (con datos de deals)
### 7.5 Campaign orchestration (contenido + email sequences)
### 7.6 Customer health / churn detection
### 7.7 PWA notificaciones real-time

---

## Fase Final — Limpiar

### Archivos a eliminar

```
services/agno/agents/content/          # Reemplazado por writer.py + Prefect flows
services/agno/agents/seo/             # Reemplazado por researcher.py + writer.py + analyst.py
services/agno/agents/social/          # Reemplazado por writer.py + analyst.py + Prefect flows
services/agno/agents/marketing/       # Reemplazado por writer.py + strategist.py
services/agno/agents/competitor/      # Reemplazado por researcher.py + analyst.py + Prefect flows
services/agno/agents/creative/        # Reemplazado por writer.py
services/agno/agents/product_dev/     # Reemplazado por analyst.py
services/agno/agents/deep_research/   # Reemplazado por researcher.py + Prefect flows
services/agno/agents/utility/         # Reemplazado por agentes individuales + Prefect
services/agno/agents/whatsapp_support/ # Reemplazado por support.py simplificado
services/agno/teams/                  # Eliminado (Prefect coordina)
services/agno/workflows/              # Eliminado (Prefect flows)
services/agno/agents/research.py      # Reemplazado por researcher.py
services/agno/agents/knowledge.py     # Absorbido por researcher.py
```

### Archivos a mantener sin cambios

```
services/agno/app/config.py           # Modelos, DB, knowledge (sin cambios)
services/agno/app/shared.py           # Guardrails, learning, compression (sin cambios)
services/agno/tools/chat_export.py    # Funciona bien (sin cambios)
services/agno/tools/sandbox.py        # Funciona bien (sin cambios)
services/agno/skills/                 # Todos se mantienen (los agentes los cargan)
services/agno/knowledge/              # Sin cambios
services/workers/flows/website_crawler.py    # Ya es Prefect, funciona
services/workers/flows/database_backup.py    # Ya es Prefect
services/workers/flows/health_check.py       # Ya es Prefect
services/workers/flows/data_*.py             # Ya son Prefect
services/workers/flows/etl_documents.py      # Ya es Prefect
services/workers/flows/knowledge_indexer.py  # Ya es Prefect
services/workers/flows/export_csv.py         # Ya es Prefect
services/workers/flows/import_csv.py         # Ya es Prefect
services/frontend/                           # Sin cambios
```

### `services/agno/app/main.py` simplificado

De 148 lineas con 42 agentes, 7 teams, 7 workflows → ~40 lineas con 8 agentes, 1 team, 0 workflows:

```python
from agno.os import AgentOS
from agents.researcher import researcher
from agents.writer import writer
from agents.analyst import analyst
from agents.strategist import strategist
from agents.support import support_router, support_agent
from agents.dash import dash
from agents.pal import pal

agent_os = AgentOS(
    id="qyne",
    description="QYNE — Multi-Brand Marketing Platform",
    agents=[researcher, writer, analyst, strategist, support_agent, dash, pal],
    teams=[support_router],
    interfaces=[...],
    db=db,
    tracing=True,
)
```

---

## Metricas de Exito por Fase

| Fase | Metrica | Target |
|------|---------|--------|
| 0 | contact_id vinculado en todos los tools | 100% de registros con relacion |
| 1 | Content production flow produce output equivalente | 3 variantes + evaluacion por run |
| 2 | Posts publicados via Postiz | 3 posts/dia en 3 plataformas |
| 3 | Growth Strategist produce plan semanal | Plan coherente cada lunes |
| 4 | Deals en pipeline, tickets con SLA | >0 deals, SLA compliance >80% |
| 5 | Deep research via Prefect | Reporte completo en <5 min |
| 6 | Email/Invoice con HITL funcionando | Drafts requieren aprobacion |
| Final | main.py con 8 agentes | 0 errores de import, dashboard funcional |
