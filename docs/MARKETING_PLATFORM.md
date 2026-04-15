# QYNE — Plataforma de Marketing Multi-Marca

> Documento de producto. Define que estamos construyendo, por que,
> y como se conecta todo. Este es el documento de referencia.

---

## Vision

Un sistema centralizado donde generas contenido, investigas mercados,
publicas en redes, trackeas leads, y manejas soporte de todas tus
empresas (Whabi, Docflow, Aurora y futuras) desde un solo dashboard.

No es un SaaS para vender. Es tu herramienta interna de marketing.

El objetivo es un sistema L4: no solo ejecuta marketing, sino que
piensa estrategicamente, experimenta, aprende de los resultados,
y mejora autonomamente.

```
Research → Strategy → Generate → Distribute → Measure → Learn → Optimize → Repeat
```

---

## Arquitectura

### Principio fundamental

> **Prefect es el cerebro operativo. AgNO es la inteligencia puntual.
> Directus es la memoria. Postiz es la boca.**

Anthropic ("Building Effective Agents"): "Start with the simplest pattern
that solves the problem. Chains first. Graduate to agentic loops only when
the task genuinely requires dynamic decision-making."

Morph LLM Workflows (2026): "The winning architecture combines a deterministic
backbone with intelligence deployed at specific steps. Agents are invoked
intentionally by the flow, and control always returns to the backbone."

### Las 3 capas

```
CAPA 1: PREFECT (backbone deterministico)
  Todos los flujos de marketing: content, SEO, social, research, experiments
  Scheduling, retry, timeout, logging, monitoring
  Steps deterministicos en Python puro (0 tokens)
  Invoca agentes AgNO como tasks puntuales
    |
    v
CAPA 2: AgNO AGENTES (inteligencia puntual, 8 agentes)
  Se invocan desde Prefect tasks, no entre ellos
  Reciben input estructurado (Pydantic), producen output estructurado
  No hay teams coordinando. Prefect coordina.
    |
    v
CAPA 3: AgNO CONVERSACIONAL (tiempo real)
  WhatsApp Support, Dash, Pal, NEXUS chat
  Necesitan routing dinamico, multi-turno, memoria
  Estos SI usan AgNO teams/routing porque son interactivos
    |
    v
DIRECTUS (memoria) ←→ POSTIZ (publicacion)
  Data layer, CRM, Kanban     30+ plataformas, OAuth, analytics
```

### Los 8 agentes (en lugar de 42)

| Agente | Rol | Donde se invoca |
|--------|-----|----------------|
| **Researcher** | Investiga cualquier tema (web search, Tavily, Exa, Firecrawl) | Prefect tasks |
| **Writer** | Escribe cualquier formato (articulo, post, script, email, copy). Las instrucciones especificas vienen del Prefect task. | Prefect tasks |
| **Analyst** | Analiza datos, compara metricas, produce reportes | Prefect tasks |
| **Strategist** | Sintetiza datos en planes y decisiones estrategicas | Prefect tasks (semanal) |
| **Support Router** | Routing de WhatsApp por producto | AgNO real-time |
| **Support Agent** | Atiende soporte con knowledge base y CRM tools | AgNO real-time |
| **Dash** | Analytics conversacional, preguntas de negocio | AgNO real-time |
| **Pal** | Asistente personal con memoria | AgNO real-time |

**Por que 8 y no 42:** Un agente Writer con instrucciones de Instagram
desde Prefect es mas confiable que un Instagram Post Agent dedicado.
Las instrucciones especificas vienen del contexto del task, no del agente.
Menos agentes = menos handoffs = menos perdida de contexto = menos tokens.

**Datos que respaldan esto:**
- 70% de casos de uso se resuelven mejor con un solo agente bien prompteado (Iterathon, 2026)
- Agent-to-agent communication genera 3-5x mas tokens que single-agent (Iterathon, 2026)
- 80% de sistemas en produccion usan control flow estructurado, no swarms (AGIX, 2026)
- Anthropic recomienda chains primero, agentic loops solo cuando es necesario

### Patron: Prefect flow con agent calls puntuales

```python
@flow(name="Content Production")
async def content_production(topic: str, brand: str):
    # Step 1: Research (AGENTE - necesita razonamiento)
    brief = await research_topic(topic)

    # Step 2: Compact (DETERMINISTICO - 0 tokens)
    compact = extract_key_points(brief)

    # Step 3: Generate variants (AGENTE - necesita creatividad)
    variants = await write_variants(compact, brand)

    # Step 4: Evaluate (AGENTE - necesita juicio)
    evaluation = await analyze_variants(variants)

    # Step 5: Store (DETERMINISTICO - 0 tokens)
    save_to_directus(variants, evaluation, brand)
```

Prefect controla el flujo. Si step 1 falla, Prefect hace retry.
Cada agente es independiente, recibe Pydantic input, produce Pydantic output.
Los steps deterministicos son Python puro. 50-70% menos tokens que todo-en-AgNO.

### Que va en Prefect vs que va en AgNO

| Flujo | Prefect (backbone) | AgNO (real-time) |
|-------|-------------------|-----------------|
| Content Production | Si | - |
| SEO Content | Si | - |
| Social Media Generation | Si | - |
| Deep Research | Si | - |
| Competitor Intel | Si | - |
| Growth Strategist (semanal) | Si | - |
| Experimentation (A/B) | Si | - |
| Lead Scoring | Si | - |
| WhatsApp Support | - | Si (multi-turno) |
| Dash (analytics) | - | Si (ad-hoc) |
| Pal (personal) | - | Si (memoria) |
| NEXUS chat | - | Si (interactivo) |

---

## Las 35 Capacidades (+6 sub-capacidades CRM)

### BLOQUE 1: GENERACION DE CONTENIDO

#### 1. Content Production Pipeline

Workflow completo de tendencia a contenido listo.

**Flujo:** Trend Scout → Compact Brief → Scriptwriter (3 variantes) → Creative Director (evaluacion) → Tu eliges.

**Agentes:**
- **Trend Scout** — Investiga tendencias de las ultimas 48h. Max 3 tool calls. Produce brief con hooks en espanol, relevance score, fuentes. Solo topics con 2+ fuentes credibles y score 7+.
- **Scriptwriter** — 3 variantes de storyboard por brief: emocional, data-driven, provocativo. 5-6 escenas, max 15 palabras por oracion. Guarda como JSON.
- **Creative Director** — Evalua las 3 variantes: mood, flujo escena por escena, momento mas fuerte, debilidad. Recomienda la mejor con justificacion.
- **Analytics Agent** — Post-publicacion. Reportes semanales: top/bottom posts, analisis por pilar y hook type, 3 recomendaciones data-driven.

**Output:** 3 guiones listos con evaluacion creativa. Tu decides cual producir.

#### 2. Video Programatico

Templates profesionales pre-disenados que se llenan con JSON de contenido.

**Estrategia:** La calidad visual viene del template, no del agente. Un disenador crea templates de alta calidad una vez. Los agentes solo generan el contenido (hook, features, stats, CTA).

**Templates target:**
- PromoProduct — Video promocional de producto
- DataStory — Video con datos/estadisticas
- Explainer — Video explicativo paso a paso
- TikTok/Reels — Formato vertical con captions

**Opciones de rendering:**
- Remotion (React, licencia comercial $100+/mes)
- Rendervid (open source, JSON nativo, MCP server integrado)
- Creatomate (API REST, template editor visual)

**Colores por marca:** Whabi (#25D366), Docflow (#e94560), Aurora (#8B5CF6). Automaticos segun campo `brand`.

**Flujo:** Disenador crea template → Template se registra con JSON schema → Content Team genera JSON → Rendering automatico → Video listo.

#### 3. Creative Studio

Team de 3 agentes en modo route para generacion de media.

- **Image Generator** — Imagenes AI desde prompts. Ratio 1:1 para social, 9:16 para stories. Prompts detallados: subject, style, lighting, composition, mood.
- **Video Generator** — Videos cortos desde imagenes y prompts. Transiciones suaves, estilo consistente.
- **Media Describer** — Describe media para accesibilidad y catalogacion. Subject, setting, colores, mood, texto visible.

**Uso:** Thumbnails, covers, variantes para A/B testing, catalogacion automatica.

#### 4. Copywriting

Copywriter ES para todo el copy en espanol LATAM neutral.

**Formatos:** Landing pages, email sequences, ad copy, social posts, descripciones de producto.

**Reglas:** Profesional pero cercano. Tu para informal, usted para formal. Sin clickbait, sin exageracion, sin claims sin datos. Cita fuentes siempre.

---

### BLOQUE 2: SEO Y POSICIONAMIENTO EN AI

#### 5. SEO Content Workflow

Pipeline de articulos optimizados para Google Y para motores AI.

**Flujo:** Keyword Researcher → Article Writer → SEO Auditor → Loop (max 2 rondas hasta veredicto PUBLISH).

**Agentes:**
- **Keyword Researcher** — Encuentra topics con alto potencial GEO. Busca gaps donde no existe buen listicle en espanol. Output estructurado: topic, target query, keywords primario/secundarios, competencia, datos disponibles, angulo unico para nuestros productos.
- **Article Writer** — Articulos de 1500-2500 palabras en espanol. Estructura obligatoria:
  1. Quick Answer (primeros 200 words) — lista numerada, extractable por AI
  2. Introduccion (200-300 words) — por que importa ahora, 2-3 stats con URLs
  3. Entries detallados (300-500 words cada uno) — features, limitaciones, precio
  4. Tabla comparativa — markdown con diferenciadores clave
  5. How to Choose (200 words) — framework de decision
  6. FAQ (4-5 preguntas) — matching queries exactas de ChatGPT/Perplexity
- **SEO Auditor** — Checklist GEO (Quick Answer, listicle, evidence density, FAQ, freshness) + SEO (titulo <60 chars, meta description, H2/H3, tabla, >1500 words). Score X/100. Veredicto: PUBLISH / REVISE / REWRITE.

**Output:** Articulo MDX con frontmatter, listo para publicar en blog.

#### 6. GEO/AEO (Generative Engine Optimization)

Optimizacion para que ChatGPT, Perplexity, Gemini y AI Overviews citen tu contenido.

**Integrado en todos los agentes de contenido via skill seo-geo:**
- Quick Answer blocks en primeros 200 words (lo que AI extrae)
- Formato listicle numerado (74.2% de citaciones AI vienen de listicles)
- FAQ Section matching queries exactas de usuarios en AI engines
- Schema Markup triple: Article + ItemList + FAQPage JSON-LD
- Freshness protocol: actualizar cada 7-14 dias, fechas visibles
- Palabras prohibidas: "premier", "lider", "revolucionario" (AI filtra marketing fluff)
- Palabras obligatorias: numeros especificos, fechas, fuentes con URL

**Distribucion post-publicacion:**
- Reddit (46.7% de citaciones de Perplexity vienen de Reddit)
- LinkedIn post con data points clave
- Quora answer linkeando al articulo

#### 7. SEO Strategy

SEO Strategist como agente dedicado a estrategia, no ejecucion.

**Capacidades:** Keyword gaps entre nuestro contenido y competidores. AI citation potential por topic. Competitor content analysis. Estrategia unificada para las 3 marcas.

**Output:** Plan de contenido mensual con topics priorizados por impacto GEO.

---

### BLOQUE 3: SOCIAL MEDIA

#### 8. Posts Adaptados por Plataforma

Un agente por plataforma, cada uno optimizado para su algoritmo.

- **Instagram Post Agent** — Reels/Stories. Visual hooks, trending audio, carousels. Hashtags 10-15 (mix broad + niche). Captions obligatorios (85% mira sin sonido). Sweet spot: 30-45s.
- **Twitter/X Post Agent** — Threads 5-7 tweets. Hooks data-driven, preguntas de engagement. Max 280 chars/tweet. Datos concretos, no opiniones.
- **LinkedIn Post Agent** — Posts profesionales. Insights de industria, case studies, analisis. Line breaks para legibilidad. Tono autoridad.

#### 9. Auditoria de Contenido Social

Social Auditor evalua cada post antes de publicar.

**Checklist:** Platform fit, engagement potential, hashtag quality, CTA clarity, timing recomendado. Score 1-10 con mejoras especificas por post.

#### 10. Calendario de Contenido

Social Media Planner genera calendarios semanales.

**Estructura:** Post type, topic, hook, CTA, hashtags por plataforma. 3 posts/dia. Rotacion de pilares (nunca el mismo pilar 2 veces seguidas). Lunes-viernes educativo/tendencias. Sabado behind-the-scenes. Domingo recap semanal.

**Output:** JSON estructurado por dia con todos los campos listos.

#### 11. Publicacion via Postiz

Postiz self-hosted como capa de publicacion.

**Integracion:**
1. Agentes generan contenido → Directus `social_posts` (status="draft")
2. Revision humana en Directus/NEXUS → status="approved"
3. Directus Flow trigger → Postiz API o CLI
4. Postiz publica en 30+ plataformas
5. Analytics de Postiz → Directus `social_analytics`

**CLI para automatizacion directa:**
```bash
postiz posts:create \
  -c "Contenido del post" \
  -m "imagen.png" \
  -s "2026-04-15T09:00:00Z" \
  -i "twitter-id,linkedin-id,instagram-id"
```

**Plataformas:** X, LinkedIn, Instagram, TikTok, YouTube, Reddit, Bluesky, Threads, Telegram, Discord, Pinterest, Mastodon, Medium, WordPress, Hashnode, Dev.to, y 14 mas.

---

### BLOQUE 4: INVESTIGACION E INTELIGENCIA

#### 12. Deep Research (con agentes)

Para investigaciones ad-hoc desde el chat.

**Flujo:** Research Planner → scouts paralelos (Tavily, Exa, Firecrawl, WebSearch) → Quality Gate (min 200 chars) → Research Synthesizer.

**Cada scout tiene un angulo diferente** (sin overlap). El planner asigna queries especificas a cada uno segun sus fortalezas.

**Output:** Reporte markdown con Executive Summary, Key Findings (con URLs), Analysis, Gaps, Recommendations, Sources. En espanol para temas LATAM.

**Costo:** ~15,000-50,000 tokens por investigacion.

#### 13. Research sin Tokens (Crawler-First)

Para investigaciones recurrentes o de gran volumen.

**Fase 1 — Recoleccion (0 tokens):**
Prefect flow con Crawl4AI:
- Adaptive Crawling con KeywordRelevanceScorer (se detiene cuando tiene suficiente info)
- BestFirstCrawling (prioriza paginas mas relevantes)
- CSS/XPath extraction para datos estructurados
- Almacena en Directus `research_raw`
- Indexa chunks en LanceDB

**Fase 2 — Sintesis (~3,000 tokens):**
Un agente lee los datos ya recolectados de Directus/LanceDB y sintetiza el reporte.

**Ahorro:** 90% menos tokens que el approach con agentes.

**Uso:** Monitoreo semanal de competidores, tracking de tendencias, investigacion de mercado recurrente.

#### 14. Client/Prospect Research

Investigacion rapida de un prospecto o cliente.

**Flujo:** Parallel(Web Research + Knowledge Base) → Synthesis Agent → ResearchReport (Pydantic structured output).

**Uso:** Antes de una llamada de ventas, investigar al prospecto combinando datos publicos con tu knowledge base interna.

#### 15. Competitor Intelligence

Analisis competitivo paralelo con sintesis accionable.

**Flujo:** Parallel(Content Scout + Pricing Scout + Reviews Scout) → Synthesizer.

- **Content Scout** — Estrategia de contenido del competidor: topics, frecuencia, engagement, gaps donde no publican.
- **Pricing Scout** — Pricing pages: planes, precios, features por tier, free trial.
- **Reviews Scout** — Reviews de G2, Capterra, ProductHunt, Reddit. Praise comun, quejas comunes, feature requests.
- **Synthesizer** — Landscape overview, tabla de pricing, gaps de contenido (oportunidades para nosotros), sentiment, 3-5 acciones.

**Frameworks incluidos:** Quick Assessment, SWOT, Feature Matrix, Positioning Map.

#### 16. Market Intelligence

Skill transversal que ensena a todos los agentes de investigacion.

- Jerarquia de fuentes: SEC filings > Statista/Gartner > Crunchbase > News > Blogs > Social
- Query patterns para market size, competitor analysis, pricing intel, datos LATAM
- Extraccion estandarizada: metrica, valor, fuente, fecha, scope
- Output: MARKET_DATA, COMPETITIVE_LANDSCAPE, TRENDS, GAPS, CONFIDENCE

---

### BLOQUE 5: ANALYTICS Y PERFORMANCE

#### 17. Analytics de Contenido

Analytics Agent genera reportes semanales de performance social.

**Metricas por plataforma:**

| Plataforma | Good | Great | Viral |
|------------|------|-------|-------|
| IG Reels views (24h) | 500+ | 5,000+ | 50,000+ |
| IG engagement rate | >3% | >6% | >10% |
| TikTok views (24h) | 1,000+ | 10,000+ | 100,000+ |
| TikTok completion rate | >30% | >50% | >70% |

**Reporte semanal:** Total posts, total views, avg engagement, follower growth, best platform, top 3 posts con analisis de por que funcionaron, bottom 3 con diagnostico, performance por pilar, performance por tipo de hook, 3 recomendaciones para la semana siguiente.

**Reglas de optimizacion:**
- 3-second rule: si retention cae bajo 50% a los 3s, el hook fallo
- Engagement > Views: 1000 views con 10% engagement > 10000 views con 1%
- Saves = valor (contenido de referencia)
- Shares = resonancia emocional
- Consistency > virality

#### 18. Dash (Business Analytics)

Agente de analytics que responde preguntas de negocio.

**Por producto:**
- Whabi: leads, conversion rate, response time, revenue
- Docflow: documents processed, compliance rate, active clinics
- Aurora: active users, voice commands/day, retention, churn

**Output siempre:** El numero especifico + tendencia (up/down/stable vs periodo anterior) + que significa + accion recomendada.

**Herramientas:** Calculator, Python, Directus MCP (lee cualquier coleccion).

#### 19. Lead Scoring

Prefect flow diario que recalcula scores.

| Accion | Puntos |
|--------|--------|
| Visita pricing page | +5 |
| Responde email | +3 |
| Agenda demo | +10 |
| Pregunta por precio en WhatsApp | +7 |
| No responde en 14 dias | -5 |
| Abre ticket de soporte (ya es cliente) | +2 |

**Automatizaciones:**
- Score >= 7 → crear deal automaticamente en pipeline de ventas
- Score >= 9 → notificacion urgente al equipo

#### 20. Sentiment Analysis

Prefect flow diario. Keyword-based (sin LLM, sin costo). Analiza conversaciones de soporte y clasifica sentimiento. Alimenta dashboards en Directus.

---

### BLOQUE 6: CRM Y VENTAS

#### 21. Pipeline de Ventas (Kanban)

Coleccion `deals` en Directus con layout Kanban.

**Stages:** Lead → Contactado → Demo Agendada → Propuesta Enviada → Negociacion → Cerrado Ganado / Cerrado Perdido

**Cada deal:** contact_id, product, stage, value (USD), next_action, next_action_date, assigned_to.

**Automatizaciones (Directus Flows + Prefect):**
- Deal sin actividad 3 dias → notificacion follow-up
- Deal en "Propuesta Enviada" 7 dias → recordatorio automatico
- Nuevo lead score >= 7 → crear deal
- Deal cerrado ganado → trigger onboarding

#### 22. Soporte Multi-Producto (Kanban)

Coleccion `support_tickets` con Kanban por producto.

**Stages:** Nuevo → En Progreso → Esperando Cliente → Resuelto → Cerrado

**Cada ticket:** contact_id (relacion a contacts), product (whabi/docflow/aurora),
priority (critical/high/medium/low), stage, assigned_to, sla_deadline,
first_response_at, resolved_at, csat_score, resolution_notes.

**SLA medible:**
- `first_response_at` y `resolved_at` permiten calcular FRT y TTR reales
- Prefect flow diario calcula SLA compliance por producto
- Dashboard en Directus muestra % de tickets dentro de SLA

**CSAT (satisfaccion del cliente):**
- Ticket resuelto → agente envia mensaje con escala 1-5 via WhatsApp
- Respuesta se guarda en `support_tickets.csat_score`
- Prefect flow semanal calcula CSAT promedio por producto

**Automatizaciones:**
- Ticket critical sin respuesta 1h → escalacion
- Ticket "Esperando Cliente" 48h → recordatorio al cliente
- Ticket resuelto → encuesta de satisfaccion via WhatsApp
- SLA por vencerse (80% del tiempo) → alerta preventiva

#### 23. WhatsApp Support Team

Router que dirige mensajes al agente correcto por producto.

- **Whabi Support** — Plans $49/$149/custom. Template approval, webhook config, contact import.
- **Docflow Support** — Plans $99/$249/custom. Document upload, permissions, retention.
- **Aurora Support** — Plans $0/$29/$79. Mic permissions, PWA install, voice recognition.
- **General Support** — Fallback para consultas generales, partnerships, careers.

**Cada interaccion automaticamente:**
- Guarda contacto (`save_contact`)
- Registra ticket (`log_support_ticket`)
- Registra conversacion con intent, sentiment, lead_score (`log_conversation`)
- Crea task de follow-up si es de alto valor
- Escala a humano si es critico (`escalate_to_human`)

**Customer 360 View (CORRECCION CRITICA):**

> **Estado actual del codigo:** Los tools `log_support_ticket`, `log_conversation`,
> y `confirm_payment` NO vinculan registros a un `contact_id`. Cada ticket,
> conversacion y pago se crea como registro independiente sin relacion al contacto.
> `save_contact` crea el contacto pero no retorna el ID para usarlo en registros
> posteriores.

**Lo que debe corregirse:**
1. `save_contact` debe retornar el `contact_id` de Directus (o buscarlo si ya existe por phone/email)
2. Todos los tools (`log_support_ticket`, `log_conversation`, `confirm_payment`) deben
   recibir y guardar `contact_id` como relacion M2O a la coleccion `contacts`
3. Nuevo tool `get_customer_360(contact_id)` que el agente de soporte llama al inicio
   de cada conversacion. Retorna: tickets anteriores, conversaciones pasadas, plan actual,
   pagos, deals en pipeline, lead score. Esto se inyecta como contexto.

**Resultado:** El agente de soporte sabe que un cliente que llama por tercera vez
por el mismo problema necesita trato diferente. Ve todo el historial antes de responder.

#### 23b. FAQ de Soporte por Producto

Coleccion `support_faq` en Directus.

**Campos:** product, question, answer, times_used, last_used, status (draft/published).

**Flujo:**
1. Agente de soporte busca en FAQ primero (query por producto)
2. Si encuentra respuesta aprobada, la usa directamente (rapido, consistente)
3. Si no encuentra, busca en knowledge base general (LanceDB)
4. Si resuelve algo nuevo, crea un FAQ draft para revision humana

**Beneficio:** Respuestas consistentes para preguntas frecuentes. Tracking de que
preguntas se repiten mas (para mejorar documentacion y producto).

#### 23c. Soporte Multi-Canal

**Estado actual:** Solo WhatsApp. Pero clientes pueden escribir por email,
formulario web, o redes sociales.

**Solucion:** Directus Flows que reciben webhooks de diferentes canales y crean
tickets con campo `channel` (whatsapp/email/web/social). Los agentes de soporte
ven todos los tickets en el mismo Kanban independientemente del canal de origen.

**Implementacion por fases:**
- Fase 4: WhatsApp (ya definido)
- Fase 6: Email (via Email Agent)
- Futuro: Web form (Directus Flow con webhook), social (via Postiz monitoring)

#### 24. Invoice y Billing

Invoice Agent con pricing de las 3 marcas.

**Pricing:**
- Whabi: Starter $49/mes, Pro $149/mes, Enterprise custom
- Docflow: Basic $99/mes, Pro $249/mes, Enterprise custom
- Aurora: Free $0, Pro $29/mes, Business $79/mes

**HITL obligatorio:** `confirm_payment` requiere aprobacion humana (@approval). Nunca confirma un pago sin intervencion humana. Registra cada interaccion de billing como ticket.

#### 25. Email

Email Agent redacta y envia emails profesionales.

**Reglas de produccion:**
- HITL: `requires_confirmation=True` — siempre muestra draft completo antes de enviar
- Nunca envia sin confirmacion explicita del usuario
- Si EmailTools no esta configurado, genera draft como texto para copy-paste
- Espanol LATAM neutral

#### 26. Scheduling y Recordatorios

Scheduler Agent crea tareas y recordatorios en Directus CRM.

- "Recuerdame llamar a Juan el viernes" → task en Directus
- "Que tengo pendiente esta semana?" → lista tasks
- Timezone America/Bogota por defecto
- HITL: `requires_confirmation=True` solo para tasks con deadline < 24h

#### 27. Onboarding de Clientes

Onboarding Agent guia nuevos clientes paso a paso.

- Identifica producto (Whabi/Docflow/Aurora)
- UN paso a la vez, nunca dump de informacion
- Busca en knowledge base para respuestas especificas
- Asume cero conocimiento tecnico
- Usa skills especificos por producto (whabi, docflow, aurora)
- Tracking de completitud: coleccion `onboarding_progress` con steps completados por cliente

#### 27b. Customer Health (Post-Venta)

Tracking de salud del cliente despues del onboarding.

**Coleccion `customer_health`:**
- contact_id, product, plan, start_date, renewal_date
- usage_score (basado en actividad: tickets, logins, uso de features)
- churn_risk (high/medium/low, calculado por Prefect flow semanal)
- upsell_potential (Starter que podria ser Pro, basado en uso)

**Automatizaciones:**
- churn_risk sube a "high" → notificacion + task de retencion
- renewal_date en 30 dias → recordatorio de renovacion
- usage_score alto + plan basico → sugerencia de upsell

**Implementacion:** Fase 7 (necesita datos de uso reales de los productos).

#### 27c. Notificaciones y Control Center

**Dashboard NEXUS** es el control center principal. Ya muestra mensajes de WhatsApp.

**Notificaciones en tiempo real (futuro):**
- PWA con push notifications para situaciones criticas:
  - Ticket critical sin respuesta
  - Deal de alto valor necesita follow-up
  - SLA por vencerse
  - Escalacion a humano pendiente
- Alternativa: Telegram/Slack bot para notificaciones urgentes
- El control center debe ser la experiencia principal: limpio, rapido,
  con toda la informacion relevante sin tener que abrir Directus

**Implementacion por fases:**
- Fase 4: Notificaciones basicas via Directus Flows (webhook a Telegram)
- Fase 7: PWA con push notifications en tiempo real

---

### BLOQUE 7: KNOWLEDGE Y DATA

#### 28. Website Crawler

Prefect flow para crawl profundo de sitios web.

**Pipeline:** Discover (BFS/DFS/BestFirst) → Fetch (Crawl4AI con JS rendering) → Chunk (por headers, max 500 tokens) → Classify (27 keywords) → Dedup → Store (Directus `documents`) → Index (LanceDB con Voyage AI embeddings).

**Uso:** Crawlear documentacion de competidores, blogs de industria, sitios de referencia. Todo queda indexado y buscable por agentes via RAG.

**Parametros:** url, max_pages, max_depth, include_paths, exclude_paths, index_in_knowledge.

#### 29. Knowledge Base (RAG)

LanceDB local con Voyage AI embeddings.

- Hybrid search (vector + keyword)
- Indexacion automatica de PDFs, TXT, MD, CSV, JSON
- Knowledge Agent dedicado para consultas
- Agentic RAG: el agente decide cuando buscar en knowledge (no pre-carga todo)

**Flujo de indexacion:** Documento → Docling parse → Directus `documents` → Voyage AI embeddings → LanceDB chunks → Agentes buscan semanticamente.

#### 30. Data Operations

Prefect flows para mantenimiento de datos:

- **data_sync** — Sincroniza entre colecciones con field mapping
- **data_cleanup** — Encuentra duplicados y datos viejos (solo reporta)
- **dedup_merger** — Merge inteligente de contactos duplicados por email
- **data_enricher** — Campos computados: clasificacion de dominio email, boost de lead score
- **export_csv** — Exporta cualquier coleccion a CSV en RustFS
- **import_csv** — Importa CSV a cualquier coleccion

---

### BLOQUE 8: PRODUCT DEVELOPMENT

#### 31. Product Dev Team

Team coordinado para analisis de features.

- **Product Manager** — RICE scoring (Reach, Impact, Confidence, Effort). Prioriza roadmap, escribe specs.
- **UX Researcher** — Valida desde perspectiva usuario. Pain points, accesibilidad, learning curve, edge cases.
- **Technical Writer** — Documentacion: overview → prerequisites → step-by-step → troubleshooting. En espanol.

**Uso:** "Analiza si deberiamos agregar [feature] a Whabi" → PM analiza, UX valida, Tech Writer documenta.

#### 32. Code Review

Code Review Agent con razonamiento multi-paso (2-5 steps).

**Checklist:** SQL injection, XSS, hardcoded secrets, race conditions, error handling, edge cases.

**Output:** SEVERITY (critical/warning/info), ISSUE (file:line), FIX (codigo especifico), WHY (impacto).

---

### BLOQUE 9: ESTRATEGIA Y CRECIMIENTO AUTONOMO (L4)

Este bloque es lo que convierte el sistema de "ejecuta bien" a
"piensa, ejecuta, aprende, mejora". Sin esto, tienes un sistema L3
muy fuerte. Con esto, es L4.

#### 33. Growth Strategist Agent (Decision Engine)

El cerebro estrategico del sistema. Cada lunes produce un plan semanal
basado en datos reales, no intuicion.

**Inputs (lee automaticamente):**
- Analytics Agent: performance de contenido de la semana anterior
- Dash: metricas de negocio por producto (leads, conversion, revenue)
- Competitor Intel: movimientos recientes de competidores
- Lead Scorer: estado del pipeline de ventas
- `marketing_learnings`: insights acumulados de semanas anteriores

**Outputs (escribe en Directus `weekly_plan`):**
- Canales a priorizar esta semana (y por que)
- Topics a producir (con angulo especifico por marca)
- Contenido a pausar o matar (bajo performance sostenido)
- Allocation de esfuerzo: % contenido vs % SEO vs % social vs % research
- KPIs target para la semana
- Cross-brand insights: "esto funciono en Aurora, probar en Whabi"

**Trigger:** Prefect flow cada lunes 7am. Lee datos, ejecuta Growth Strategist,
guarda plan en Directus. El plan aparece en el dashboard NEXUS.

**Reglas:**
- Siempre justifica decisiones con datos (no "creo que" sino "engagement subio 40% cuando...")
- Compara performance cross-brand para detectar patrones transferibles
- Aplica el patron 70/20/10: 70% contenido probado, 20% variaciones, 10% experimentos nuevos
- Si no hay datos suficientes (primeras semanas), produce plan conservador y lo dice explicitamente

**Por que es critico:** Sin este agente, produces contenido sin direccion.
Con el, cada pieza de contenido tiene un proposito estrategico.

#### 34. Experimentation System

Convierte la generacion de contenido en un loop de mejora continua.
No es un sistema separado — es una extension del Content + Analytics workflow.

**Como funciona:**

1. **Generacion de variantes:** El Scriptwriter ya genera 3 variantes por brief
   (emocional, data-driven, provocativo). Esto se extiende a hooks de social media:
   mismo contenido → 3-5 hooks diferentes.

2. **Publicacion A/B:** Las variantes se publican en horarios diferentes via Postiz.
   Cada variante se tagea en Directus `social_posts` con `experiment_id` y `variant`.

3. **Medicion:** Analytics Agent compara performance de variantes despues de 48h.
   Metricas: engagement rate, saves, shares, completion rate.

4. **Declaracion de ganador:** Si una variante supera a las demas por >20% en
   engagement, se declara ganadora. Se registra en `marketing_learnings`.

5. **Escalado:** El ganador se re-publica en mas plataformas/horarios.
   Los perdedores se archivan con diagnostico de por que fallaron.

**Patron 70/20/10 (gestionado por Growth Strategist):**
- **70% Exploit** — Contenido con formatos/hooks que ya probaron funcionar
- **20% Explore** — Variaciones de lo que funciona (nuevo hook, mismo formato)
- **10% Leap** — Formatos o angulos completamente nuevos

**Que se experimenta:**
- Hooks (pregunta vs dato vs provocacion vs storytelling)
- Formatos (carrusel vs reel vs thread vs post largo)
- Horarios (manana vs tarde vs noche)
- Pilares (AI trends vs tools vs business vs tutorials)

**Coleccion Directus `experiments`:**
```
experiment_id, topic, variants[], start_date, end_date,
winner_variant, winner_metric, learning_extracted, status
```

**Por que es critico:** Sin experimentacion, repites lo que "crees" que funciona.
Con experimentacion, tienes datos de que realmente funciona. El sistema mejora
cada semana automaticamente.

#### 35. Marketing Learnings (Memoria Estructurada)

Base de conocimiento que acumula lo que funciona y lo que no, por marca,
canal, formato, y audiencia. Es la memoria a largo plazo del sistema.

**Coleccion Directus `marketing_learnings`:**
```
brand: "docflow"
channel: "instagram"
category: "hook_type"
insight: "Hooks emocionales generan 3.2x mas engagement que data-driven"
evidence: "Comparacion de 12 posts en 4 semanas. Emocional avg 8.5% vs data 2.7%"
confidence: "high"  (high/medium/low basado en cantidad de evidencia)
date_learned: "2026-04-15"
source: "experiment_042"  (link al experimento que genero el insight)
applicable_to: ["docflow", "whabi"]  (marcas donde aplica)
```

**Quien escribe:**
- Analytics Agent: despues de cada reporte semanal
- Growth Strategist: despues de cada plan semanal (insights cross-brand)
- Experiment System: despues de cada experimento completado

**Quien lee:**
- Content Team: antes de generar contenido, consulta learnings relevantes
- Social Media Planner: al crear calendario, prioriza formatos que funcionan
- Growth Strategist: al crear plan semanal, basa decisiones en learnings acumulados
- SEO Strategist: al definir topics, consulta que angulos funcionan por marca

**Implementacion en AgNO:** Skill `marketing-learnings` que los agentes cargan.
El skill les ensena a consultar la coleccion antes de generar y a escribir
nuevos insights cuando detectan patrones.

**Multi-brand intelligence (tu ventaja competitiva):**
El campo `applicable_to` permite que un insight de Aurora se aplique a Docflow.
El Growth Strategist detecta estos patrones automaticamente:
- "Formato listicle funciona en Docflow LinkedIn. Docflow y Whabi comparten audiencia B2B. Probar listicle para Whabi."
- "Hook de pregunta funciona en Aurora Instagram. Aurora y Docflow son ambos health-adjacent. Probar en Docflow."

Esto es algo que casi ninguna empresa tiene: aprendizaje cruzado entre marcas
con evidencia estructurada.

**Por que es critico:** Sin memoria estructurada, cada semana empiezas de cero.
Con ella, el sistema acumula conocimiento y cada decision es mejor que la anterior.

---

### Como se conectan las 3 capacidades L4

```
Lunes 7am:
  Prefect trigger → Growth Strategist Agent
    Lee: analytics, CRM, learnings, experiments
    Produce: weekly_plan en Directus

Lunes-Viernes:
  Content Team genera contenido segun weekly_plan
    Lee: marketing_learnings antes de generar
    Genera: 3-5 variantes por pieza (experimentacion)
    Publica: via Postiz con experiment_id

Viernes:
  Analytics Agent genera reporte semanal
    Compara: variantes de experimentos (declara ganadores)
    Escribe: nuevos insights en marketing_learnings
    Escala: ganadores a mas plataformas

Lunes siguiente:
  Growth Strategist lee los nuevos learnings
    Ajusta: plan basado en lo que funciono
    Detecta: patrones cross-brand
    Produce: nuevo weekly_plan mejorado

→ Loop infinito de mejora
```

---

## Decisiones de Arquitectura

### Context entre Agentes

**Problema:** Cuando un agente pasa output al siguiente, se pierde el *por que* de las decisiones.

**Solucion:** Cada agente emite un artefacto Pydantic estructurado:

```python
class StepArtifact(BaseModel):
    content: str                    # Output principal
    decisions: list[Decision]       # Que se decidio y por que
    constraints: list[str]          # Restricciones para el siguiente step
    quality_signals: dict           # Metricas de calidad
    sources: list[str]              # URLs/referencias

class Decision(BaseModel):
    what: str                       # Que se decidio
    why: str                        # Razonamiento
    alternatives_rejected: list[str] # Que se descarto
    constraint_for_next: str        # Implicacion para el siguiente agente
```

Funciones de compaction entre steps extraen solo lo relevante, preservando decisions y constraints.

### Human-in-the-Loop por Nivel de Riesgo

| Agente | Riesgo | Patron |
|--------|--------|--------|
| Invoice Agent | ALTO | `@approval` + `requires_confirmation` |
| Email Agent | ALTO | `requires_confirmation` (muestra draft) |
| Scheduler Agent | MEDIO | `requires_confirmation` solo deadline < 24h |
| Support Agents | MEDIO | `@approval(type="audit")` (registra, no bloquea) |
| Social Media | MEDIO | Draft en Directus, aprobacion humana separada |
| Automation Agent | MEDIO | `requires_confirmation` para flows destructivos |
| Content Agents | BAJO | Sin HITL (revision humana post-generacion) |
| Research Agents | BAJO | Sin HITL (solo reportes informativos) |

Timeout: Email 30min → guardar draft. Invoice 1h → task urgente. Escalation 2h → re-escalar.

Audit trail: toda accion HITL se registra en Directus `agent_audit_log`.

### Publicacion Social

AgNO genera → Directus (draft) → revision humana → Directus Flow → Postiz (30+ plataformas).

Postiz self-hosted en Docker. CLI disponible para automatizacion directa. Analytics de vuelta a Directus.

### Research sin Tokens

Investigaciones recurrentes: Crawl4AI (Adaptive Crawling, 0 tokens) via Prefect → Directus → LLM solo para sintesis final (~3K tokens).

Investigaciones ad-hoc: Deep Research Workflow con agentes (~15-50K tokens).

### CRM

Directus con layouts Kanban nativos. Deals pipeline para ventas. Support tickets por producto. Lead scoring automatico con deal creation. Follow-up automatizado via Directus Flows.

---

## Stack Tecnico

| Componente | Tecnologia | Rol |
|-----------|-----------|-----|
| Agentes | AgNO (Python) | 8 agentes core, 4 conversacionales + 4 invocados por Prefect |
| Orquestacion | Prefect | Backbone de todos los flujos de marketing, schedules, retry, monitoring |
| Data Layer | Directus + PostgreSQL | CRM, CMS, REST/GraphQL, Kanban, Flows |
| Knowledge | LanceDB + Voyage AI | Vector search, RAG, embeddings |
| Social Media | Postiz (self-hosted) | 30+ plataformas, OAuth, analytics |
| Scraping | Crawl4AI | Web crawling, CSS/XPath extraction |
| Storage | RustFS | S3-compatible object storage |
| Cache | Redis | Directus cache |
| Frontend | Next.js + CopilotKit | Dashboard NEXUS (AG-UI) |
| Monitoring | Uptime Kuma | Health checks |
| Proxy | Traefik | Reverse proxy + SSL |
| Modelos | MiniMax (tools), Groq (fast), OpenRouter (reasoning), Voyage AI (embeddings) |

---

## Prioridad de Activacion

El orden esta disenado para que cada fase alimente la siguiente.
No puedes tener Growth Strategist sin analytics. No puedes experimentar
sin contenido publicado. No puedes aprender sin experimentos medidos.

### Fase 1 — Contenido + Learnings Base (semanas 1-2)
1. Content Production Workflow (trend → script → review)
2. SEO Content Workflow (keyword → article → audit loop)
3. Copywriter ES
4. **Marketing Learnings** — coleccion en Directus + skill para agentes (cap. 35)

> Desde el dia 1, todo contenido generado alimenta la memoria del sistema.

### Fase 2 — Social Media + Publicacion (semanas 3-4)
5. Social Media Workflow (IG + X + LinkedIn + audit)
6. Social Media Planner (calendarios)
7. Postiz setup + integracion con Directus
8. **Experimentacion basica** — 3 variantes de hook por post, tagging en Directus (cap. 34)

> Con Postiz publicando y variantes tageadas, empiezas a acumular datos de A/B.

### Fase 3 — Analytics + Decision Engine (semanas 5-6)
9. Analytics Agent + reportes semanales
10. Dash (business analytics)
11. Sentiment analysis
12. **Growth Strategist Agent** — plan semanal automatico cada lunes (cap. 33)

> El Growth Strategist necesita 2-4 semanas de datos de las fases 1-2.
> Primeras semanas produce planes conservadores. Mejora con cada ciclo.

### Fase 4 — CRM y Ventas (semanas 7-8)
13. Pipeline de ventas Kanban en Directus
14. Soporte Kanban por producto
15. Lead scoring mejorado
16. WhatsApp Support Team

> El CRM alimenta al Growth Strategist con datos de conversion y pipeline.

### Fase 5 — Investigacion (semanas 9-10)
17. Deep Research Workflow
18. Crawler-first research (Prefect + Crawl4AI)
19. Competitor Intelligence Workflow
20. Marketing LATAM Team (coordinacion)

> Research alimenta al Growth Strategist con inteligencia competitiva.

### Fase 6 — Automatizacion (semanas 11-12)
21. Video programatico (templates + rendering)
22. Email Agent con HITL
23. Invoice Agent con HITL
24. Scheduler Agent
25. Onboarding Agent

### Fase 7 — Optimizacion Avanzada (mes 4+)
26. **Experimentacion completa** — A/B automatizado con declaracion de ganador y escalado (cap. 34)
27. Content recycling — Prefect flow que re-publica top performers con variaciones
28. AI Perception Monitoring — como AI engines hablan de tus marcas
29. Revenue optimization — cuando haya 3+ meses de datos de deals en CRM
30. Campaign orchestration — campanas full-funnel (contenido + email sequences)

### El loop L4 completo (activo desde fase 3)

```
Semana N:
  Lunes    → Growth Strategist produce plan (lee learnings + analytics)
  Mar-Jue  → Content Team ejecuta plan (genera variantes, experimenta)
  Viernes  → Analytics Agent mide resultados (declara ganadores)
             Escribe nuevos learnings en Directus
  
Semana N+1:
  Lunes    → Growth Strategist lee nuevos learnings
             Ajusta plan (mas de lo que funciono, menos de lo que no)
             Detecta patrones cross-brand
  → Repeat
```

Cada semana el sistema es mejor que la anterior.

---

## Resumen Ejecutivo

### Que tenemos (9 bloques, 35 capacidades + 6 sub-capacidades CRM)

| Bloque | Caps | Que resuelve |
|--------|------|-------------|
| 1. Contenido | 1-4 | Generar contenido multi-formato (video, imagen, copy, scripts) |
| 2. SEO/GEO | 5-7 | Posicionar en Google Y en AI engines (ChatGPT, Perplexity) |
| 3. Social Media | 8-11 | Publicar en 30+ plataformas con auditoria y calendario |
| 4. Investigacion | 12-16 | Research profundo, competitor intel, market intelligence |
| 5. Analytics | 17-20 | Medir todo: contenido, negocio, leads, sentimiento |
| 6. CRM/Ventas | 21-27c | Pipeline ventas, soporte Kanban, WhatsApp, billing, customer 360 |
| 7. Knowledge | 28-30 | Crawling, RAG, data operations |
| 8. Product Dev | 31-32 | Analisis de features, code review |
| 9. L4 Strategy | 33-35 | Decision engine, experimentacion, memoria estructurada |

### Que falta (futuro, no bloqueante)

| Gap | Cuando | Dependencia |
|-----|--------|-------------|
| Revenue optimization (funnel analysis, pricing) | Fase 7+ | 3+ meses de datos de deals |
| Campaign orchestrator (full-funnel) | Fase 7+ | Landing pages + email sequences |
| Customer health / churn detection | Fase 7+ | Datos de uso reales de productos |
| PWA de notificaciones en tiempo real | Fase 7+ | Control center definido |
| Soporte via web form y social | Futuro | Postiz monitoring + Directus webhooks |

### Correccion critica pendiente (codigo)

Los tools de Directus (`log_support_ticket`, `log_conversation`, `confirm_payment`)
no vinculan registros a `contact_id`. Esto debe corregirse antes de activar el CRM
(Fase 4). Sin esta correccion, no hay Customer 360 View y cada interaccion es un
registro huerfano.
