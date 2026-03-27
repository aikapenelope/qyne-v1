"""
NEXUS Cerebro — Knowledge Agent.

Queries the internal knowledge base (pgvector) and provides context.
Uses reasoning for complex queries that require multi-step analysis.
"""

from agno.agent import Agent

from app.config import REASONING_MODEL, FOLLOWUP_MODEL, db, knowledge_base
from app.shared import guardrails, learning_minimal

knowledge_agent = Agent(
    name="Knowledge Agent",
    id="knowledge-agent",
    role="Query internal knowledge base and provide context",
    model=REASONING_MODEL,
    knowledge=knowledge_base,
    search_knowledge=True,
    pre_hooks=guardrails,
    reasoning=True,
    reasoning_min_steps=2,
    reasoning_max_steps=5,
    instructions=[
        "You are a knowledge specialist.",
        "Search the knowledge base for relevant information before answering.",
        "Provide context from internal knowledge and past analyses.",
        "Cross-reference information across different domains.",
        "Cite specific facts and relationships.",
        "When no relevant knowledge is found, work from conversation context.",
    ],
    db=db,
    learning=learning_minimal,
    add_history_to_context=True,
    num_history_runs=3,
    add_datetime_to_context=True,
    update_memory_on_run=True,
    markdown=True,
    followups=True,
    num_followups=3,
    followup_model=FOLLOWUP_MODEL,
)
