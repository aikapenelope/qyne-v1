"""
NEXUS Cerebro — Research Agent.

Searches the web for current information and data.
Uses free tools (DuckDuckGo, Wikipedia, etc.) to avoid API costs.
"""

from agno.agent import Agent
from agno.tools.websearch import WebSearchTools

from app.config import TOOL_MODEL, FOLLOWUP_MODEL, db
from app.shared import guardrails, learning_minimal, compression

research_agent = Agent(
    name="Research Agent",
    id="research-agent",
    role="Search the web for current information and data",
    model=TOOL_MODEL,
    tools=[WebSearchTools(fixed_max_results=5)],
    tool_call_limit=5,
    retries=2,
    pre_hooks=guardrails,
    instructions=[
        "You are a research specialist.",
        "Use the web_search tool to find current, accurate information.",
        "Always include sources with URLs and dates.",
        "Present data in structured formats when possible.",
        "Be thorough but concise.",
    ],
    db=db,
    learning=learning_minimal,
    add_history_to_context=True,
    num_history_runs=3,
    add_datetime_to_context=True,
    markdown=True,
    followups=True,
    num_followups=3,
    followup_model=FOLLOWUP_MODEL,
    compression_manager=compression,
)
