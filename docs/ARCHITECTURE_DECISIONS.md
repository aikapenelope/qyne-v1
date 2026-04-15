# QYNE v1 — Decisiones de Arquitectura para Produccion

> Documento complementario a `CAPABILITIES.md`. Aqui se definen las decisiones
> tecnicas para los problemas abiertos del sistema, basadas en investigacion
> del estado del arte a abril 2026.

---

## 1. Preservacion de Contexto entre Agentes (El Problema del Telefono)

### El problema

Cuando un agente pasa su output al siguiente en un workflow (Trend Scout → Scriptwriter → Creative Director), el contexto se degrada en cada handoff. Lo que desaparece no es la informacion cruda sino el **contexto de decision**: el *por que* detras de cada eleccion.

Ejemplo concreto en nuestro Content Production Workflow:
1. Trend Scout investiga y elige un tema por razones especificas (relevancia, timing, datos disponibles)
2. Scriptwriter recibe el brief pero pierde las razones de la eleccion
3. Creative Director evalua los scripts sin saber por que se eligio ese tema

### Solucion: Structured Decision Infrastructure

En lugar de pasar solo texto entre steps, cada agente debe emitir un **artefacto estructurado** (Pydantic model) que preserve:

```python
class StepArtifact(BaseModel):
    """Artefacto estandar entre steps de workflow."""
    content: str                    # El output principal
    decisions: list[Decision]       # Decisiones tomadas y por que
    constraints: list[str]          # Restricciones para el siguiente step
    quality_signals: dict           # Metricas de calidad del output
    sources: list[str]              # URLs/referencias usadas

class Decision(BaseModel):
    what: str                       # Que se decidio
    why: str                        # Por que (razonamiento)
    alternatives_rejected: list[str] # Que se descarto y por que
    constraint_for_next: str        # Que implica para el siguiente agente
```

### Implementacion en AgNO

AgNO ya soporta `output_schema` (Pydantic) en agentes. La estrategia:

1. **Cada agente de workflow usa `output_schema`** para emitir structured output
2. **El workflow inyecta el artefacto completo** (no solo `content`) como input del siguiente step
3. **Las instrucciones del siguiente agente** incluyen explicitamente: "Respeta las decisions y constraints del step anterior"
4. **Directus almacena cada artefacto** como registro en una coleccion `workflow_artifacts` para trazabilidad

### Patron de Context Caching de AgNO

AgNO estructura los system messages con **contenido estatico primero, dinamico despues**:

1. Description del agente (estatico — cached)
2. Info de miembros del team (estatico — cached)
3. Instrucciones core (estatico — cached)
4. Memorias del usuario (dinamico)
5. Knowledge recuperado (dinamico)

Esto maximiza cache hits y reduce costos. Para nuestros workflows, las instrucciones de sintesis y handoff deben estar en la parte estatica.

### Patron Recomendado: Workflow con Compaction Explicita

En lugar de pasar el output completo de un agente al siguiente (que puede ser enorme), usar **funciones de compaction** entre steps que:

1. Extraen solo lo relevante para el siguiente step
2. Preservan decisions y constraints
3. Descartan el razonamiento intermedio que no afecta al siguiente

Esto ya existe parcialmente en `_compact_research` del Content Production Workflow. Debe generalizarse a todos los workflows.

---

## 2. Imagenes: Generacion AI para Marketing

### Decision

Generacion de imagenes AI via Image Generator (NanoBanana/Google) para
thumbnails, covers, banners, y variantes de A/B testing. El Writer genera
el prompt descriptivo, el Image Generator produce la imagen, Media Describer
cataloga para accesibilidad.

No se incluye generacion de video. El costo por video AI es alto ($0.15-0.50
por segundo), la calidad es inconsistente, y los templates programaticos
(Remotion, Rendervid) producen resultados visualmente limitados. Si se
necesita video en el futuro, se evalua como servicio externo puntual.

---

## 3. Deep Research sin Tokens: Crawler-First Pipeline

### El problema

El Deep Research Workflow actual usa agentes LLM (Tavily Scout, Exa Scout, etc.) que consumen tokens para cada busqueda. Para investigaciones recurrentes o de gran volumen, esto es costoso.

### Solucion: Pipeline de 2 fases (Crawl → Synthesize)

**Fase 1: Recoleccion (0 tokens LLM)**
Prefect flow que usa Crawl4AI para recolectar datos sin LLM:

```
research_crawler flow:
  1. Recibe: topic, keywords, target_sites[]
  2. Crawl4AI BestFirstCrawling con KeywordRelevanceScorer
     - Adaptive crawling: se detiene cuando tiene suficiente info
     - CSS/XPath extraction para datos estructurados (0 tokens)
     - Markdown output para texto libre
  3. Almacena en Directus: coleccion research_raw
     - url, title, content_markdown, extracted_data, topic, date_crawled
  4. Indexa chunks en LanceDB para busqueda semantica
```

**Fase 2: Sintesis (tokens solo para el reporte final)**
Un solo agente sintetizador lee los datos ya recolectados:

```
research_synthesizer agent:
  1. Lee research_raw de Directus (filtrado por topic)
  2. Busca en LanceDB por relevancia semantica
  3. Sintetiza en reporte estructurado
  4. Costo: ~2,000-5,000 tokens (vs 15,000-50,000 del approach actual)
```

### Capacidades de Crawl4AI relevantes

- **Adaptive Crawling**: Se detiene automaticamente cuando tiene suficiente informacion (coverage + consistency + saturation scoring)
- **BestFirstCrawling**: Prioriza paginas mas relevantes usando KeywordRelevanceScorer
- **JsonCssExtractionStrategy**: Extraccion estructurada sin LLM para sitios con HTML consistente
- **Deep Crawl con BFS/DFS**: Explora sitios completos con control de profundidad
- **Prefetch mode**: 5-10x mas rapido para descubrimiento de URLs
- **Crash recovery**: Resume crawls largos si se interrumpen

### Implementacion como Prefect Flow

```python
@flow(name="Research Crawler")
async def research_crawler(
    topic: str,
    keywords: list[str],
    target_sites: list[str] | None = None,
    max_pages: int = 30,
):
    """Fase 1: Recoleccion sin LLM."""
    # Adaptive crawling con keyword scoring
    config = AdaptiveConfig(
        confidence_threshold=0.8,
        max_pages=max_pages,
        strategy="statistical",  # Sin LLM, sin costo
    )
    # ... crawl, extract, store in Directus, index in LanceDB
```

### Cuando usar cada approach

| Escenario | Approach | Costo |
|-----------|----------|-------|
| Investigacion recurrente (semanal) | Crawler-first | ~0 tokens recoleccion + ~3K sintesis |
| Investigacion ad-hoc desde chat | Deep Research Workflow (agentes) | ~15-50K tokens |
| Monitoreo de competidores | Crawler scheduled (Prefect) | 0 tokens |
| Pregunta puntual | Knowledge Agent (RAG sobre datos ya crawleados) | ~500 tokens |

---

## 4. Social Media: Publicacion sin APIs de Pago

### El problema

Las APIs de X/Twitter y LinkedIn son de pago o tienen acceso restringido. No es viable pagar por API access solo para publicar.

### Solucion: Contenido listo + publicacion via herramienta externa

**Arquitectura recomendada:**

```
Agentes generan contenido → Directus (draft) → Revision humana → Publicacion
```

1. **Social Media Workflow** genera posts adaptados por plataforma (IG, X, LinkedIn)
2. Posts se guardan en Directus coleccion `social_posts` con status="draft"
3. **Revision humana** en Directus UI o NEXUS dashboard (aprobar/editar/rechazar)
4. **Publicacion** via una de estas opciones:

### Opciones de publicacion evaluadas

| Opcion | Costo | Ventaja | Desventaja |
|--------|-------|---------|------------|
| **Postiz** (self-hosted, open source) | $0 (self-hosted) | 30+ plataformas, AI integrado, Apache 2.0 | Requiere setup Docker |
| **Mixpost** (self-hosted, open source) | $0 (self-hosted) | Laravel/Vue, approval workflows, teams | Menos plataformas |
| **n8n + APIs oficiales** | Costo de API | Control total, ya tenemos n8n | APIs de X/LinkedIn son caras |
| **Buffer/Hootsuite** | $15-100/mes | Simple, confiable | SaaS externo, costo recurrente |
| **Manual copy-paste** | $0 | Sin dependencias | No escala |

### Recomendacion: Postiz self-hosted

**Postiz** es open source (Apache 2.0), soporta 30+ plataformas (X, Instagram, LinkedIn, TikTok, YouTube, Reddit, Bluesky, Threads, Telegram, etc.), y se puede self-hostear en Docker.

**Integracion con QYNE:**
1. Agentes generan contenido → Directus `social_posts`
2. n8n trigger: nuevo post con status="approved" → Postiz API
3. Postiz publica en las plataformas configuradas
4. Postiz reporta metricas → n8n → Directus `social_analytics`

Alternativa: si Postiz es demasiado para empezar, el flujo manual funciona:
1. Agentes generan contenido listo para copiar
2. Dashboard muestra posts organizados por plataforma y fecha
3. Copy-paste manual a cada plataforma

---

## 5. CRM: Lead Tracking y Soporte Kanban

### El problema

El CRM actual en Directus es basico: colecciones de contacts, tickets, tasks. Falta:
- Pipeline visual de ventas (Kanban)
- Follow-up automatico con recordatorios
- Kanban de soporte tecnico por producto
- Lead scoring con acciones automaticas

### Arquitectura de CRM recomendada

#### 5.1 Pipeline de Ventas (Kanban)

Coleccion `deals` en Directus con stages:

```
Lead → Contactado → Demo Agendada → Propuesta Enviada → Negociacion → Cerrado Ganado / Perdido
```

Cada deal tiene:
- contact_id (relacion a contacts)
- product (whabi/docflow/aurora)
- stage (el stage actual del Kanban)
- value (valor estimado en USD)
- next_action (que hacer y cuando)
- next_action_date (fecha del proximo follow-up)
- assigned_to (quien es responsable)

**Automatizaciones via n8n:**
- Deal sin actividad por 3 dias → notificacion de follow-up
- Deal en "Propuesta Enviada" por 7 dias → recordatorio automatico
- Nuevo lead con score >= 7 → crear deal automaticamente
- Deal cerrado ganado → trigger onboarding workflow

#### 5.2 Kanban de Soporte Tecnico

Coleccion `support_tickets` con stages por producto:

```
Nuevo → En Progreso → Esperando Cliente → Resuelto → Cerrado
```

Cada ticket tiene:
- product (whabi/docflow/aurora)
- priority (critical/high/medium/low)
- stage (Kanban stage)
- assigned_to
- sla_deadline (basado en priority)
- resolution_notes

**Automatizaciones:**
- Ticket critical sin respuesta en 1h → escalacion automatica
- Ticket "Esperando Cliente" por 48h → recordatorio al cliente
- Ticket resuelto → encuesta de satisfaccion (via WhatsApp)

#### 5.3 Lead Scoring Mejorado

El `lead_scorer` flow actual es basico. Mejorar con:

| Accion | Puntos |
|--------|--------|
| Visita a pricing page | +5 |
| Responde email | +3 |
| Agenda demo | +10 |
| Pregunta por precio en WhatsApp | +7 |
| No responde en 14 dias | -5 |
| Abre ticket de soporte (ya es cliente) | +2 |

Score >= 7 → crear deal automaticamente
Score >= 9 → notificacion urgente al equipo de ventas

#### 5.4 Directus como CRM Visual

Directus ya soporta:
- **Kanban layout** nativo para colecciones (arrastrar cards entre stages)
- **Flows** internos para automatizaciones simples
- **Dashboards** con graficos y metricas
- **Roles y permisos** para que cada equipo vea solo lo suyo

La clave es configurar las colecciones con los campos correctos y los layouts Kanban.

---

## 6. Human-in-the-Loop: Patrones para Produccion

### El problema

Agentes que envian emails, crean invoices, confirman pagos, o publican contenido necesitan supervision humana. Sin HITL, un error del LLM puede enviar un email incorrecto o confirmar un pago falso.

### Los 4 patrones HITL de AgNO

AgNO soporta 4 patrones mutuamente excluyentes por tool:

| Patron | Flag | Comportamiento | Uso |
|--------|------|----------------|-----|
| **Confirmation** | `requires_confirmation=True` | Agente pausa, muestra lo que va a hacer, espera aprobacion | Enviar email, publicar post, crear invoice |
| **User Input** | `requires_user_input=True` | Agente pausa para recoger datos faltantes del usuario | Datos de facturacion, preferencias |
| **User Feedback** | `user_feedback_schema` | Agente pausa para recoger feedback estructurado | Seleccion multiple, ratings |
| **External Execution** | `external_execution=True` | Agente pausa, espera que la accion se ejecute externamente | Pagos, tareas humanas, jobs largos |

### Clasificacion de agentes por nivel de riesgo

| Agente | Riesgo | Patron HITL Recomendado |
|--------|--------|------------------------|
| **Invoice Agent** | ALTO | `@approval` + `requires_confirmation=True` en confirm_payment (ya implementado) |
| **Email Agent** | ALTO | `requires_confirmation=True` en send_email — mostrar draft completo antes de enviar |
| **Scheduler Agent** | MEDIO | `requires_confirmation=True` solo para crear tasks con deadline < 24h |
| **Support Agents** | MEDIO | `@approval(type="audit")` en log_support_ticket — registra para auditoria pero no bloquea |
| **Social Media Agents** | MEDIO | Posts van a Directus como draft, publicacion requiere aprobacion humana separada |
| **Automation Agent** | MEDIO | `requires_confirmation=True` en trigger_prefect_flow para flows destructivos |
| **Content Agents** | BAJO | Sin HITL — generan contenido que siempre pasa por revision humana antes de publicar |
| **Research Agents** | BAJO | Sin HITL — solo generan reportes informativos |

### Patron de Confidence-Based Routing

Para agentes de soporte, implementar routing basado en confianza:

```python
# Pseudo-codigo del patron
if agent_confidence >= 0.9:
    # Responder automaticamente, log para auditoria
    respond_and_log(audit=True)
elif agent_confidence >= 0.6:
    # Responder pero crear task de revision
    respond_and_create_review_task()
else:
    # Escalar a humano inmediatamente
    escalate_to_human()
```

### Timeout y Fallback

Para aprobaciones que no llegan:
- **Email Agent**: Si no hay aprobacion en 30 min, guardar draft en Directus y notificar
- **Invoice Agent**: Si no hay aprobacion en 1h, crear task urgente
- **Support escalation**: Si humano no responde en 2h, re-escalar al siguiente nivel

### Audit Trail

Toda accion de agente con HITL debe registrarse en Directus `agent_audit_log`:
- agent_name, action, input, output, approval_status, approved_by, timestamp
- Esto es critico para compliance y debugging

---

## 7. Observabilidad: AgentOS es Suficiente

### Evaluacion

AgNO AgentOS ya incluye tracing nativo, dashboard visual (os.agno.com),
per-user/per-session isolation, y audit logs. Langfuse agrega dashboards
de costo por agente, evaluaciones LLM-as-judge, y prompt management versionado.

### Pero el costo de Langfuse es prohibitivo

Langfuse v3 requiere ClickHouse como OLAP storage. Requisitos minimos
confirmados por el maintainer: **4 CPU + 16GB RAM** (8GB "at the lower end").
Un usuario reporto que v2 corria en 4GB, v3 necesita el doble. No hay
forma de reducirlo.

Benchmark de overhead (aimultiple.com, 2026):
- LangSmith: ~0% overhead
- Laminar: ~5% overhead
- AgentOps: ~12% overhead
- Langfuse: ~15% overhead (el mas alto de los testeados)

### Decision: No agregar Langfuse

AgentOS cubre el 80% de las necesidades de observabilidad. El 20% restante
(costos por agente, evals automaticas) no justifica duplicar los recursos
del servidor. Si en el futuro se necesitan evals mas sofisticadas, Langfuse
tiene integracion nativa con AgNO via OpenTelemetry (se puede agregar sin
cambiar codigo).

---

## 8. Deep Research: GPT Researcher como Tool de AgNO

### Que es GPT Researcher

Agente autonomo de deep research (26.5K stars, Apache 2.0). Ranked #1 en
benchmarks academicos (Carnegie Mellon DeepResearchGym): 85.36% precision
en citaciones, 90.82% recall. Genera reportes de 2K+ palabras con fuentes.

### Integracion: Como tool del Researcher agent, no como sistema aparte

```python
from gpt_researcher import GPTResearcher
from agno.tools.decorator import tool

@tool()
async def deep_research(query: str, report_type: str = "research_report") -> str:
    """Investigacion profunda autonoma con multiples fuentes."""
    researcher = GPTResearcher(query=query, report_type=report_type)
    await researcher.conduct_research()
    return await researcher.write_report()
```

El Researcher agent de AgNO tiene este tool disponible. Cuando Prefect lo
invoca con instrucciones de "investigacion profunda", el agente decide usar
`deep_research`. Para busquedas simples, usa DuckDuckGo/Tavily directamente.

### Por que no A2A (Agent-to-Agent protocol)

Prefect es mejor que A2A para este caso porque:
- El resultado siempre se guarda en Directus como step intermedio del flow
- Retry, timeout, logging automatico via Prefect
- No necesitas que dos agentes "hablen" entre si
- A2A tiene sentido para agentes de diferentes sistemas. Los nuestros estan
  todos en el mismo sistema.

---

## 9. Reflection Pattern (Mejora de Calidad)

### Que es

El agente genera una respuesta, se critica a si mismo, y refina antes de
entregar. Generate → Reflect → Refine. Mejora pass rates 10-20% en benchmarks.

### Implementacion en Prefect flows

Agregar reflection como step intermedio despues de cada agente que genera
contenido:

```python
@flow
async def write_with_reflection(brief, brand, max_rounds=2):
    draft = await write_content(brief, brand)        # Writer agent
    for round in range(max_rounds):
        critique = await analyze_content(draft, criteria)  # Analyst agent
        if critique.passes:
            break
        draft = await refine_content(draft, critique)  # Writer agent
    return draft
```

El loop es deterministico (Prefect controla max iteraciones). La evaluacion
es inteligente (Analyst agent). Esto ya existe parcialmente en el SEO Content
Workflow (article → audit → revise loop). Debe generalizarse a todos los
flows de contenido.

---

## 10. Mautic: Email Marketing (Fase 7)

### Que agrega

Mautic (8.7K stars, open source, 40K+ empresas) cubre lo que falta para
full-funnel marketing:
- Email sequences automaticas (drip campaigns)
- Landing pages con forms
- A/B testing de emails
- Segmentacion avanzada por comportamiento
- Progressive profiling

### Cuando agregarlo

Fase 7 (mes 4+), cuando el sistema base este funcionando. No es urgente
pero es el upgrade mas potente para revenue: contenido (QYNE) → landing
page (Mautic) → email sequence (Mautic) → CRM (Directus).

### Integracion

Mautic tiene REST API. Directus Flow sincroniza contactos bidireccional.
Prefect flow puede trigger campanas. Self-hosted en Docker (~512MB-1GB RAM).

---

## 11. Resumen de Decisiones

| Area | Decision | Razon |
|------|----------|-------|
| Context entre agentes | Structured Decision Infrastructure (Pydantic artifacts) | Preserva el *por que*, no solo el *que* |
| Video | Eliminado. Costo alto, calidad inconsistente. Solo imagenes AI. | Video AI $0.15-0.50/seg, Remotion visualmente limitado |
| Deep Research | Crawler-first (Crawl4AI + Prefect) → sintesis LLM | 90% menos tokens, datos mas frescos |
| Deep Research (profundo) | GPT Researcher como tool del Researcher agent | #1 en benchmarks, se integra como tool de AgNO |
| Social publishing | Contenido listo en Directus + Postiz self-hosted | Sin costo de API, 30+ plataformas |
| CRM ventas | Kanban en Directus con deals pipeline + auto follow-up | Visual, automatizado, integrado |
| CRM soporte | Kanban por producto con SLA y escalacion | Tracking por producto, prioridades claras |
| HITL | 4 patrones por nivel de riesgo del agente | Seguridad sin friction innecesaria |
| Lead tracking | Scoring mejorado + deal creation automatica | Ningun lead se pierde |
| Observabilidad | AgentOS nativo (no Langfuse) | Langfuse necesita 16GB RAM extra, AgentOS cubre 80% |
| Calidad de contenido | Reflection pattern en Prefect flows | Generate → Reflect → Refine, +10-20% calidad |
| Email marketing | Mautic en Fase 7 | Full-funnel: landing → email sequence → CRM |
| Orquestacion | Prefect backbone (no A2A) | Resultado siempre en Directus, retry/timeout automatico |
