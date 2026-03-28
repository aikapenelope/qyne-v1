# QYNE v1 — Composable Architecture: Agents, Tools, Workflows, Steps

## The Core Principle

In Agno, everything is composable:

```
Agents have tools.
Workflows have steps.
An agent can be a step.
A workflow can be a tool.
An agent can be a tool.
A workflow can be a step.
```

This means you can build arbitrarily complex systems from simple primitives.
A single agent can trigger a workflow that contains other agents that use
other agents as tools. There is no limit to the depth of composition.

## The 6 Composition Patterns

### Pattern 1: Agent has Tools (basic)

The simplest pattern. An agent uses tools to interact with the world.

```python
support_agent = Agent(
    tools=[save_contact, log_ticket, escalate_to_human]
)
```

**In QYNE**: Every agent uses this. Support Agent has Directus REST tools.
Automation Agent has Prefect API tools. Dash has Calculator + Python tools.

### Pattern 2: Agent as a Workflow Step

An agent becomes a step in a deterministic pipeline. The workflow controls
the order, the agent controls the reasoning within its step.

```python
content_production_workflow = Workflow(
    steps=[
        Step(name="Research", agent=trend_scout),      # Agent as step
        Step(name="Compact", executor=_compact),        # Function as step
        Step(name="Script", agent=scriptwriter),        # Agent as step
        Step(name="Review", agent=creative_director),   # Agent as step
    ]
)
```

**In QYNE**: All 7 workflows use this. Deep Research has planner → scouts →
quality gate → synthesizer. SEO Content has keyword research → article →
audit loop.

### Pattern 3: Workflow as a Tool (WorkflowTools)

An agent can trigger an entire workflow as if it were a single tool call.
The agent decides WHEN to run the workflow. The workflow decides HOW.

```python
from agno.tools.workflow import WorkflowTools

# Wrap the workflow as a tool
research_tool = WorkflowTools(
    workflow=deep_research_workflow,
    add_few_shot=True,
    async_mode=True,
)

# Give it to an agent
nexus_master_agent = Agent(
    tools=[research_tool],
    instructions=["When the user asks for deep research, use run_workflow"]
)
```

**In QYNE (not yet implemented)**: This would let nexus_master trigger
deep_research_workflow, content_production_workflow, or competitor_intel_workflow
directly from chat. Instead of routing to a team, it runs the full pipeline.

### Pattern 4: Agent as a Tool

One agent can use another agent as a tool. The parent agent decides when
to call the child agent. The child agent runs independently and returns results.

```python
from agno.tools.decorator import tool

researcher = Agent(name="Researcher", tools=[WebSearchTools()])

@tool()
def research(query: str) -> str:
    """Run a research query using the Research Agent."""
    response = researcher.run(query)
    return response.content

parent_agent = Agent(
    tools=[research],
    instructions=["Use the research tool when you need web data"]
)
```

**In QYNE (not yet implemented)**: Dash could use Knowledge Agent as a tool
to search the knowledge base before answering data questions. The Invoice
Agent could use the Scheduler Agent as a tool to create follow-up reminders
after generating an invoice.

### Pattern 5: Workflow as a Workflow Step (nested workflows)

A workflow can contain another workflow as a step. This creates hierarchical
pipelines where each sub-workflow is a self-contained unit.

```python
data_preparation = Workflow(
    steps=[
        Step(name="Fetch", agent=scraper_agent),
        Step(name="Clean", executor=clean_data),
    ]
)

full_pipeline = Workflow(
    steps=[
        data_preparation,                              # Sub-workflow as step
        Step(name="Analyze", agent=analytics_agent),
        Step(name="Report", agent=report_agent),
    ]
)
```

**In QYNE (not yet implemented)**: The content production workflow could
include the deep research workflow as its first step, creating a
research → content pipeline that runs end-to-end.

### Pattern 6: Team as a Workflow Step

A team (multiple agents collaborating) can be a step in a workflow.
The workflow controls the sequence, the team controls the collaboration.

```python
research_team = Team(
    members=[web_agent, knowledge_agent],
    mode=TeamMode.coordinate,
)

workflow = Workflow(
    steps=[
        research_team,                                 # Team as step
        Step(name="Synthesize", agent=synthesizer),
    ]
)
```

**In QYNE**: The client_research_workflow already uses this pattern with
Parallel(research_agent, knowledge_agent) as a step.

## How This Applies to QYNE

### Current State (what we have)

```
nexus_master (Team, route mode)
    │
    ├── cerebro (Team) → research, knowledge, automation agents
    ├── content_team (Team) → trend_scout, scriptwriter, analytics
    ├── whatsapp_support_team (Team) → whabi, docflow, aurora, general
    ├── product_dev_team (Team) → PM, UX, tech writer
    ├── creative_studio (Team) → image, video, media
    ├── marketing_latam (Team) → copywriter, SEO, social
    ├── dash (Agent) → data analytics
    ├── pal (Agent) → personal assistant
    └── ... (14 individual agents)

Workflows (separate, triggered manually or by Prefect):
    ├── content_production_workflow
    ├── deep_research_workflow
    ├── client_research_workflow
    ├── seo_content_workflow
    ├── social_media_workflow
    ├── competitor_intel_workflow
    └── media_generation_workflow
```

### Target State (with full composition)

```
nexus_master (Team, route mode)
    │
    ├── cerebro (Team)
    │   ├── research_agent (has deep_research_workflow as tool)
    │   ├── knowledge_agent
    │   └── automation_agent (has Prefect API + n8n MCP as tools)
    │
    ├── content_team (Team)
    │   ├── trend_scout (has competitor_intel_workflow as tool)
    │   ├── scriptwriter
    │   ├── creative_director
    │   └── analytics_agent (has Dash as tool for data queries)
    │
    ├── whatsapp_support_team (Team)
    │   ├── whabi_support (has Invoice Agent as tool for billing)
    │   ├── docflow_support
    │   ├── aurora_support
    │   └── general_support (has Onboarding Agent as tool)
    │
    ├── dash (Agent, has knowledge_agent as tool)
    ├── pal (Agent, has scheduler_agent as tool)
    └── invoice_agent (has scheduler_agent as tool for reminders)

Workflows (available as tools to agents):
    ├── deep_research_workflow → tool for research_agent
    ├── content_production_workflow → tool for content_team
    ├── seo_content_workflow → tool for marketing_latam
    ├── competitor_intel_workflow → tool for trend_scout
    └── social_media_workflow → tool for social_media_planner
```

### What Changes

| Pattern | Current | Target |
|---------|---------|--------|
| Agent has tools | Yes (REST, MCP, Prefect) | Same + agents as tools |
| Agent as step | Yes (all workflows) | Same |
| Workflow as tool | No | Yes (WorkflowTools) |
| Agent as tool | No | Yes (@tool wrapper) |
| Nested workflows | No | Yes (sub-workflows) |
| Team as step | Partial (Parallel) | Full |

## Implementation Plan

### Phase 1: Workflows as Tools (highest impact)

Give agents the ability to trigger full workflows from chat:

```python
from agno.tools.workflow import WorkflowTools

# In research_agent:
research_agent = Agent(
    tools=[
        WebSearchTools(),
        WorkflowTools(workflow=deep_research_workflow, async_mode=True),
    ],
    instructions=[
        "For simple questions, search the web directly.",
        "For complex research, use run_workflow to trigger deep research.",
    ]
)
```

This means: "Investiga a fondo sobre X" triggers the full deep research
pipeline (planner → parallel scouts → quality gate → synthesis) instead
of a single web search.

### Phase 2: Agents as Tools (cross-agent collaboration)

Let agents call other agents for specialized tasks:

```python
@tool()
def ask_knowledge_base(query: str) -> str:
    """Search the internal knowledge base for relevant information."""
    response = knowledge_agent.run(query)
    return response.content

dash = Agent(
    tools=[ask_knowledge_base, CalculatorTools(), PythonTools()],
)
```

This means: Dash can search the knowledge base before answering data
questions, combining structured data from Directus with unstructured
knowledge from LanceDB.

### Phase 3: Nested Workflows (pipeline composition)

Compose workflows from other workflows:

```python
full_content_pipeline = Workflow(
    steps=[
        deep_research_workflow,           # Sub-workflow: research
        content_production_workflow,       # Sub-workflow: create content
        seo_content_workflow,             # Sub-workflow: optimize for SEO
    ]
)
```

This means: One command produces a fully researched, scripted, and
SEO-optimized piece of content.

## Rules for Composition

1. **Depth limit**: Max 3 levels of nesting. Deeper = harder to debug.
2. **Timeout awareness**: Nested calls multiply latency. Set timeouts.
3. **Error propagation**: If a sub-agent fails, the parent must handle it.
4. **Token budget**: Each level of nesting consumes tokens. Monitor usage.
5. **Tracing**: Every level is traced. Use traces to debug composition.
6. **Approval chains**: If a sub-agent needs approval, the parent waits.

## What NOT to Compose

- Don't make an agent call itself (infinite loop).
- Don't nest teams inside teams (use workflows instead).
- Don't use workflows for simple tool calls (overhead not worth it).
- Don't compose for the sake of composing. Start simple, add layers when needed.
