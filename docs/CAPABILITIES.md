# QYNE v1 — Catalogo Completo de Capacidades para Uso Interno

## Contexto del Sistema

**Infraestructura:** 2 servidores Hetzner Cloud (platform-infra CX23/CX33/CX33 en hel1 + mastra-infra CX43 en hel1). El servidor mastra-infra es un VPS limpio con Docker, donde corre QYNE.

**Stack de aplicacion (12 servicios):**

| Servicio | Base de datos | Funcion |
|----------|--------------|---------|
| PostgreSQL 16 | -- | 2 DBs aisladas: directus_db, prefect_db |
| Redis 7 | -- | Cache de Directus |
| RustFS | Archivos en disco | Object storage S3-compatible |
| Reranker (Infinity) | Modelo en memoria | BAAI/bge-reranker-base |
| Directus | PostgreSQL (directus_db) | CMS + REST/GraphQL + MCP Server |
| AgNO | SQLite + LanceDB | AgentOS: 42 agentes, 7 teams, 7 workflows, 24 skills |
| Frontend | -- | Next.js + CopilotKit (AG-UI), 18 paginas |
| n8n | SQLite | Automatizaciones deterministicas |
| Prefect Server | PostgreSQL (prefect_db) | Orquestacion de workflows |
| Prefect Worker | -- | Ejecuta flows (scraping, ETL, backups) |
| Uptime Kuma | SQLite | Monitoreo de salud |
| Traefik | -- | Reverse proxy + SSL |

**Principio de operacion:** Todo se controla desde el dashboard NEXUS (chat). Prefect, n8n y Directus son dashboards de debugging, no de operacion diaria.

---

## PARTE 1: GENERACION DE CONTENIDO

### 1.1 Content Production Pipeline

**Que es:** Workflow completo que va de tendencia a video listo para publicar.

**Flujo:** Trend Scout (investigacion) → Compact Brief → Scriptwriter (3 variantes de storyboard) → Creative Director (evaluacion visual) → Tu seleccionas la mejor.

**Agentes involucrados:**
- **Trend Scout** — Busca tendencias AI/tech de las ultimas 48h. Max 3 tool calls. Produce content brief con hooks en espanol, relevance score, fuentes.
- **Scriptwriter** — Genera 3 variantes de storyboard (emocional, data-driven, provocativo). 5-6 escenas por variante. Guarda como JSON.
- **Creative Director** — Evalua las 3 variantes visualmente. Mood, flujo escena por escena, momento mas fuerte, debilidad. Recomienda la mejor.
- **Analytics Agent** — Analiza performance post-publicacion. Reportes semanales con top/bottom posts, analisis por pilar, recomendaciones data-driven.

**Lo que puedes hacer hoy (una vez portados):**
- Pedir "Crea un video sobre [tema]" y recibir 3 guiones listos con evaluacion creativa
- Generar contenido para Reels/TikTok con hooks optimizados en espanol
- Obtener reportes semanales de performance con recomendaciones automaticas
- Rotar contenido entre pilares definidos (AI Trends, AI Tools, AI Business, etc.)

**Lo que falta portar:** Los 4 agentes estan definidos en `agents/content/agents.py` y el workflow en `workflows/content_production.py`. Necesitan ser activados en el AgentOS.

---

### 1.2 Video Programatico con Remotion

**Que es:** Generacion de videos a escala usando templates React. No necesitas editor de video ni imagenes AI.

**Templates disponibles:**

| Template | Input | Resultado |
|----------|-------|-----------|
| PromoProduct | brand, hook, features[], stat, cta | Video promocional de producto |
| DataStory | hook, data_points[], insight, cta | Video con datos/estadisticas |
| Explainer | hook, steps[], conclusion, cta | Video explicativo paso a paso |
| TikTok Captions | video_url, language | Subtitulos automaticos |

**Lo que puedes hacer:**
- Generar 100+ videos personalizados por marca sin editor humano
- Cada marca (Whabi, Docflow, Aurora) tiene colores automaticos
- El Scriptwriter genera el JSON, Remotion lo renderiza
- Videos para Instagram Reels (9:16, 30-45s) y TikTok (9:16, 21-34s)

**Flujo completo:** Chat → Content Team genera brief + script JSON → Remotion renderiza video → Listo para publicar.

---

### 1.3 Generacion de Imagenes y Media

**Que es:** Creative Studio con 3 agentes especializados.

**Agentes:**
- **Image Generator** — Genera imagenes AI desde prompts de texto. Ratio 1:1 para social media. Usa NanoBanana (requiere GOOGLE_API_KEY).
- **Video Generator** — Genera videos cortos desde imagenes y prompts. Transiciones suaves, estilo consistente.
- **Media Describer** — Describe imagenes/videos para accesibilidad y catalogacion. Sujeto, setting, colores, mood, composicion.

**Lo que puedes hacer:**
- Generar thumbnails y covers para posts
- Crear variantes visuales para A/B testing
- Catalogar automaticamente todo el media generado
- El team funciona en modo route: la solicitud va al especialista correcto

---

## PARTE 2: SEO, GEO Y POSICIONAMIENTO EN AI

### 2.1 SEO Content Workflow

**Que es:** Pipeline completo de articulos optimizados para Google Y para motores AI (ChatGPT, Perplexity, Gemini).

**Flujo:** Keyword Researcher → Article Writer → SEO Auditor → Loop (max 2 rondas hasta PUBLISH).

**Agentes:**
- **Keyword Researcher** — Encuentra topics con alto potencial GEO. Busca gaps donde no existe buen listicle en espanol. Output: topic, target query, keywords, competencia, angulo unico para nuestros productos.
- **Article Writer** — Escribe articulos de 1500-2500 palabras en espanol. Estructura obligatoria: Quick Answer (primeros 200 words) → Intro con stats → Entries detallados → Tabla comparativa → How to Choose → FAQ. Guarda como MDX con frontmatter.
- **SEO Auditor** — Audita cada articulo con checklist de GEO (Quick Answer, listicle format, evidence density, FAQ, freshness) y SEO (titulo <60 chars, meta description, H2/H3, tabla, >1500 words). Score X/100. Veredicto: PUBLISH / REVISE / REWRITE.

**Lo que puedes hacer:**
- Generar articulos que AI engines citan (74.2% de citaciones AI vienen de listicles)
- Posicionar Whabi, Docflow y Aurora como #1 en sus nichos con comparaciones honestas
- Ciclo automatico de revision hasta que el articulo pase el quality gate
- Distribucion post-publicacion: Reddit (46.7% de citaciones Perplexity), LinkedIn, Quora

### 2.2 Answer Engine Optimization (AEO/GEO)

**Que es:** Optimizacion para que los motores AI (ChatGPT, Perplexity, Gemini, AI Overviews) citen tu contenido.

**Skill seo-geo ya incluye:**
- Quick Answer blocks en los primeros 200 words (lo que AI extrae)
- Formato listicle numerado (el formato que AI prefiere)
- FAQ Section que matchea queries exactas de usuarios en ChatGPT/Perplexity
- Schema Markup triple: Article + ItemList + FAQPage JSON-LD
- Freshness protocol: actualizar cada 7-14 dias, fechas visibles
- Palabras prohibidas (marketing fluff que AI filtra) y palabras obligatorias (datos especificos que AI confia)

**Lo que puedes hacer:**
- Cada articulo generado ya viene optimizado para citacion AI
- Posicionar tus productos en las respuestas de ChatGPT cuando alguien pregunte "mejor CRM para WhatsApp" o "mejor EHR para clinicas"
- Monitorear si AI engines te citan (requiere agregar herramienta de monitoreo tipo LLMrefs)

---

## PARTE 3: SOCIAL MEDIA

### 3.1 Social Media Workflow

**Que es:** Pipeline de creacion de posts por plataforma con auditoria de calidad.

**Flujo:** Instagram Post Agent → Twitter/X Post Agent → LinkedIn Post Agent → Social Auditor.

**Agentes:**
- **Instagram Post Agent** — Reels/Stories en espanol. Visual hooks, trending audio, carousels, hashtags (10-15).
- **Twitter/X Post Agent** — Threads (5-7 tweets) en espanol. Hooks data-driven, preguntas de engagement. Max 280 chars/tweet.
- **LinkedIn Post Agent** — Posts profesionales en espanol. Insights, case studies, analisis de industria. Line breaks para legibilidad.
- **Social Auditor** — Audita cada post: platform fit, engagement potential, hashtag quality, CTA clarity, timing. Score 1-10 con mejoras especificas.

**Lo que puedes hacer:**
- Generar contenido adaptado a cada plataforma desde un solo brief
- Auditoria automatica antes de publicar
- Calendario de contenido: 3 posts/dia, rotacion de pilares, lunes-viernes educativo, sabado BTS, domingo recap

### 3.2 Marketing LATAM Team

**Que es:** Team coordinado de 3 agentes para marketing en espanol latinoamericano.

**Agentes:**
- **Copywriter ES** — Copy persuasivo en espanol LATAM neutral. Landing pages, email sequences, ad copy, social posts. Tu/usted segun contexto.
- **SEO Strategist** — Estrategias SEO + GEO para contenido en espanol. Keyword gaps, AI citation potential, competitor analysis. Optimiza para Google Y para AI engines.
- **Social Media Planner** — Calendarios de contenido semanales. Post type, topic, hook, CTA, hashtags por plataforma. Optimiza para algoritmo de cada plataforma.

**Lo que puedes hacer:**
- Campanas completas en espanol: desde copy hasta calendario de publicacion
- Estrategia SEO/GEO unificada para las 3 marcas
- El team se coordina internamente: el planner define la estrategia, el copywriter ejecuta, el SEO valida

---

## PARTE 4: INVESTIGACION Y INTELIGENCIA

### 4.1 Deep Research Workflow

**Que es:** Sistema de investigacion multi-proveedor con scouts paralelos.

**Flujo:** Research Planner → N scouts en paralelo → Quality Gate (min 200 chars) → Research Synthesizer → Reporte markdown.

**Scouts disponibles (condicional por API key):**
- **Tavily Scout** — Busqueda AI-optimizada. Mejor para noticias, articulos, anuncios recientes.
- **Exa Scout** — Busqueda semantica/neural. Mejor para papers, docs tecnicos, contenido nicho.
- **Firecrawl Scout** — Extraccion profunda de paginas. Mejor para documentacion, READMEs, articulos detallados.
- **WebSearch Scout** — DuckDuckGo como fallback gratuito. Siempre disponible.

**Lo que puedes hacer:**
- Investigar cualquier tema con multiples fuentes en paralelo
- El planner asigna angulos diferentes a cada scout (sin overlap)
- Quality gate automatico: si la investigacion es muy delgada, se detiene
- Reporte final con Executive Summary, Key Findings, Analysis, Gaps, Recommendations, Sources
- Reportes en espanol para temas LATAM, ingles para el resto

### 4.2 Client Research Workflow

**Que es:** Investigacion rapida combinando web + knowledge base interna.

**Flujo:** Parallel(Web Research + Knowledge Lookup) → Synthesis Agent → ResearchReport (Pydantic structured output).

**Lo que puedes hacer:**
- Investigar un cliente o prospecto combinando datos publicos con tu knowledge base
- Output estructurado (no texto libre) para integracion con CRM

### 4.3 Competitor Intelligence Workflow

**Que es:** Analisis competitivo paralelo con sintesis accionable.

**Flujo:** Parallel(Content Scout + Pricing Scout + Reviews Scout) → Competitor Synthesizer.

**Agentes:**
- **Content Scout** — Analiza estrategia de contenido del competidor: topics, frecuencia, engagement, gaps.
- **Pricing Scout** — Investiga pricing pages: planes, precios, features por tier, free trial.
- **Reviews Scout** — Recopila reviews de G2, Capterra, ProductHunt, Reddit. Praise comun, quejas comunes, NPS, feature requests.
- **Synthesizer** — Sintetiza todo en: landscape overview, tabla de pricing, gaps de contenido (oportunidades), sentiment analysis, 3-5 acciones recomendadas.

**Lo que puedes hacer:**
- "Analiza la competencia de Whabi" → reporte completo con pricing, contenido, reviews y acciones
- Identificar gaps donde tus competidores no tienen contenido (oportunidades SEO/GEO)
- Monitorear cambios de pricing de competidores
- Frameworks incluidos: Quick Assessment, SWOT, Feature Matrix

### 4.4 Market Intelligence

**Skill que ensena a los agentes:**
- Jerarquia de fuentes de datos (SEC filings > Statista/Gartner > Crunchbase > News > Blogs > Social)
- Query patterns para market size, competitor analysis, pricing intelligence, datos LATAM
- Extraccion estandarizada: metrica, valor, fuente, fecha, scope
- Output estructurado: MARKET_DATA, COMPETITIVE_LANDSCAPE, TRENDS, GAPS, CONFIDENCE

---

## PARTE 5: SOPORTE Y CRM

### 5.1 WhatsApp Support Team

**Que es:** Router que dirige mensajes de WhatsApp al agente de soporte correcto por producto.

**Agentes:**
- **Whabi Support** — Especialista en WhatsApp CRM. Conoce planes ($49/$149/custom), features, issues comunes (template approval, webhook config, contact import).
- **Docflow Support** — Especialista en EHR. Conoce planes ($99/$249/custom), features, issues comunes (document upload, permissions, retention).
- **Aurora Support** — Especialista en Voice PWA. Conoce planes ($0/$29/$79), features, issues comunes (mic permissions, PWA install, voice recognition).
- **General Support** — Fallback para consultas generales, partnerships, careers.

**Capacidades compartidas de todos los agentes de soporte:**
- `save_contact()` — Guarda contacto en Directus CRM automaticamente cuando el cliente se identifica
- `save_company()` — Guarda empresa cuando el cliente la menciona
- `confirm_payment()` — Confirma pagos con aprobacion humana obligatoria (@approval)
- `log_support_ticket()` — Registra cada interaccion para analytics
- `escalate_to_human()` — Escala a humano para quejas serias, disputas de pago, temas legales
- `log_conversation()` — Registra resumen al final de cada conversacion (intent, sentiment, lead_score, next_action)

**Lo que puedes hacer:**
- Soporte 24/7 automatizado para las 3 marcas via WhatsApp
- Cada interaccion queda registrada en Directus con sentiment analysis
- Escalacion automatica para casos criticos
- Lead scoring automatico basado en la conversacion
- Follow-up tasks creadas automaticamente para interacciones de alto valor

### 5.2 CRM Tools (Directus Business Logic)

**Tools custom que van mas alla del CRUD basico:**
- `confirm_payment` — Workflow de aprobacion: requiere confirmacion humana, registra en payments, crea task de seguimiento
- `log_support_ticket` — Registra ticket con product, intent, summary, resolution, urgency. Si urgency=high o lead_score>=7, crea task de follow-up
- `escalate_to_human` — Crea task urgente + evento de escalacion en Directus
- `save_contact` — Guarda contacto con source=whatsapp, status=lead. Si hay notas, crea evento
- `save_company` — Guarda empresa con domain, employees, industry
- `log_conversation` — Registra conversacion completa con channel, intent, sentiment, lead_score. Si hay next_action, crea task

---

## PARTE 6: AUTOMATIZACION Y ORQUESTACION

### 6.1 Automation Agent

**Que es:** Agente unico que controla n8n, Directus y Prefect. Un solo orquestador, no multiples agentes de automatizacion.

**Herramientas:**
- **Prefect API:** list_prefect_deployments, trigger_prefect_flow, trigger_website_crawler, check_prefect_flow_status, list_recent_flow_runs
- **n8n MCP:** list/get/create/update/activate/deactivate/execute workflows, list/get executions
- **Directus MCP:** read-items, create-item, update-item, read-collections, read-fields, read-flows, trigger-flow
- **Directus REST:** save_contact, save_company, log_conversation, log_support_ticket

**Lo que puedes hacer:**
- "Scrapea docs.agno.com" → lista deployments → encuentra website-crawler → trigger con parametros → reporta
- "Procesa documentos pendientes" → encuentra etl-documents → trigger
- Crear workflows en n8n desde el chat
- Leer y escribir en cualquier coleccion de Directus
- Validacion de parametros contra schemas conocidos (previene errores del LLM)

### 6.2 Prefect Flows (21 flows definidos)

**Pipelines multi-etapa:**

| Pipeline | Etapas | Trigger |
|----------|--------|---------|
| Property Pipeline | Fetch+Extract → Normalize → Validate → Dedup → Enrich → Store → Download Images → Update | Chat o schedule cada 6h |
| Website Crawler | Discover (BFS) → Fetch (Crawl4AI) → Chunk → Classify → Dedup → Store → Index (LanceDB) | Chat o on-demand |

**Flows individuales:**

| Categoria | Flows |
|-----------|-------|
| Data Operations | data_sync, data_cleanup, dedup_merger, data_enricher, export_csv, import_csv |
| Document Processing | etl_documents (Docling parse), knowledge_indexer (Voyage AI embeddings) |
| Monitoring | health_check (cada 5min), report_generator (lunes 8am), email_digest (diario 8am), lead_scorer (diario 6am), sentiment_analyzer (diario) |
| Infrastructure | database_backup (diario 3am), scraper_latam (legacy, cada 6h) |
| Quality | property_quality_audit, selector_health_check |

**Lo que puedes hacer:**
- Scraping automatizado de sitios web con CSS schemas (0 tokens, gratis)
- Crawling profundo de documentacion con indexacion en LanceDB para RAG
- Backups automaticos de PostgreSQL a RustFS
- Health checks cada 5 minutos con alertas
- Reportes semanales automaticos
- Lead scoring diario basado en actividad y recencia
- Sentiment analysis de conversaciones (keyword-based, sin LLM)
- Export/Import CSV para integracion con herramientas externas

---

## PARTE 7: AGENTES UTILITARIOS

### 7.1 Dash — Data Analytics Agent

**Que es:** Agente de analytics que responde preguntas de negocio sobre las 3 marcas.

**Capacidades:**
- Consulta datos de Directus CRM (contacts, companies, tasks, tickets)
- Calcula metricas, porcentajes, tasas de crecimiento
- Ejecuta Python para transformaciones complejas
- Contexto por producto: Whabi (leads, conversion, response time), Docflow (documents, compliance), Aurora (active users, voice commands, retention)

**Output:** El numero especifico + la tendencia + que significa + accion recomendada.

### 7.2 Pal — Personal Agent

**Que es:** Agente personal que aprende todo sobre ti y organiza tu informacion.

**Sistema de almacenamiento:** JSON files (notes, bookmarks, people, projects, decisions).

**Capacidades:**
- Recuerda preferencias, decisiones, contactos, proyectos
- Busca en web cuando necesitas informacion externa
- Conecta informacion entre archivos con tags
- Memoria agentiva habilitada (aprende automaticamente)
- 10 runs de historial para contexto profundo

### 7.3 Onboarding Agent

**Que es:** Guia paso a paso para nuevos clientes de cualquier producto.

**Capacidades:**
- Identifica el producto (Whabi/Docflow/Aurora)
- Guia UN paso a la vez (no dump de informacion)
- Busca en knowledge base para respuestas especificas
- Asume cero conocimiento tecnico del cliente

### 7.4 Email Agent

**Que es:** Redacta y envia emails profesionales.

**Capacidades:**
- Drafts en espanol LATAM neutral
- Siempre muestra el draft antes de enviar
- Nunca envia sin confirmacion explicita
- Si EmailTools no esta configurado, genera el texto como draft

### 7.5 Scheduler Agent

**Que es:** Crea recordatorios, tareas y eventos en el CRM.

**Capacidades:**
- "Recuerdame llamar a Juan el viernes" → task en Directus
- "Que tengo pendiente esta semana?" → lista tasks
- Timezone America/Bogota por defecto
- Si no se especifica hora, default 9:00 AM

### 7.6 Invoice Agent

**Que es:** Genera cotizaciones, facturas y trackea pagos.

**Capacidades:**
- Conoce pricing de las 3 marcas (Whabi $49/$149/custom, Docflow $99/$249/custom, Aurora $0/$29/$79)
- Usa confirm_payment con @approval obligatorio
- Registra cada interaccion de billing como ticket
- Precios en USD por defecto

### 7.7 Code Review Agent

**Que es:** Revisa codigo con razonamiento multi-paso.

**Capacidades:**
- Lee codigo, razona sobre problemas potenciales (2-5 pasos de razonamiento)
- Review estructurado: SEVERITY, ISSUE (file:line), FIX, WHY
- Chequea: SQL injection, XSS, hardcoded secrets, race conditions, error handling
- Opera en workspace sandboxed

---

## PARTE 8: PRODUCT DEVELOPMENT

### 8.1 Product Dev Team

**Que es:** Team coordinado para analisis de features y documentacion.

**Agentes:**
- **Product Manager** — Analiza feature requests con RICE scoring (Reach, Impact, Confidence, Effort). Prioriza roadmap, escribe specs.
- **UX Researcher** — Valida decisiones desde perspectiva del usuario. Pain points, accesibilidad, learning curve, edge cases.
- **Technical Writer** — Documentacion clara y estructurada. Overview → Prerequisites → Step-by-step → Troubleshooting. En espanol.

**Lo que puedes hacer:**
- "Analiza si deberiamos agregar [feature] a Whabi" → PM analiza, UX valida, Tech Writer documenta
- Priorizar backlog con scoring objetivo
- Documentar features nuevas automaticamente

---

## PARTE 9: KNOWLEDGE Y RAG

### 9.1 Knowledge Base (LanceDB)

**Que es:** Vector store local con embeddings de Voyage AI para busqueda semantica.

**Capacidades actuales:**
- Hybrid search (vector + keyword)
- Indexacion automatica de PDFs, TXT, MD, CSV, JSON desde la carpeta knowledge/
- Knowledge Agent dedicado para consultas
- 6 knowledge bases cargadas

**Flujo de indexacion:**
1. Documento llega (upload o crawl)
2. Docling parsea (PDF/DOCX → texto)
3. Texto se guarda en Directus `documents`
4. Voyage AI genera embeddings
5. Chunks se indexan en LanceDB
6. Agentes pueden buscar semanticamente

### 9.2 Website Crawler → Knowledge

**Que es:** Crawl profundo de sitios web con clasificacion por topic e indexacion para RAG.

**Etapas:** Discover (BFS) → Fetch (Crawl4AI con JS rendering) → Chunk (por headers, max 500 tokens) → Classify (27 keywords) → Dedup → Store (Directus) → Index (LanceDB).

**Lo que puedes hacer:**
- "Crawlea la documentacion de [producto]" → toda la doc queda indexada y buscable por agentes
- Filtrar por paths (include/exclude)
- Clasificacion automatica por topic
- Los agentes pueden responder preguntas sobre el contenido crawleado

---

## PARTE 10: CAPACIDADES TRANSVERSALES

### 10.1 Composicion de Agentes

El sistema soporta 6 patrones de composicion:

| Patron | Estado | Ejemplo |
|--------|--------|---------|
| Agent tiene Tools | Funcionando | Support Agent + Directus REST tools |
| Agent como Step de Workflow | Funcionando | Trend Scout como paso de Content Production |
| Workflow como Tool (WorkflowTools) | Definido, no implementado | Research Agent puede trigger deep_research_workflow |
| Agent como Tool | Definido, no implementado | Dash usa Knowledge Agent como tool |
| Workflow anidado | Definido, no implementado | Content Production incluye Deep Research como sub-workflow |
| Team como Step | Parcial (Parallel) | Client Research usa Parallel(web, knowledge) |

**Lo que puedes hacer cuando se implemente:**
- Un comando "Investiga a fondo y crea contenido sobre X" ejecuta: deep research → content production → SEO audit, todo encadenado
- Dash consulta la knowledge base antes de responder preguntas de datos
- Invoice Agent usa Scheduler Agent para crear recordatorios de pago

### 10.2 Guardrails y Seguridad

- **PII Detection** — Detecta informacion personal sensible antes de procesarla
- **Prompt Injection** — Detecta intentos de manipulacion del prompt
- **Approval Workflows** — Pagos requieren aprobacion humana (@approval)
- **Human-in-the-loop** — Escalacion a humano para casos criticos

### 10.3 Learning y Memoria

| Feature | Estado |
|---------|--------|
| User Memory (automatica) | Funcionando |
| User Memory (agentiva) | Funcionando |
| Entity Memory | Funcionando |
| Session Context | Funcionando |
| User Profile | Funcionando |
| Learned Knowledge | Funcionando |
| Decision Log | Funcionando |
| Compression Manager | Funcionando |
| Chat History | Funcionando |

**Lo que significa:** Los agentes aprenden de cada interaccion. Recuerdan preferencias, decisiones pasadas, y contexto de conversaciones anteriores. Esto mejora con el uso.

### 10.4 Modelos AI

| Rol | Modelo | Uso |
|-----|--------|-----|
| TOOL_MODEL | MiniMax | Agentes con herramientas (la mayoria) |
| FAST_MODEL | Groq | Generacion rapida (scripts, articles) |
| REASONING_MODEL | OpenRouter | Razonamiento profundo (synthesis, research) |
| Embeddings | Voyage AI | Vectores para knowledge base |

### 10.5 Interfaces

| Interface | Estado | Uso |
|-----------|--------|-----|
| AG-UI (CopilotKit) | Funcionando | Dashboard web principal |
| WhatsApp | Config only, no testeado | Soporte al cliente |
| Slack | No usado | Potencial para notificaciones internas |
| Telegram | No usado | Potencial para canal alternativo |
| A2A Protocol | No usado | Comunicacion agent-to-agent entre sistemas |
| MCP Server mode | No usado | Exponer agentes como herramientas para otros sistemas |

---

## PARTE 11: DATA SCRAPING Y ETL

### 11.1 Property Pipeline (Multi-Site)

**Que es:** Scraping de sitios inmobiliarios con CSS schemas (0 tokens LLM).

**Sitios configurados:**
- rentahouse_ve (CSS + detail, produccion)
- century21_ve (Links + detail, produccion)
- mercadolibre_ve (CSS only, configurado)

**Capacidades:**
- 2 modos de listing: CSS (HTML consistente) y Links (SPAs, WordPress)
- Normalizacion de precios, monedas, ubicaciones, telefonos (formato internacional)
- Deduplicacion por URL
- Enriquecimiento: price_per_m2, price_category, property_type
- Descarga de imagenes a RustFS (URLs permanentes, no hotlinking)
- Deployments separados por sitio con schedules independientes
- Concurrency limit=1 para evitar rate limiting

**Agregar un sitio nuevo:** Analizar HTML → Elegir modo (CSS/Links) → Agregar config a SITE_CONFIGS → Agregar detail parser si necesario → Test → Register deployment.

### 11.2 Scraping Generico

**scraper_latam** — Scraper generico con BeautifulSoup. Legacy, reemplazado por property_pipeline para inmuebles.

**Website Crawler** — Crawl profundo con BFS, Crawl4AI para JS rendering, chunking por headers, clasificacion por topic, indexacion en LanceDB.

### 11.3 Data Operations

| Flow | Que hace |
|------|---------|
| data_sync | Sincroniza datos entre colecciones de Directus con field mapping |
| data_cleanup | Encuentra duplicados y datos viejos (solo reporta, no borra) |
| dedup_merger | Merge inteligente de contactos duplicados por email |
| data_enricher | Agrega campos computados: clasificacion de dominio email, boost de lead score |
| export_csv | Exporta cualquier coleccion a CSV en RustFS |
| import_csv | Importa CSV desde RustFS a cualquier coleccion |

---

## PARTE 12: MONITOREO Y REPORTES

### 12.1 Health Monitoring

- **health_check** (cada 5 min) — Verifica todos los servicios via HTTP. Crea alert task si algo esta caido.
- **Uptime Kuma** — Dashboard visual de salud (requiere configurar monitors).

### 12.2 Reportes Automaticos

| Reporte | Schedule | Contenido |
|---------|----------|-----------|
| Weekly Report | Lunes 8am | Metricas agregadas: contacts, tickets, conversations |
| Daily Digest | Diario 8am | Resumen de actividad de las ultimas 24h |
| Lead Scorer | Diario 6am | Recalcula scores de contactos por actividad y recencia |
| Sentiment Analyzer | Diario | Scoring de sentimiento de conversaciones (keyword-based) |

### 12.3 Backups

- **database_backup** (diario 3am) — pg_dump de directus_db + prefect_db → gzip → RustFS.

---

## PARTE 13: CAPACIDADES POR DESARROLLAR (EXTENSIONES NATURALES)

Estas son capacidades que tu stack puede soportar con trabajo adicional, ordenadas por impacto:

### 13.1 AI Perception Monitoring
Rastrear como ChatGPT, Gemini, Perplexity hablan de tus marcas. Implementable con Prefect flow que hace queries sistematicas a APIs de AI y compara respuestas en el tiempo. Almacena en Directus para tracking historico.

### 13.2 Automated Review Response
Scraping de reviews en Google/Yelp/G2 + generacion de respuestas on-brand con agentes. El Social Auditor ya tiene la logica de evaluacion; falta el scraping de reviews y la publicacion de respuestas.

### 13.3 Email Marketing Sequences
El Email Agent ya existe. Falta conectar con n8n para secuencias automaticas: trigger por evento en Directus (nuevo lead) → secuencia de 3-5 emails → tracking de apertura.

### 13.4 Landing Page Generation
Agentes que generan landing pages optimizadas por campana. El Copywriter ES + SEO Strategist ya tienen la logica. Falta un template system (similar a Remotion pero para HTML).

### 13.5 Ad Creative Generation
Variantes de ads para Meta/Google desde un brief. El Creative Studio + Copywriter ES pueden generar copy + visual. Falta integracion con APIs de Meta/Google Ads.

### 13.6 Content Performance Prediction
Antes de publicar, predecir engagement basado en historico. El Analytics Agent + datos de Directus pueden alimentar un modelo simple. Falta acumular datos historicos suficientes.

### 13.7 Multi-Language Content
Generar contenido en espanol + ingles + portugues desde el mismo brief. Los agentes ya trabajan en espanol. Agregar instrucciones para ingles/portugues es directo.

### 13.8 Automated Social Posting
Conectar el Social Media Workflow con APIs de Instagram/Twitter/LinkedIn para publicar directamente. Actualmente genera el contenido pero no publica. n8n puede manejar la publicacion.

### 13.9 Client Portal
Exponer un subset del dashboard NEXUS para que clientes vean reportes, metricas y contenido generado. El frontend Next.js ya tiene 18 paginas; agregar vistas read-only por cliente.

### 13.10 Webhook-Driven Content
n8n triggers que detectan eventos (nuevo competidor, cambio de precio, mencion en redes) y automaticamente generan contenido de respuesta. La infraestructura existe; falta configurar los workflows.

---

## RESUMEN: INVENTARIO COMPLETO

| Categoria | Componentes | Estado |
|-----------|------------|--------|
| **Agentes** | 42 definidos (3 portados, 39 pendientes) | 7% operativo |
| **Teams** | 7 definidos (0 portados) | 0% operativo |
| **Workflows** | 7 definidos (0 portados) | 0% operativo |
| **Skills** | 24 cargados | Funcionando |
| **Prefect Flows** | 21 definidos | Infra lista, 0 deployments |
| **Tools custom** | 5 archivos (directus, prefect, chat_export, sandbox) | Definidos |
| **Remotion Templates** | 4 templates | Skill definida |
| **Knowledge bases** | 6 cargadas | Funcionando |
| **Pydantic Models** | 8 definidos (0 portados) | 0% operativo |
| **Frontend** | 18 paginas | Funcionando |
| **Servicios Docker** | 12 | Infra lista |

**Prioridad de activacion para marketing interno:**
1. Content Production Workflow (trend → script → review)
2. SEO Content Workflow (keyword → article → audit loop)
3. Social Media Workflow (IG + Twitter + LinkedIn + audit)
4. Marketing LATAM Team (copywriter + SEO + social planner)
5. Competitor Intel Workflow (content + pricing + reviews → synthesis)
6. Remotion video rendering
7. Prefect deployments para schedules automaticos
