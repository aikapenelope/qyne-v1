# QYNE — Resumen Ejecutivo

> Documento de referencia rapida. Resume los 4 documentos del proyecto
> (MARKETING_PLATFORM.md, ARCHITECTURE_DECISIONS.md, MIGRATION_ROADMAP.md,
> CAPABILITIES.md) en un solo lugar.

---

## Que es

Una plataforma de marketing multi-marca que maneja contenido, SEO, social media,
investigacion, CRM, soporte y analytics para Whabi, Docflow, Aurora (y futuras
marcas) desde un solo dashboard. No es SaaS para vender. Es tu herramienta interna.

El objetivo es L4: el sistema piensa, ejecuta, aprende y mejora cada semana
autonomamente.

---

## Arquitectura (3 capas, 4 componentes)

```
CAPA 1: PREFECT (backbone)
  Controla TODOS los flujos de marketing
  Retry, timeout, scheduling, logging, monitoring
  Steps deterministicos en Python puro (0 tokens)
  Invoca agentes como tasks puntuales
        |
CAPA 2: AgNO (8 agentes)
  4 invocados por Prefect: Researcher, Writer, Analyst, Strategist
  4 conversacionales: Support Router, Support Agent, Dash, Pal
        |
CAPA 3: DIRECTUS + POSTIZ
  Directus: data layer, CRM, Kanban, triggers
  Postiz: publicacion en 30+ plataformas
```

**Por que 8 agentes y no 42:** 70% de los casos se resuelven mejor con un solo
agente bien prompteado. Agent-to-agent communication genera 3-5x mas tokens.
Las instrucciones especificas vienen del Prefect task, no del agente. Un Writer
con instrucciones de Instagram es mas confiable que un Instagram Post Agent dedicado.

---

## Las 35 capacidades (9 bloques)

**Bloque 1 — Contenido (caps 1-3)**
Content Production Pipeline (trend → 3 variantes → evaluacion), Creative Studio
(imagenes AI, catalogacion), Copywriting espanol LATAM.

**Bloque 2 — SEO/GEO (caps 5-7)**
SEO Content Workflow (keyword → articulo → audit loop hasta PUBLISH), GEO/AEO
(optimizacion para citacion en ChatGPT/Perplexity/Gemini), SEO Strategy (plan
mensual por impacto GEO).

**Bloque 3 — Social Media (caps 8-11)**
Posts adaptados por plataforma (IG/X/LinkedIn), auditoria pre-publicacion (score
1-10), calendario semanal (3 posts/dia, rotacion de pilares), publicacion via
Postiz (30+ plataformas, CLI).

**Bloque 4 — Investigacion (caps 12-16)**
Deep Research con agentes (scouts paralelos), Research sin tokens (Crawl4AI +
Prefect, 90% menos costo), Client/Prospect Research, Competitor Intelligence
(content + pricing + reviews paralelo), Market Intelligence (skill transversal).

**Bloque 5 — Analytics (caps 17-20)**
Analytics de contenido (reportes semanales con benchmarks), Dash (preguntas de
negocio por producto), Lead Scoring (diario, deal creation automatica score >= 7),
Sentiment Analysis (keyword-based, sin LLM).

**Bloque 6 — CRM y Ventas (caps 21-27c)**
Pipeline de ventas Kanban (Lead → Contactado → Demo → Propuesta → Cerrado),
Soporte Kanban por producto (con SLA medible, CSAT 1-5, FAQ por producto),
WhatsApp Support Team (router + agente multi-skill), Customer 360 View (historial
completo del cliente), Invoice con HITL, Email con confirmacion, Scheduling,
Onboarding, Customer Health post-venta, Notificaciones (Telegram ahora, PWA futuro).

**Bloque 7 — Knowledge (caps 28-30)**
Website Crawler (BFS/DFS → chunk → classify → index en LanceDB), Knowledge Base
RAG (hybrid search, Voyage AI), Data Operations (sync, cleanup, dedup, enrich,
export/import CSV).

**Bloque 8 — Product Dev (caps 31-32)**
Product Dev Team (RICE scoring + UX + Tech Writer), Code Review (razonamiento
multi-paso).

**Bloque 9 — L4 Strategy (caps 33-35)**
Growth Strategist (plan semanal basado en datos, cross-brand), Experimentation
(A/B de hooks/formatos, 70/20/10, escalado de ganadores), Marketing Learnings
(memoria estructurada por marca/canal/formato con cross-brand intelligence).

---

## Decisiones tecnicas clave

**Context entre agentes:** Pydantic artifacts con decisions, constraints,
quality_signals. Funciones de compaction entre steps. El siguiente agente recibe
el *por que*, no solo el *que*.

**HITL por riesgo:** Invoice/Email = ALTO (confirmation obligatoria). Support =
MEDIO (audit log). Content = BAJO (revision humana post-generacion). Timeouts:
Email 30min, Invoice 1h, Escalation 2h.

**Video:** No incluido. Costo alto ($0.15-0.50/seg), calidad inconsistente,
templates programaticos visualmente limitados. Solo imagenes AI.

**Research sin tokens:** Crawl4AI Adaptive Crawling via Prefect (0 tokens
recoleccion) → LLM solo para sintesis final (~3K tokens). 90% menos costo.

**Social publishing:** Agentes generan → Directus (draft) → revision humana →
Postiz (30+ plataformas). CLI para automatizacion directa.

**CRM:** Directus Kanban nativo. Correccion critica pendiente: tools actuales no
vinculan `contact_id`. Debe corregirse antes de activar CRM.

---

## Migracion: 42 agentes → 8

**4 agentes Prefect (invocados como tasks):**
- **Researcher** — Reemplaza 14 agentes (research, scouts, keyword, competitors)
- **Writer** — Reemplaza 7 agentes (article, copywriter, posts, email)
- **Analyst** — Reemplaza 6 agentes (analytics, creative director, auditors, PM)
- **Strategist** — Reemplaza 3 agentes (growth, SEO strategy, social planner)

**4 agentes AgNO real-time (conversacionales):**
- **Support Router** — Team minimo que routea por producto
- **Support Agent** — 1 agente multi-skill (reemplaza 4 de soporte)
- **Dash** — Analytics conversacional (sin cambios)
- **Pal** — Asistente personal (sin cambios)

**Eliminados:** 3 agentes, 6 de 7 teams, todos los 7 AgNO workflows.
**Nuevos:** 12 Prefect flows de marketing.

---

## Roadmap de construccion

**Fase 0 — Preparacion:** agent_invoker.py, corregir contact_id, modelos Pydantic.

**Fase 1 — Contenido + Learnings (semanas 1-2):** 4 agentes Prefect, flows
content_production y seo_content, coleccion marketing_learnings.

**Fase 2 — Social Media + Experimentacion (semanas 3-4):** Flows social media,
Postiz setup, experimentacion basica (3 variantes por post).

**Fase 3 — Analytics + Decision Engine (semanas 5-6):** Flows growth_strategist
(lunes 7am) y experiment_analysis (viernes). Loop L4 se activa aqui.

**Fase 4 — CRM y Soporte (semanas 7-8):** Pipeline ventas Kanban, Soporte Kanban,
Lead scoring, Support simplificado, Customer 360 View.

**Fase 5 — Investigacion (semanas 9-10):** Deep research, competitor intel,
crawler-first research.

**Fase 6 — Automatizacion (semanas 11-12):** Email HITL, Invoice HITL,
Onboarding.

**Fase 7 — Optimizacion (mes 4+):** Experimentacion completa, content recycling,
AI Perception Monitoring, revenue optimization, campaign orchestration.

---

## Lo que falta (futuro, no bloqueante)

| Gap | Cuando | Dependencia |
|-----|--------|-------------|
| Revenue optimization | Fase 7+ | 3+ meses de datos de deals |
| Campaign orchestrator full-funnel | Fase 7+ | Landing pages + email sequences |
| Customer health / churn detection | Fase 7+ | Datos de uso reales |
| PWA notificaciones real-time | Fase 7+ | Control center definido |
| Soporte via web form y social | Futuro | Postiz monitoring + webhooks |

---

## Correccion critica (Fase 0)

Los tools de Directus (`log_support_ticket`, `log_conversation`, `confirm_payment`)
no vinculan registros a `contact_id`. Sin esta correccion no hay Customer 360 View.
