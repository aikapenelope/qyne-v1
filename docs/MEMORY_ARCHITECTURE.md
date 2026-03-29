# QYNE v1 — Agno Memory Architecture: What Goes Where

## The 7 Layers of Agent Context

Agno has 7 distinct places where information lives. Each has different
token costs, persistence, and use cases. Using the wrong layer wastes
tokens or loses information.

```
Layer          Loaded when?              Token cost per message    Persistence
─────          ────────────              ──────────────────────    ───────────
Instructions   Every message             Fixed (always in prompt)  Code
Skills         Every message             Fixed (always in prompt)  Files on disk
Knowledge      Only when searched        ~500 tokens per search    LanceDB (vector)
User Profile   Every message (if set)    ~50-100 tokens            Database
User Memory    Every message (if set)    ~100-300 tokens           Database
Entity Memory  Every message (if set)    ~200-500 tokens           Database
Session Context Every message            ~100-200 tokens           Database (per session)
Learned Knowledge Only when searched     ~300-500 tokens per search Database + vector
Decision Log   Only when searched        ~200-400 tokens per search Database
Chat History   Every message (N recent)  ~500-2000 tokens          Database (per session)
```

## Layer 1: Instructions (cheapest, always loaded)

**What**: Hardcoded text in the agent definition.
**When loaded**: Every single message. Part of the system prompt.
**Token cost**: Fixed. Whatever you write is always there.
**Best for**: Core behavior rules, personality, response format.

```python
agent = Agent(
    instructions=[
        "You are a support specialist for AikaLabs.",
        "ALWAYS greet in Spanish.",
        "For payments, use confirm_payment (requires approval).",
    ],
)
```

**In QYNE**: Each agent has its own instructions. These define WHAT the agent does.

## Layer 2: Skills (cheap, always loaded)

**What**: Markdown files loaded from disk at startup.
**When loaded**: Every message. Appended to system prompt.
**Token cost**: Fixed. The entire skill file is in every message.
**Best for**: Tool usage guides, domain knowledge, reference data.

```python
# File: skills/automation-commands/automation-playbook.md
# Contains: exact Prefect deployment IDs, command templates, decision rules

agent = Agent(
    skills=Skills(loaders=[LocalSkills("skills/automation-commands")]),
)
```

**In QYNE**: 25 skill directories. The automation-playbook.md has exact
deployment IDs and command templates. This is the RIGHT place for tool
usage instructions.

**Why skills, not knowledge**: Skills are always in context — the agent
doesn't need to search for them. Knowledge requires a search query which
costs extra tokens and might miss.

**Size limit**: Keep skills under 2000 tokens each. Larger skills waste
tokens on every message even when not needed.

## Layer 3: Knowledge Base (moderate, searched on demand)

**What**: Documents indexed in LanceDB with vector embeddings.
**When loaded**: Only when the agent searches (via KnowledgeTools or search_knowledge=True).
**Token cost**: ~500 tokens per search (query embedding + top results).
**Best for**: Large reference documents, crawled websites, uploaded PDFs.

```python
agent = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,  # Agent searches automatically when relevant
)
```

**In QYNE**: 6 markdown docs + 23 crawled pages from startups.rip + 3 from docs.agno.com.

**Don't put here**: Tool instructions, command syntax, deployment IDs.
These need to be always available, not searched.

**Do put here**: Product documentation, company policies, reference material,
crawled websites, uploaded documents.

## Layer 4: User Profile (cheap, always loaded per user)

**What**: Structured data about the user (name, company, role, timezone).
**When loaded**: Every message for that user_id.
**Token cost**: ~50-100 tokens (small structured block).
**Best for**: User identity, preferences that affect every response.

```python
learning = LearningMachine(
    user_profile=UserProfileConfig(mode=LearningMode.ALWAYS),
)
```

**Context injection**:
```
<user_profile>
Name: Juan Perez
Company: TechCorp
Role: CTO
Preferred language: Spanish
</user_profile>
```

**In QYNE**: Active on support agents and utility agents (pal, dash, onboarding).

## Layer 5: User Memory (moderate, always loaded per user)

**What**: Unstructured observations about the user (preferences, behaviors).
**When loaded**: Every message for that user_id.
**Token cost**: ~100-300 tokens (grows over time, needs curation).
**Best for**: Remembering preferences, past interactions, context.

```python
learning = LearningMachine(
    user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),
)
```

**Context injection**:
```
<user_memory>
- Prefers code examples over explanations
- Working on a real estate scraping project
- Uses MercadoLibre Venezuela as data source
</user_memory>
```

**In QYNE**: Active on support agents, pal, dash.

**Curation**: Memories accumulate. Prune every 90 days or when > 20 memories.

## Layer 6: Entity Memory (moderate, always loaded)

**What**: Facts about external entities (companies, people, projects).
**When loaded**: Every message (relevant entities).
**Token cost**: ~200-500 tokens (depends on entity count).
**Best for**: CRM-like knowledge about clients, companies, products.

```python
learning = LearningMachine(
    entity_memory=EntityMemoryConfig(mode=LearningMode.ALWAYS),
)
```

**Tools**: search_entities, create_entity, add_fact, add_event, add_relationship.

**In QYNE**: Active on support agents and utility agents.

## Layer 7: Learned Knowledge (moderate, searched on demand)

**What**: Reusable insights the agent discovers over time.
**When loaded**: Only when searched (agent calls search_learnings).
**Token cost**: ~300-500 tokens per search.
**Best for**: Patterns, solutions, best practices discovered during work.

```python
learning = LearningMachine(
    knowledge=knowledge_base,  # Vector DB for storing learnings
    learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
)
```

**Tools**: search_learnings, save_learning.

**In QYNE**: Active on all agents with learning_minimal or learning_full.

## Layer 8: Decision Log (cheap, searched on demand)

**What**: Record of significant decisions with reasoning.
**When loaded**: Only when searched.
**Token cost**: ~200-400 tokens per search.
**Best for**: Audit trail, consistency in repeated decisions.

```python
learning = LearningMachine(
    decision_log=DecisionLogConfig(mode=LearningMode.AGENTIC),
)
```

**Tools**: log_decision, record_outcome, search_decisions.

## Layer 9: Chat History (expensive, always loaded)

**What**: Previous messages in the current session.
**When loaded**: Every message (last N runs).
**Token cost**: ~500-2000 tokens (depends on num_history_runs).
**Best for**: Conversation continuity within a session.

```python
agent = Agent(
    add_history_to_context=True,
    num_history_runs=5,  # Last 5 exchanges
)
```

**In QYNE**: Most agents use num_history_runs=5. Pal uses 10.

**Optimization**: Use Context Compression to reduce history token cost:
```python
agent = Agent(
    compression_manager=CompressionManager(
        model=FAST_MODEL,
        compress_tool_results=True,
    ),
)
```

## Decision Matrix: What Goes Where

| Information type | Layer | Why |
|-----------------|-------|-----|
| Tool usage instructions | **Skills** | Always available, no search needed |
| Deployment IDs, API endpoints | **Skills** | Must be exact, always in context |
| Agent personality, rules | **Instructions** | Core behavior, never changes |
| Product documentation | **Knowledge** | Large, searched when relevant |
| Crawled websites | **Knowledge** | Large, searched when relevant |
| User name, company, role | **User Profile** | Small, needed every message |
| User preferences | **User Memory** | Grows over time, always relevant |
| Client/company facts | **Entity Memory** | CRM-like, always relevant |
| Discovered patterns | **Learned Knowledge** | Searched when similar situation |
| Past decisions | **Decision Log** | Searched for consistency |
| Conversation context | **Chat History** | Last N messages for continuity |
| Saved conversations | **Directus documents** | Permanent storage, not in agent context |

## Token Budget Per Message (QYNE current config)

| Layer | Tokens | Notes |
|-------|--------|-------|
| Instructions | ~300 | Fixed per agent |
| Skills | ~500-2000 | Depends on skill files loaded |
| Chat History (5 runs) | ~1000-2000 | Compressed with CompressionManager |
| User Profile | ~50-100 | If user_id is set |
| User Memory | ~100-300 | Grows, needs curation |
| Entity Memory | ~200-500 | Grows, needs curation |
| Knowledge search | ~500 | Only when triggered |
| Learned Knowledge search | ~300-500 | Only when triggered |
| **Total per message** | **~2500-5000** | Without searches |
| **Total with searches** | **~3500-6000** | With 1-2 searches |

## Production Recommendations

1. **Keep skills under 2000 tokens each** — they're in every message
2. **Use AGENTIC mode for Learned Knowledge** — agent decides when to save (fewer writes)
3. **Use ALWAYS mode for User Profile and Memory** — automatic, no missed info
4. **Set num_history_runs=5** — balance between context and cost
5. **Enable compression** — reduces history tokens by 40-60%
6. **Curate memories quarterly** — prune old, deduplicate
7. **Don't put tool instructions in Knowledge** — they need to be always available
8. **Don't put large documents in Skills** — they inflate every message
9. **Use Directus for permanent storage** — not agent memory (save_chat_to_directus)
10. **Use Knowledge for searchable content** — not for instructions
